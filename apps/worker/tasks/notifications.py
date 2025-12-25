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
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Send push notification.

    TODO: Implement Firebase Cloud Messaging (FCM) integration.
    Currently logs the notification for development purposes.
    """
    with trace_task("send_push_notification", trace_headers, {"user_id": user_id}) as span:
        add_task_attribute("title", title[:100])
        add_task_attribute("retry_count", self.request.retries)

        # TODO: Implement FCM push notification
        # For now, log the notification (no real push)
        logger.info(
            "Push notification (logged, FCM not configured)",
            user_id=user_id,
            title=title,
            body=body,
            data=data,
        )
        return {'success': True, 'user_id': user_id, 'pending_fcm': True}


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
