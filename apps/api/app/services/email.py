"""
Email Service using SendGrid

Handles all transactional email sending for ActorHub.ai including:
- Welcome emails
- Identity verification notifications
- Training status updates
- License purchase confirmations
- Payout notifications
- Password reset
"""

import structlog
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import settings

logger = structlog.get_logger()


class EmailService:
    """SendGrid email service with template support."""

    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME
        self._client = None

    @property
    def client(self):
        """Lazy-load SendGrid client."""
        if self._client is None:
            if not self.api_key:
                logger.warning("SENDGRID_API_KEY not configured, emails will be logged only")
                return None
            try:
                from sendgrid import SendGridAPIClient
                self._client = SendGridAPIClient(self.api_key)
            except ImportError:
                logger.error("sendgrid package not installed. Run: pip install sendgrid")
                return None
        return self._client

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None,
    ) -> bool:
        """
        Send an email using SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            plain_content: Plain text body (optional, extracted from HTML if not provided)
            reply_to: Reply-to email address (optional)
            attachments: List of attachments (optional)

        Returns:
            True if email was sent successfully
        """
        if not self.client:
            # Log email for development
            logger.info(
                "Email would be sent (SendGrid not configured)",
                to=to_email,
                subject=subject,
            )
            return True

        try:
            from sendgrid.helpers.mail import (
                Mail, Email, To, Content, Attachment,
                FileContent, FileName, FileType, Disposition
            )
            import base64

            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
            )

            # Add HTML content
            message.add_content(Content("text/html", html_content))

            # Add plain text content if provided
            if plain_content:
                message.add_content(Content("text/plain", plain_content))

            # Add reply-to if provided
            if reply_to:
                message.reply_to = Email(reply_to)

            # Add attachments if provided
            if attachments:
                for att in attachments:
                    attachment = Attachment(
                        FileContent(base64.b64encode(att["content"]).decode()),
                        FileName(att["filename"]),
                        FileType(att.get("type", "application/octet-stream")),
                        Disposition("attachment"),
                    )
                    message.add_attachment(attachment)

            response = self.client.send(message)

            logger.info(
                "Email sent successfully",
                to=to_email,
                subject=subject,
                status_code=response.status_code,
            )

            return response.status_code in (200, 201, 202)

        except Exception as e:
            logger.error(
                "Failed to send email",
                to=to_email,
                subject=subject,
                error=str(e),
            )
            return False

    # ==========================================
    # Email Templates
    # ==========================================

    async def send_welcome_email(self, to_email: str, name: str) -> bool:
        """Send welcome email to new users."""
        subject = f"Welcome to {settings.APP_NAME}!"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{settings.APP_NAME}</h1>
                </div>
                <div class="content">
                    <h2>Welcome, {name}!</h2>
                    <p>Thank you for joining {settings.APP_NAME}. We're excited to have you on board!</p>
                    <p>With {settings.APP_NAME}, you can:</p>
                    <ul>
                        <li>Register and protect your digital identity</li>
                        <li>License your likeness for AI-generated content</li>
                        <li>Earn revenue from your Actor Packs</li>
                        <li>Verify the authenticity of AI content</li>
                    </ul>
                    <p>Get started by registering your first identity:</p>
                    <a href="{settings.FRONTEND_URL}/dashboard/identities/new" class="button">Create Identity</a>
                    <p>If you have any questions, our team is here to help.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {settings.APP_NAME}. All rights reserved.</p>
                    <p><a href="{settings.FRONTEND_URL}">Visit our website</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html)

    async def send_identity_verified_email(
        self,
        to_email: str,
        name: str,
        identity_name: str,
    ) -> bool:
        """Send notification when identity is verified."""
        subject = f"Your Identity '{identity_name}' Has Been Verified"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
                .success {{ background: #d1fae5; padding: 15px; border-radius: 6px; text-align: center; margin: 20px 0; }}
                .button {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Identity Verified ✓</h1>
                </div>
                <div class="content">
                    <h2>Great news, {name}!</h2>
                    <div class="success">
                        <strong>Your identity "{identity_name}" has been successfully verified.</strong>
                    </div>
                    <p>Your identity is now protected and can be used for:</p>
                    <ul>
                        <li>Licensing your likeness for AI content</li>
                        <li>Training Actor Packs for image generation</li>
                        <li>Earning revenue from licensed uses</li>
                    </ul>
                    <a href="{settings.FRONTEND_URL}/dashboard/identities" class="button">View Your Identity</a>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {settings.APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html)

    async def send_training_complete_email(
        self,
        to_email: str,
        name: str,
        identity_name: str,
        quality_score: float,
    ) -> bool:
        """Send notification when Actor Pack training is complete."""
        subject = f"Actor Pack Training Complete for '{identity_name}'"
        quality_display = f"{quality_score:.0f}%" if quality_score else "N/A"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
                .stats {{ background: #f3f4f6; padding: 20px; border-radius: 6px; text-align: center; margin: 20px 0; }}
                .score {{ font-size: 48px; font-weight: bold; color: #8b5cf6; }}
                .button {{ display: inline-block; background: #8b5cf6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Training Complete!</h1>
                </div>
                <div class="content">
                    <h2>Hi {name},</h2>
                    <p>Your Actor Pack for <strong>"{identity_name}"</strong> has finished training and is now available!</p>
                    <div class="stats">
                        <p>Quality Score</p>
                        <div class="score">{quality_display}</div>
                    </div>
                    <p>Your Actor Pack can now be:</p>
                    <ul>
                        <li>Listed on the marketplace for licensing</li>
                        <li>Used to generate AI images of your likeness</li>
                        <li>Downloaded for personal use</li>
                    </ul>
                    <a href="{settings.FRONTEND_URL}/dashboard/actor-packs" class="button">View Actor Pack</a>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {settings.APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html)

    async def send_training_failed_email(
        self,
        to_email: str,
        name: str,
        identity_name: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """Send notification when Actor Pack training fails."""
        subject = f"Actor Pack Training Failed for '{identity_name}'"
        error_text = error_message or "An unexpected error occurred during training."
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
                .error {{ background: #fee2e2; padding: 15px; border-radius: 6px; margin: 20px 0; color: #991b1b; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Training Failed</h1>
                </div>
                <div class="content">
                    <h2>Hi {name},</h2>
                    <p>Unfortunately, the training for your Actor Pack <strong>"{identity_name}"</strong> was not successful.</p>
                    <div class="error">
                        <strong>Error:</strong> {error_text}
                    </div>
                    <p><strong>What you can do:</strong></p>
                    <ul>
                        <li>Ensure your training images are high quality and well-lit</li>
                        <li>Upload at least 10-20 images with varied angles</li>
                        <li>Make sure faces are clearly visible in all images</li>
                        <li>Try restarting the training process</li>
                    </ul>
                    <a href="{settings.FRONTEND_URL}/dashboard/identities" class="button">Try Again</a>
                    <p>If the problem persists, please contact our support team.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {settings.APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html)

    async def send_license_purchase_email(
        self,
        to_email: str,
        name: str,
        identity_name: str,
        license_type: str,
        price: float,
        currency: str = "USD",
    ) -> bool:
        """Send confirmation when user purchases a license."""
        subject = f"License Purchase Confirmed - {identity_name}"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
                .receipt {{ background: #f9fafb; padding: 20px; border-radius: 6px; margin: 20px 0; }}
                .receipt-item {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e5e7eb; }}
                .receipt-total {{ font-weight: bold; font-size: 18px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Purchase Confirmed</h1>
                </div>
                <div class="content">
                    <h2>Thank you, {name}!</h2>
                    <p>Your license purchase has been confirmed.</p>
                    <div class="receipt">
                        <div class="receipt-item">
                            <span>Identity</span>
                            <span>{identity_name}</span>
                        </div>
                        <div class="receipt-item">
                            <span>License Type</span>
                            <span>{license_type}</span>
                        </div>
                        <div class="receipt-item receipt-total">
                            <span>Total</span>
                            <span>${price:.2f} {currency}</span>
                        </div>
                    </div>
                    <a href="{settings.FRONTEND_URL}/dashboard/licenses" class="button">View License</a>
                    <p>You can now use this license to generate AI content with the licensed identity.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {settings.APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html)

    async def send_creator_sale_notification(
        self,
        to_email: str,
        name: str,
        identity_name: str,
        license_type: str,
        earnings: float,
        currency: str = "USD",
    ) -> bool:
        """Send notification to creator when their identity is licensed."""
        subject = f"You made a sale! '{identity_name}' was licensed"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
                .earnings {{ background: #d1fae5; padding: 25px; border-radius: 6px; text-align: center; margin: 20px 0; }}
                .amount {{ font-size: 48px; font-weight: bold; color: #059669; }}
                .button {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>You Made a Sale!</h1>
                </div>
                <div class="content">
                    <h2>Congratulations, {name}!</h2>
                    <p>Someone just licensed your identity <strong>"{identity_name}"</strong>.</p>
                    <div class="earnings">
                        <p>Your Earnings</p>
                        <div class="amount">${earnings:.2f}</div>
                        <p>{license_type} License</p>
                    </div>
                    <p>Your earnings have been added to your balance and will be available for payout according to your payout schedule.</p>
                    <a href="{settings.FRONTEND_URL}/dashboard/analytics" class="button">View Analytics</a>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {settings.APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html)

    async def send_payout_completed_email(
        self,
        to_email: str,
        name: str,
        amount: float,
        currency: str = "USD",
    ) -> bool:
        """Send notification when payout is completed."""
        subject = f"Payout Completed - ${amount:.2f} {currency}"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
                .payout {{ background: #d1fae5; padding: 25px; border-radius: 6px; text-align: center; margin: 20px 0; }}
                .amount {{ font-size: 48px; font-weight: bold; color: #059669; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payout Complete</h1>
                </div>
                <div class="content">
                    <h2>Hi {name},</h2>
                    <p>Your payout has been processed successfully!</p>
                    <div class="payout">
                        <p>Amount Transferred</p>
                        <div class="amount">${amount:.2f}</div>
                        <p>{currency}</p>
                    </div>
                    <p>The funds should arrive in your connected bank account within 2-3 business days.</p>
                    <a href="{settings.FRONTEND_URL}/dashboard/settings" class="button">View Payout History</a>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {settings.APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html)

    async def send_password_reset_email(
        self,
        to_email: str,
        name: str,
        reset_token: str,
    ) -> bool:
        """Send password reset email with token link."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        subject = "Reset Your Password"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
                .warning {{ background: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; color: #92400e; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset</h1>
                </div>
                <div class="content">
                    <h2>Hi {name},</h2>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <a href="{reset_url}" class="button">Reset Password</a>
                    <div class="warning">
                        <strong>Important:</strong> This link will expire in 1 hour. If you didn't request this reset, please ignore this email.
                    </div>
                    <p>If the button doesn't work, copy and paste this URL into your browser:</p>
                    <p style="word-break: break-all; font-size: 12px; color: #666;">{reset_url}</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {settings.APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, html)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
