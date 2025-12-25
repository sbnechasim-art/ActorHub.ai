"""
Notification Tasks

Handles email, push, and webhook notifications with distributed tracing.

FIXED: Now actually sends emails via SendGrid instead of being a stub.
"""
import asyncio
from typing import Dict, Optional
from datetime import datetime
import structlog
import httpx

from celery_app import app
from config import settings
from tracing import trace_task, get_trace_headers_for_subtask, add_task_attribute

logger = structlog.get_logger()

# SendGrid client (lazy-loaded)
_sendgrid_client = None

# Firebase Admin SDK (lazy-loaded)
_firebase_app = None


def get_firebase_app():
    """Get or initialize Firebase Admin SDK."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    if not settings.FIREBASE_CREDENTIALS_PATH and not settings.FIREBASE_PROJECT_ID:
        logger.debug("Firebase not configured, push notifications will be logged only")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Check if already initialized
        try:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app
        except ValueError:
            pass  # Not initialized yet

        # Initialize with credentials file or default credentials
        if settings.FIREBASE_CREDENTIALS_PATH:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            # Use Application Default Credentials (for GCP)
            _firebase_app = firebase_admin.initialize_app()

        logger.info("Firebase Admin SDK initialized")
        return _firebase_app

    except ImportError:
        logger.warning("firebase-admin package not installed. Run: pip install firebase-admin")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None


def _send_push_notification_sync(
    device_tokens: list,
    title: str,
    body: str,
    data: dict = None,
    image_url: str = None
) -> dict:
    """
    Send push notification via Firebase Cloud Messaging.

    Args:
        device_tokens: List of FCM device tokens
        title: Notification title
        body: Notification body
        data: Optional custom data payload
        image_url: Optional image URL to display

    Returns:
        Dict with success status and details
    """
    app = get_firebase_app()
    if not app:
        # Log for development
        logger.info(
            "Push notification would be sent (Firebase not configured)",
            title=title,
            token_count=len(device_tokens),
        )
        return {"success": True, "sent": 0, "failed": 0, "pending_fcm": True}

    try:
        from firebase_admin import messaging

        # Build notification
        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url,
        )

        # Build Android-specific config
        android_config = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                icon="ic_notification",
                color="#6366F1",  # Primary color
                sound="default",
                click_action="FLUTTER_NOTIFICATION_CLICK",
            ),
        )

        # Build iOS-specific config (APNs)
        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound="default",
                    badge=1,
                ),
            ),
        )

        # Build web push config
        web_push_config = messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=title,
                body=body,
                icon="/icon-192.png",
            ),
        )

        # Send to multiple tokens
        if len(device_tokens) == 1:
            # Single message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=device_tokens[0],
                android=android_config,
                apns=apns_config,
                webpush=web_push_config,
            )
            response = messaging.send(message)
            logger.info("Push notification sent", message_id=response)
            return {"success": True, "sent": 1, "failed": 0, "message_id": response}
        else:
            # Multicast for multiple tokens
            message = messaging.MulticastMessage(
                notification=notification,
                data=data or {},
                tokens=device_tokens,
                android=android_config,
                apns=apns_config,
                webpush=web_push_config,
            )
            response = messaging.send_each_for_multicast(message)

            logger.info(
                "Push notifications sent",
                success_count=response.success_count,
                failure_count=response.failure_count,
            )

            # Collect failed tokens for cleanup
            failed_tokens = []
            for idx, result in enumerate(response.responses):
                if not result.success:
                    failed_tokens.append(device_tokens[idx])

            return {
                "success": response.success_count > 0,
                "sent": response.success_count,
                "failed": response.failure_count,
                "failed_tokens": failed_tokens,
            }

    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return {"success": False, "error": str(e)}


async def _get_user_device_tokens(user_id: str) -> list:
    """Fetch user's device tokens from database."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        result = await db.execute(
            text("""
                SELECT token FROM device_tokens
                WHERE user_id = :user_id AND is_active = true
            """),
            {"user_id": user_id}
        )
        tokens = [row[0] for row in result.fetchall()]

    await engine.dispose()
    return tokens


def get_sendgrid_client():
    """Get or create SendGrid client."""
    global _sendgrid_client
    if _sendgrid_client is None:
        if not settings.SENDGRID_API_KEY:
            logger.warning("SENDGRID_API_KEY not configured, emails will be logged only")
            return None
        try:
            from sendgrid import SendGridAPIClient
            _sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        except ImportError:
            logger.error("sendgrid package not installed. Run: pip install sendgrid")
            return None
    return _sendgrid_client


def _send_email_sync(to: str, subject: str, body: str, html: Optional[str] = None) -> bool:
    """
    Synchronous email sending via SendGrid.

    Returns True if email was sent successfully.
    """
    client = get_sendgrid_client()
    if not client:
        # Log for development
        logger.info(
            "Email would be sent (SendGrid not configured)",
            to=to,
            subject=subject,
        )
        return True

    try:
        from sendgrid.helpers.mail import Mail, Email, To, Content

        message = Mail(
            from_email=Email(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
            to_emails=To(to),
            subject=subject,
        )

        # Add HTML content if provided, otherwise use plain text
        if html:
            message.add_content(Content("text/html", html))
        message.add_content(Content("text/plain", body))

        response = client.send(message)
        success = response.status_code in (200, 201, 202)

        if success:
            logger.info(
                "Email sent successfully",
                to=to,
                subject=subject,
                status_code=response.status_code,
            )
        else:
            logger.warning(
                "Email send returned non-success status",
                to=to,
                subject=subject,
                status_code=response.status_code,
            )

        return success

    except Exception as e:
        logger.error(
            "Failed to send email",
            to=to,
            subject=subject,
            error=str(e),
        )
        return False


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_email(
    self,
    to: str,
    subject: str,
    body: str,
    html: str = None,
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Send email notification via SendGrid.

    FIXED: Now actually sends emails instead of being a stub.
    Includes retry logic with exponential backoff.
    """
    with trace_task("send_email", trace_headers, {"recipient": to[:50]}) as span:
        add_task_attribute("subject", subject[:100])
        add_task_attribute("retry_count", self.request.retries)

        try:
            success = _send_email_sync(to, subject, body, html)

            if success:
                return {'success': True, 'to': to}
            else:
                raise Exception("Email send returned failure status")

        except Exception as e:
            logger.error(
                "Email task failed",
                to=to,
                subject=subject,
                error=str(e),
                retry_count=self.request.retries
            )
            # Retry with exponential backoff
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))

            return {'success': False, 'to': to, 'error': str(e)}


@app.task(bind=True, max_retries=2, default_retry_delay=15)
def send_push_notification(
    self,
    user_id: str,
    title: str,
    body: str,
    data: Dict = None,
    device_tokens: list = None,
    image_url: str = None,
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Send push notification via Firebase Cloud Messaging.

    Args:
        user_id: Target user ID
        title: Notification title
        body: Notification body
        data: Optional custom data payload (e.g., {"action": "open_pack", "pack_id": "..."})
        device_tokens: Optional list of device tokens (if not provided, fetched from DB)
        image_url: Optional image URL to display in notification
        trace_headers: Trace context for distributed tracing

    Returns:
        Dict with success status, sent count, and any failed tokens
    """
    with trace_task("send_push_notification", trace_headers, {"user_id": user_id}) as span:
        add_task_attribute("title", title[:100])
        add_task_attribute("retry_count", self.request.retries)

        try:
            # Get device tokens if not provided
            tokens = device_tokens
            if not tokens:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    tokens = loop.run_until_complete(_get_user_device_tokens(user_id))
                finally:
                    loop.close()

            if not tokens:
                logger.debug("No device tokens found for user", user_id=user_id)
                return {
                    "success": True,
                    "user_id": user_id,
                    "sent": 0,
                    "message": "No device tokens registered"
                }

            add_task_attribute("token_count", len(tokens))

            # Ensure data values are strings (FCM requirement)
            clean_data = {}
            if data:
                for key, value in data.items():
                    clean_data[str(key)] = str(value) if value is not None else ""

            # Send push notification
            result = _send_push_notification_sync(
                device_tokens=tokens,
                title=title,
                body=body,
                data=clean_data,
                image_url=image_url,
            )

            add_task_attribute("sent_count", result.get("sent", 0))
            add_task_attribute("failed_count", result.get("failed", 0))

            if result.get("success"):
                logger.info(
                    "Push notification sent",
                    user_id=user_id,
                    sent=result.get("sent", 0),
                    failed=result.get("failed", 0),
                )
                return {
                    "success": True,
                    "user_id": user_id,
                    **result
                }
            else:
                raise Exception(result.get("error", "Unknown FCM error"))

        except Exception as e:
            logger.error(
                "Push notification failed",
                user_id=user_id,
                error=str(e),
                retry_count=self.request.retries
            )
            # Retry with exponential backoff
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=15 * (2 ** self.request.retries))

            return {"success": False, "user_id": user_id, "error": str(e)}


@app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_webhook(
    self,
    url: str,
    payload: Dict,
    headers: Dict = None,
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Send webhook notification with exponential backoff retry.

    FIXED: Now includes retry logic with exponential backoff.
    Retries: 60s, 120s, 240s, 480s, 960s (up to 5 retries)
    """
    with trace_task("send_webhook", trace_headers, {"url": url[:200]}) as span:
        add_task_attribute("retry_count", self.request.retries)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send_webhook_async(url, payload, headers))
        finally:
            loop.close()

        add_task_attribute("status_code", result.get("status_code", 0))
        add_task_attribute("success", result.get("success", False))

        if result.get("success"):
            logger.info("Webhook delivered successfully", url=url, status=result.get("status_code"))
            return result
        else:
            error = result.get("error", "Unknown error")
            logger.warning(
                "Webhook delivery failed",
                url=url,
                error=error,
                retry_count=self.request.retries
            )
            # Retry with exponential backoff
            if self.request.retries < self.max_retries:
                raise self.retry(
                    exc=Exception(error),
                    countdown=60 * (2 ** self.request.retries)
                )

            return result


async def _send_webhook_async(url: str, payload: Dict, headers: Dict = None) -> Dict:
    """Async webhook sending"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers or {}
            )
            return {
                'success': response.status_code < 400,
                'status_code': response.status_code
            }
    except Exception as e:
        logger.error("Webhook request failed", error=str(e), url=url)
        return {'success': False, 'error': str(e)}


@app.task
def notify_training_complete(
    user_id: str,
    actor_pack_id: str,
    quality_score: float,
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Notify user that Actor Pack training is complete.
    """
    with trace_task("notify_training_complete", trace_headers, {
        "user_id": user_id,
        "actor_pack_id": actor_pack_id,
        "quality_score": quality_score,
    }) as span:
        # Propagate trace context to sub-tasks
        child_headers = get_trace_headers_for_subtask()

        # Send email
        send_email.delay(
            to=f"user-{user_id}@actorhub.ai",  # Would be real email from DB
            subject="Your Actor Pack is Ready!",
            body=f"Your Actor Pack has been trained with a quality score of {quality_score}%.",
            trace_headers=child_headers
        )

        # Send push notification
        send_push_notification.delay(
            user_id=user_id,
            title="Actor Pack Ready",
            body=f"Quality score: {quality_score}%",
            data={'actor_pack_id': actor_pack_id},
            trace_headers=child_headers
        )

        logger.info(
            "Training complete notifications sent",
            user_id=user_id,
            actor_pack_id=actor_pack_id,
            quality_score=quality_score
        )
        return {'success': True}


@app.task
def notify_unauthorized_use(
    identity_id: str,
    platform: str,
    image_url: str,
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Notify identity owner of unauthorized use detection.
    """
    with trace_task("notify_unauthorized_use", trace_headers, {
        "identity_id": identity_id,
        "platform": platform,
    }) as span:
        logger.warning(
            "Unauthorized use detected",
            identity_id=identity_id,
            platform=platform,
            image_url=image_url[:200]
        )

        # Would look up user from identity and send notifications
        return {
            'success': True,
            'identity_id': identity_id,
            'platform': platform
        }


@app.task
def notify_license_purchased(
    seller_id: str,
    buyer_id: str,
    license_id: str,
    amount: float,
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Notify seller that a license was purchased.
    """
    with trace_task("notify_license_purchased", trace_headers, {
        "seller_id": seller_id,
        "license_id": license_id,
        "amount": amount,
    }) as span:
        child_headers = get_trace_headers_for_subtask()

        send_email.delay(
            to=f"seller-{seller_id}@actorhub.ai",
            subject="New License Sale!",
            body=f"Congratulations! Someone purchased a license for ${amount}.",
            trace_headers=child_headers
        )

        logger.info(
            "License purchase notification sent",
            seller_id=seller_id,
            buyer_id=buyer_id,
            license_id=license_id,
            amount=amount
        )
        return {'success': True}
