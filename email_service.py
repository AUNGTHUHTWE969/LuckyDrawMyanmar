import smtplib
import logging
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import config

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.email_address = config.EMAIL_ADDRESS
        self.email_password = config.EMAIL_PASSWORD
    
    def send_email(self, to_email, subject, body):
        """Send email"""
        try:
            # Create message
            msg = MimeMultipart()
            msg['From'] = self.email_address
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MimeText(body, 'html'))
            
            # Create server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.email_address, to_email, text)
            server.quit()
            
            logger.info(f"Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_password_reset_email(self, to_email, reset_token):
        """Send password reset email"""
        subject = "LUCKY DRAW MYANMAR - Password Reset Request"
        
        body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You have requested to reset your password for LUCKY DRAW MYANMAR account.</p>
            <p>Please use the following token to reset your password:</p>
            <div style="background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-family: monospace;">
                <strong>{reset_token}</strong>
            </div>
            <p>This token will expire in 1 hour.</p>
            <p>If you did not request this reset, please ignore this email.</p>
            <br>
            <p>Best regards,<br>LUCKY DRAW MYANMAR Team</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, body)
    
    def send_email_verification(self, to_email, verification_token):
        """Send email verification"""
        subject = "LUCKY DRAW MYANMAR - Verify Your Email Address"
        
        body = f"""
        <html>
        <body>
            <h2>Email Verification</h2>
            <p>Thank you for registering with LUCKY DRAW MYANMAR!</p>
            <p>Please use the following verification code to verify your email address:</p>
            <div style="background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 18px;">
                <strong>{verification_token}</strong>
            </div>
            <p>This code will expire in 24 hours.</p>
            <br>
            <p>Best regards,<br>LUCKY DRAW MYANMAR Team</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, body)
