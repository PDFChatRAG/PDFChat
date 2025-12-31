"""Email service for sending verification codes and notifications."""

import os
import logging
from typing import Optional
import resend

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Resend."""

    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL")
        
        if not self.api_key:
            logger.warning("RESEND_API_KEY not set. Email service will be disabled.")
        else:
            resend.api_key = self.api_key

    def send_verification_code(self, to_email: str, code: str, purpose: str = "password reset") -> bool:
        """Send verification code email.
        
        Args:
            to_email: Recipient email address
            code: Verification code (6 digits)
            purpose: Purpose of the code (default: "password reset")
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.api_key:
            logger.error("Cannot send email: RESEND_API_KEY not configured")
            return False

        subject = f"Your {purpose.title()} Verification Code"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background-color: #007bff; color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px;">PDFChat</h1>
                </div>
                
                <div style="padding: 40px 30px;">
                    <h2 style="color: #333; margin-top: 0;">Verification Code</h2>
                    <p style="color: #666; font-size: 16px; line-height: 1.5;">
                        You requested a {purpose} for your PDFChat account. Use the verification code below:
                    </p>
                    
                    <div style="background-color: #f8f9fa; border: 2px dashed #007bff; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                        <div style="font-size: 42px; font-weight: bold; letter-spacing: 8px; color: #007bff; font-family: 'Courier New', monospace;">
                            {code}
                        </div>
                    </div>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.5;">
                        <strong>This code expires in 10 minutes.</strong>
                    </p>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.5;">
                        If you didn't request this code, please ignore this email. Your account is secure.
                    </p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; text-align: center; border-top: 1px solid #e0e0e0;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                        © 2025 PDFChat. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            params = {
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }
            
            email = resend.Emails.send(params)
            logger.info(f"Verification code email sent to {to_email}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_password_reset_confirmation(self, to_email: str) -> bool:
        """Send password reset confirmation email.
        
        Args:
            to_email: Recipient email address
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.api_key:
            logger.error("Cannot send email: RESEND_API_KEY not configured")
            return False

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background-color: #28a745; color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px;">✓ Password Reset Successful</h1>
                </div>
                
                <div style="padding: 40px 30px;">
                    <p style="color: #666; font-size: 16px; line-height: 1.5;">
                        Your PDFChat password has been successfully reset.
                    </p>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.5;">
                        If you didn't make this change, please contact support immediately.
                    </p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; text-align: center; border-top: 1px solid #e0e0e0;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                        © 2025 PDFChat. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            params = {
                "from": self.from_email,
                "to": [to_email],
                "subject": "Password Reset Confirmation",
                "html": html_content
            }
            
            email = resend.Emails.send(params)
            logger.info(f"Password reset confirmation sent to {to_email}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to send confirmation email to {to_email}: {e}")
            return False
