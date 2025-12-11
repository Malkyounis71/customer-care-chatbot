import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from datetime import datetime
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.enabled = settings.EMAIL_ENABLED
        self.smtp_server = settings.EMAIL_HOST
        self.smtp_port = settings.EMAIL_PORT
        self.use_tls = settings.EMAIL_USE_TLS
        self.username = settings.EMAIL_HOST_USER
        self.password = settings.EMAIL_HOST_PASSWORD
        self.from_email = settings.EMAIL_FROM
        
        
        logger.info(f"📧 Email sender initialized (Enabled: {self.enabled})")
        if self.enabled:
            logger.info(f"   SMTP: {self.smtp_server}:{self.smtp_port}")
            logger.info(f"   From: {self.from_email}")
        
    def test_connection(self):
        """Test SMTP connection to Gmail - ONLY CALLED WHEN NEEDED"""
        if not self.enabled:
            logger.warning("⚠️ Email is disabled in settings")
            return False
            
        try:
            logger.info(f"🔌 Testing Gmail connection...")
            
            # Clean password (remove spaces)
            password_clean = self.password.replace(" ", "") if self.password else ""
            
            # TIMEOUT and handle connection properly
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            server.ehlo()
            
            if self.use_tls:
                server.starttls()
                server.ehlo()
            
            # Try to login
            logger.info(f"🔑 Attempting login to Gmail...")
            server.login(self.username, password_clean)
            server.quit()
            
            logger.info("✅ Gmail connection test SUCCESSFUL!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Gmail connection test FAILED: {e}")
            return False
    
    def send_appointment_confirmation(self, to_email, appointment_data):
        """
        Send appointment confirmation email via Gmail
        Returns: True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("⚠️ Email sending is disabled in settings")
            return False
            
        try:
            logger.info(f"📤 Preparing to send appointment email...")
            logger.info(f"   From: {self.from_email}")
            logger.info(f"   To: {to_email}")
            logger.info(f"   Appointment ID: {appointment_data.get('appointment_id', 'N/A')}")
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = f"✅ Appointment Confirmed - {appointment_data.get('service_type', 'Service')}"
            
            # Get appointment details
            date_str = appointment_data.get('date', '')
            time_str = appointment_data.get('time', '')
            service_type = appointment_data.get('service_type', 'Service')
            customer_name = appointment_data.get('customer_name', 'Customer')
            appointment_id = appointment_data.get('appointment_id', 'N/A')
            
            # HTML Email Content
            html_content = f"""<!DOCTYPE html>
            <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0;">🎉 Appointment Confirmed!</h1>
                    <h3 style="margin: 10px 0 0; opacity: 0.9;">COB Customer Care Chatbot</h3>
                </div>
                <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                    <p>Hello <strong>{customer_name}</strong>,</p>
                    <p>Your appointment has been successfully scheduled!</p>
                    
                    <div style="background: white; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">📋 Appointment Details</h3>
                        <p><strong>Service:</strong> {service_type}</p>
                        <p><strong>Date:</strong> {date_str}</p>
                        <p><strong>Time:</strong> {time_str}</p>
                        <p><strong>Name:</strong> {customer_name}</p>
                        <p><strong>Email:</strong> {to_email}</p>
                    </div>
                    
                    <div style="background: #f0f7ff; border: 2px dashed #667eea; padding: 15px; text-align: center; margin: 20px 0;">
                        <strong style="font-size: 18px;">Appointment ID: {appointment_id}</strong>
                    </div>
                    
                    <p style="text-align: center; color: #666;">
                        We look forward to serving you!<br>
                        <strong>The COB Company Team</strong>
                    </p>
                </div>
                <div style="text-align: center; color: #999; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p>© 2024 COB Company. All rights reserved.</p>
                    <p>This is an automated message. Please do not reply.</p>
                </div>
            </body></html>"""
            
            # Plain text version
            text_content = f"""APPOINTMENT CONFIRMED - COB Customer Care

Hello {customer_name},

Your appointment has been confirmed!

APPOINTMENT DETAILS:
Service: {service_type}
Date: {date_str}
Time: {time_str}
Name: {customer_name}
Email: {to_email}

APPOINTMENT ID: {appointment_id}

We look forward to serving you!

The COB Company Team
© 2024 COB Company. All rights reserved.
Automated message - do not reply."""
            
            # Attach both versions
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Connect to Gmail SMTP
            logger.info(f"🔗 Connecting to Gmail SMTP: {self.smtp_server}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
            server.ehlo()
            
            if self.use_tls:
                logger.info("🔒 Starting TLS encryption...")
                server.starttls()
                server.ehlo()
            
            # Clean password (remove spaces for login)
            password_clean = self.password.replace(" ", "") if self.password else ""
            logger.info(f"🔑 Logging into Gmail...")
            
            server.login(self.username, password_clean)
            logger.info("✅ Gmail login successful!")
            
            # Send email
            logger.info(f"🚀 Sending email to {to_email}...")
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"✅✅✅ Email SENT SUCCESSFULLY to {to_email}")
            logger.info(f"✅ Appointment ID: {appointment_id}")
            logger.info("📧 Check your Gmail inbox (and spam folder)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌❌❌ FAILED to send email: {e}")
            return False
    
    def send_appointment_update(self, to_email, old_appointment, new_appointment):
        """
        Send appointment update confirmation email via Gmail
        Returns: True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("⚠️ Email sending is disabled in settings")
            return False
            
        try:
            logger.info(f"📤 Preparing to send appointment UPDATE email...")
            logger.info(f"   From: {self.from_email}")
            logger.info(f"   To: {to_email}")
            logger.info(f"   Appointment ID: {new_appointment.get('appointment_id', 'N/A')}")
            
            # Get old appointment details
            old_date = old_appointment.get('date', '')
            old_time = old_appointment.get('time', '')
            old_service = old_appointment.get('service_type', 'Service')
            old_name = old_appointment.get('customer_name', 'Customer')
            old_email = old_appointment.get('email', '')
            
            # Get new appointment details
            new_date = new_appointment.get('date', '')
            new_time = new_appointment.get('time', '')
            new_service = new_appointment.get('service_type', 'Service')
            new_name = new_appointment.get('customer_name', 'Customer')
            appointment_id = new_appointment.get('appointment_id', 'N/A')
            
            # Check what changed
            changes = []
            if old_service != new_service:
                changes.append(f"<strong>Service:</strong> {old_service} → <span style='color: #28a745;'>{new_service}</span>")
            if old_date != new_date:
                changes.append(f"<strong>Date:</strong> {old_date} → <span style='color: #28a745;'>{new_date}</span>")
            if old_time != new_time:
                changes.append(f"<strong>Time:</strong> {old_time} → <span style='color: #28a745;'>{new_time}</span>")
            if old_name != new_name:
                changes.append(f"<strong>Name:</strong> {old_name} → <span style='color: #28a745;'>{new_name}</span>")
            if old_email != to_email:
                changes.append(f"<strong>Email:</strong> {old_email} → <span style='color: #28a745;'>{to_email}</span>")
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = f"🔄 Appointment Updated - {new_service}"
            
            # Build changes HTML section
            changes_html = ""
            if changes:
                changes_list = "".join([f"<li>{change}</li>" for change in changes])
                changes_html = f"""<div style="background: #fff3cd; border: 2px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px;">
                    <h4 style="margin-top: 0; color: #856404;">🔄 Changes Made:</h4>
                    <ul style="margin-bottom: 0;">{changes_list}</ul>
                </div>"""
            
            # HTML Email Content - fixed the f-string
            html_content = f"""<!DOCTYPE html>
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #fd7e14 0%, #ffc107 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="margin: 0;">🔄 Appointment Updated!</h1>
        <h3 style="margin: 10px 0 0; opacity: 0.9;">COB Customer Care Chatbot</h3>
    </div>
    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
        <p>Hello <strong>{new_name}</strong>,</p>
        <p>Your appointment has been successfully updated!</p>
        
        <div style="background: white; border-left: 4px solid #fd7e14; padding: 20px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #fd7e14;">📋 Updated Appointment Details</h3>
            <p><strong>Service:</strong> <span style="color: #28a745;">{new_service}</span></p>
            <p><strong>Date:</strong> <span style="color: #28a745;">{new_date}</span></p>
            <p><strong>Time:</strong> <span style="color: #28a745;">{new_time}</span></p>
            <p><strong>Name:</strong> {new_name}</p>
            <p><strong>Email:</strong> {to_email}</p>
        </div>
        
        {changes_html}
        
        <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin: 20px 0; text-align: center;">
            <p style="margin: 0;"><strong>Previous Appointment:</strong></p>
            <p style="margin: 5px 0;">{old_service} on {old_date} at {old_time}</p>
        </div>
        
        <div style="background: #f0f7ff; border: 2px dashed #667eea; padding: 15px; text-align: center; margin: 20px 0;">
            <strong style="font-size: 18px;">Appointment ID: {appointment_id}</strong>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="mailto:support@cobcompany.com" style="background: #fd7e14; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                📞 Contact Support
            </a>
        </div>
        
        <p style="text-align: center; color: #666;">
            We look forward to serving you!<br>
            <strong>The COB Company Team</strong>
        </p>
    </div>
    <div style="text-align: center; color: #999; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
        <p>© 2024 COB Company. All rights reserved.</p>
        <p>This is an automated message. Please do not reply.</p>
    </div>
</body></html>"""
            
            # Plain text version
            changes_text = ""
            if changes:
                clean_changes = []
                for change in changes:
                    clean_change = change.replace("<strong>", "").replace("</strong>", "")
                    clean_change = clean_change.replace("<span style='color: #28a745;'>", "").replace("</span>", "")
                    clean_change = clean_change.replace(" → ", ": ")
                    clean_changes.append(clean_change)
                changes_text = "CHANGES MADE:\n" + "\n".join([f"• {change}" for change in clean_changes])
            
            text_content = f"""APPOINTMENT UPDATED - COB Customer Care

Hello {new_name},

Your appointment has been updated successfully!

UPDATED APPOINTMENT DETAILS:
Service: {new_service}
Date: {new_date}
Time: {new_time}
Name: {new_name}
Email: {to_email}

APPOINTMENT ID: {appointment_id}

PREVIOUS APPOINTMENT:
Service: {old_service}
Date: {old_date}
Time: {old_time}

{changes_text if changes else 'No changes made (all fields remained the same)'}

If you have any questions or need to make further changes, please contact our support team.

We look forward to serving you!

The COB Company Team
© 2024 COB Company. All rights reserved.
Automated message - do not reply."""
            
            # Attach both versions
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Connect to Gmail SMTP
            logger.info(f"🔗 Connecting to Gmail SMTP for update email...")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
            server.ehlo()
            
            if self.use_tls:
                logger.info("🔒 Starting TLS encryption...")
                server.starttls()
                server.ehlo()
            
            # Clean password (remove spaces for login)
            password_clean = self.password.replace(" ", "") if self.password else ""
            logger.info(f"🔑 Logging into Gmail for update...")
            
            server.login(self.username, password_clean)
            logger.info("✅ Gmail login successful for update!")
            
            # Send email
            logger.info(f"🚀 Sending update email to {to_email}...")
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"✅✅✅ Update email SENT SUCCESSFULLY to {to_email}")
            logger.info(f"✅ Appointment ID: {appointment_id}")
            logger.info("📧 Check your Gmail inbox (and spam folder)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌❌❌ FAILED to send update email: {e}")
            return False


email_sender = EmailSender()