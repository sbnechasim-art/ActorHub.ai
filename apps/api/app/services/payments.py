"""
Stripe Payments Service

Centralized, resilient Stripe integration with:
- Circuit breaker protection
- Retry with exponential backoff
- Idempotency keys for safe retries
- Proper timeout configuration
- Comprehensive error handling
"""

import asyncio
import uuid
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional

import structlog

from app.core.config import settings
from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    RetryConfig,
    ResilientService,
    STRIPE_CIRCUIT_CONFIG,
    STRIPE_RETRY_CONFIG,
    retry_sync,
    EXTERNAL_CALL_DURATION,
)

logger = structlog.get_logger()


class StripeError(Exception):
    """Base exception for Stripe errors"""

    def __init__(self, message: str, code: Optional[str] = None, decline_code: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.decline_code = decline_code


class StripeServiceUnavailable(StripeError):
    """Raised when Stripe service is unavailable (circuit open)"""

    pass


class StripePaymentFailed(StripeError):
    """Raised when payment fails (card declined, etc.)"""

    pass


class StripeService:
    """
    Resilient Stripe payment service.

    All Stripe operations go through this service to ensure:
    - Consistent error handling
    - Circuit breaker protection
    - Retry logic for transient failures
    - Idempotency for safe retries
    - Proper timeouts
    """

    # Stripe SDK instance
    _stripe = None

    # Circuit breaker instance
    _circuit_breaker = CircuitBreaker("stripe", STRIPE_CIRCUIT_CONFIG)

    # Default timeouts (seconds)
    DEFAULT_TIMEOUT = 30
    WEBHOOK_TIMEOUT = settings.WEBHOOK_TIMEOUT

    def __init__(self):
        self._ensure_configured()

    def _ensure_configured(self):
        """Ensure Stripe is properly configured"""
        if self._stripe is None:
            try:
                import stripe

                stripe.api_key = settings.STRIPE_SECRET_KEY
                stripe.max_network_retries = 0  # We handle retries ourselves
                stripe.default_http_client = stripe.http_client.RequestsClient(
                    timeout=self.DEFAULT_TIMEOUT
                )
                self._stripe = stripe
                logger.info("Stripe client initialized with resilience settings")
            except ImportError:
                logger.error("stripe package not installed")
                raise ImportError("stripe package is required. Run: pip install stripe")

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured"""
        return bool(settings.STRIPE_SECRET_KEY)

    @property
    def is_available(self) -> bool:
        """Check if Stripe service is available (circuit closed)"""
        return self._circuit_breaker.is_closed

    def _generate_idempotency_key(self, prefix: str = "") -> str:
        """Generate idempotency key for safe retries"""
        key = f"{prefix}_{uuid.uuid4().hex}" if prefix else uuid.uuid4().hex
        return key

    async def _execute_stripe_call(
        self,
        operation_name: str,
        stripe_func,
        *args,
        idempotency_key: Optional[str] = None,
        skip_retry: bool = False,
        **kwargs,
    ) -> Any:
        """
        Execute a Stripe API call with full resilience stack.

        Args:
            operation_name: Name for logging/metrics
            stripe_func: Stripe SDK function to call
            idempotency_key: Key for safe retries (auto-generated if not provided)
            skip_retry: Skip retry logic (for non-idempotent operations)
            *args, **kwargs: Arguments for the Stripe function
        """
        if not self.is_configured:
            raise StripeError("Stripe is not configured. Set STRIPE_SECRET_KEY.")

        # Add idempotency key if not provided
        if idempotency_key is None and not skip_retry:
            idempotency_key = self._generate_idempotency_key(operation_name)

        if idempotency_key:
            kwargs["idempotency_key"] = idempotency_key

        # Wrap the sync Stripe call to run in executor
        loop = asyncio.get_event_loop()

        def sync_call():
            import time
            start = time.time()
            try:
                result = stripe_func(*args, **kwargs)
                duration = time.time() - start
                EXTERNAL_CALL_DURATION.labels(
                    service="stripe", operation=operation_name
                ).observe(duration)
                return result
            except self._stripe.error.RateLimitError as e:
                raise ConnectionError(f"Stripe rate limited: {e}")
            except self._stripe.error.APIConnectionError as e:
                raise ConnectionError(f"Stripe connection error: {e}")
            except self._stripe.error.CardError as e:
                raise StripePaymentFailed(
                    str(e), code=e.code, decline_code=e.decline_code
                )
            except self._stripe.error.StripeError as e:
                raise StripeError(str(e), code=getattr(e, "code", None))

        async def async_call():
            return await loop.run_in_executor(None, sync_call)

        try:
            # Check circuit breaker
            if not await self._circuit_breaker._check_state():
                raise StripeServiceUnavailable(
                    "Stripe service temporarily unavailable. Please try again later."
                )

            # Execute with retry if not skipped
            if skip_retry:
                result = await async_call()
            else:
                # Retry config for Stripe (only retry transient errors)
                retry_config = RetryConfig(
                    max_attempts=3,
                    base_delay=1.0,
                    max_delay=10.0,
                    retryable_exceptions={ConnectionError, TimeoutError, asyncio.TimeoutError},
                )

                async def retryable_call():
                    return await async_call()

                from app.core.resilience import retry_async
                result = await retry_async(
                    retryable_call,
                    config=retry_config,
                    service_name="stripe",
                )

            await self._circuit_breaker._record_success()
            return result

        except (StripePaymentFailed, StripeError) as e:
            # Don't count payment failures as circuit breaker failures
            # These are expected business errors
            logger.warning(
                f"Stripe {operation_name} failed",
                error=str(e),
                code=getattr(e, "code", None),
            )
            raise

        except Exception as e:
            await self._circuit_breaker._record_failure(e)
            logger.error(
                f"Stripe {operation_name} error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    # ===========================================
    # Customer Operations
    # ===========================================

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create a new Stripe customer"""
        params = {"email": email}
        if name:
            params["name"] = name
        if metadata:
            params["metadata"] = metadata

        result = await self._execute_stripe_call(
            "create_customer",
            self._stripe.Customer.create,
            **params,
        )
        return {"customer_id": result.id, "email": result.email}

    async def get_customer(self, customer_id: str) -> Dict:
        """Retrieve a Stripe customer"""
        result = await self._execute_stripe_call(
            "get_customer",
            self._stripe.Customer.retrieve,
            customer_id,
            skip_retry=True,  # GET operations are idempotent
        )
        return {
            "customer_id": result.id,
            "email": result.email,
            "name": result.name,
            "created": result.created,
        }

    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Update a Stripe customer"""
        params = {}
        if email:
            params["email"] = email
        if name:
            params["name"] = name
        if metadata:
            params["metadata"] = metadata

        result = await self._execute_stripe_call(
            "update_customer",
            self._stripe.Customer.modify,
            customer_id,
            **params,
        )
        return {"customer_id": result.id}

    # ===========================================
    # Checkout Operations
    # ===========================================

    async def create_checkout_session(
        self,
        customer_id: str,
        line_items: List[Dict],
        mode: str = "subscription",
        success_url: str = None,
        cancel_url: str = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create a Stripe Checkout Session"""
        success_url = success_url or f"{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = cancel_url or f"{settings.FRONTEND_URL}/checkout?canceled=true"

        params = {
            "customer": customer_id,
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        if metadata:
            params["metadata"] = metadata

        result = await self._execute_stripe_call(
            "create_checkout_session",
            self._stripe.checkout.Session.create,
            **params,
        )

        return {
            "session_id": result.id,
            "checkout_url": result.url,
            "payment_intent": result.payment_intent,
        }

    async def get_checkout_session(self, session_id: str) -> Dict:
        """Retrieve a Checkout Session"""
        result = await self._execute_stripe_call(
            "get_checkout_session",
            self._stripe.checkout.Session.retrieve,
            session_id,
            skip_retry=True,
        )
        return {
            "session_id": result.id,
            "status": result.status,
            "payment_status": result.payment_status,
            "customer": result.customer,
            "amount_total": result.amount_total,
        }

    # ===========================================
    # Subscription Operations
    # ===========================================

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create a subscription"""
        params = {
            "customer": customer_id,
            "items": [{"price": price_id}],
        }
        if metadata:
            params["metadata"] = metadata

        result = await self._execute_stripe_call(
            "create_subscription",
            self._stripe.Subscription.create,
            **params,
        )

        return {
            "subscription_id": result.id,
            "status": result.status,
            "current_period_end": result.current_period_end,
        }

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> Dict:
        """Cancel a subscription"""
        if at_period_end:
            result = await self._execute_stripe_call(
                "cancel_subscription",
                self._stripe.Subscription.modify,
                subscription_id,
                cancel_at_period_end=True,
            )
        else:
            result = await self._execute_stripe_call(
                "cancel_subscription_immediately",
                self._stripe.Subscription.delete,
                subscription_id,
            )

        return {
            "subscription_id": result.id,
            "status": result.status,
            "cancel_at_period_end": result.cancel_at_period_end,
        }

    async def reactivate_subscription(self, subscription_id: str) -> Dict:
        """Reactivate a canceled subscription"""
        result = await self._execute_stripe_call(
            "reactivate_subscription",
            self._stripe.Subscription.modify,
            subscription_id,
            cancel_at_period_end=False,
        )

        return {
            "subscription_id": result.id,
            "status": result.status,
        }

    async def get_subscription(self, subscription_id: str) -> Dict:
        """Get subscription details"""
        result = await self._execute_stripe_call(
            "get_subscription",
            self._stripe.Subscription.retrieve,
            subscription_id,
            skip_retry=True,
        )

        return {
            "subscription_id": result.id,
            "status": result.status,
            "current_period_start": result.current_period_start,
            "current_period_end": result.current_period_end,
            "cancel_at_period_end": result.cancel_at_period_end,
        }

    # ===========================================
    # Refund Operations
    # ===========================================

    async def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create a refund"""
        params = {"payment_intent": payment_intent_id}
        if amount:
            params["amount"] = amount
        if reason:
            params["reason"] = reason
        if metadata:
            params["metadata"] = metadata

        result = await self._execute_stripe_call(
            "create_refund",
            self._stripe.Refund.create,
            **params,
        )

        return {
            "refund_id": result.id,
            "status": result.status,
            "amount": result.amount,
        }

    # ===========================================
    # Webhook Handling
    # ===========================================

    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str = None,
    ):
        """
        Construct and verify a webhook event.

        Note: This is synchronous as it's typically called in a webhook handler.
        """
        webhook_secret = webhook_secret or settings.STRIPE_WEBHOOK_SECRET

        if not webhook_secret:
            raise StripeError("Webhook secret not configured")

        try:
            event = self._stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            return event
        except self._stripe.error.SignatureVerificationError as e:
            raise StripeError(f"Invalid webhook signature: {e}")

    # ===========================================
    # Account Operations (for Connect)
    # ===========================================

    async def create_connect_account(
        self,
        email: str,
        country: str = "US",
        account_type: str = "express",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create a Stripe Connect account"""
        params = {
            "type": account_type,
            "email": email,
            "country": country,
            "capabilities": {
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        }
        if metadata:
            params["metadata"] = metadata

        result = await self._execute_stripe_call(
            "create_connect_account",
            self._stripe.Account.create,
            **params,
        )

        return {
            "account_id": result.id,
            "email": result.email,
        }

    async def create_account_link(
        self,
        account_id: str,
        refresh_url: str,
        return_url: str,
        link_type: str = "account_onboarding",
    ) -> Dict:
        """Create an account link for Connect onboarding"""
        result = await self._execute_stripe_call(
            "create_account_link",
            self._stripe.AccountLink.create,
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type=link_type,
        )

        return {
            "url": result.url,
            "expires_at": result.expires_at,
        }

    async def create_login_link(self, account_id: str) -> Dict:
        """Create a login link for Connect dashboard"""
        result = await self._execute_stripe_call(
            "create_login_link",
            self._stripe.Account.create_login_link,
            account_id,
        )

        return {"url": result.url}

    async def get_account(self, account_id: str = None) -> Dict:
        """Get account details (own account if no ID provided)"""
        if account_id:
            result = await self._execute_stripe_call(
                "get_account",
                self._stripe.Account.retrieve,
                account_id,
                skip_retry=True,
            )
        else:
            result = await self._execute_stripe_call(
                "get_own_account",
                self._stripe.Account.retrieve,
                skip_retry=True,
            )

        return {
            "account_id": result.id,
            "email": result.email,
            "charges_enabled": result.charges_enabled,
            "payouts_enabled": result.payouts_enabled,
            "details_submitted": result.details_submitted,
            "requirements": getattr(result.requirements, "currently_due", []) if result.requirements else [],
        }

    # ===========================================
    # Transfer Operations (Payouts to Connected Accounts)
    # ===========================================

    async def create_transfer(
        self,
        amount: int,
        destination: str,
        currency: str = "usd",
        transfer_group: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a transfer to a connected Stripe account.

        Args:
            amount: Amount in cents
            destination: Connected account ID
            currency: Currency code (default: usd)
            transfer_group: Group identifier for related transfers
            metadata: Additional metadata
        """
        params = {
            "amount": amount,
            "currency": currency,
            "destination": destination,
        }
        if transfer_group:
            params["transfer_group"] = transfer_group
        if metadata:
            params["metadata"] = metadata

        result = await self._execute_stripe_call(
            "create_transfer",
            self._stripe.Transfer.create,
            **params,
        )

        logger.info(
            "Transfer created",
            transfer_id=result.id,
            destination=destination,
            amount=amount,
        )

        return {
            "transfer_id": result.id,
            "amount": result.amount,
            "currency": result.currency,
            "destination": result.destination,
        }

    async def get_balance(self, stripe_account: Optional[str] = None) -> Dict:
        """
        Get balance for own account or a connected account.

        Args:
            stripe_account: Connected account ID (optional)
        """
        if stripe_account:
            result = await self._execute_stripe_call(
                "get_balance",
                lambda: self._stripe.Balance.retrieve(stripe_account=stripe_account),
                skip_retry=True,
            )
        else:
            result = await self._execute_stripe_call(
                "get_balance",
                self._stripe.Balance.retrieve,
                skip_retry=True,
            )

        available = sum(b.amount for b in result.available) if result.available else 0
        pending = sum(b.amount for b in result.pending) if result.pending else 0
        currency = result.available[0].currency if result.available else "usd"

        return {
            "available": available / 100,  # Convert cents to dollars
            "pending": pending / 100,
            "currency": currency,
        }

    # ===========================================
    # Health Check
    # ===========================================

    async def health_check(self) -> Dict:
        """Check Stripe API health"""
        if not self.is_configured:
            return {
                "status": "not_configured",
                "error": "STRIPE_SECRET_KEY not set",
            }

        try:
            result = await self.get_account()
            return {
                "status": "healthy",
                "circuit_state": self._circuit_breaker.state.name,
            }
        except CircuitBreakerOpenError:
            return {
                "status": "circuit_open",
                "error": "Circuit breaker is open",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Singleton instance
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    """Get or create Stripe service singleton"""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
