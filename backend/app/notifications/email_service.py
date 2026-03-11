"""Email notification service using aiosmtplib."""

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

def get_base_template(title: str, content: str) -> str:
    """Returns a professional Botivate-branded HTML template."""
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <!-- Header Ribbon -->
            <tr>
                <td style="height: 6px; background: linear-gradient(90deg, #60a5fa 0%, #4f46e5 100%); line-height: 6px; font-size: 6px;">&nbsp;</td>
            </tr>
            <!-- Header Content -->
            <tr>
                <td style="padding: 30px 40px; border-bottom: 2px solid #f1f5f9;">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%">
                        <tr>
                            <td>
                                <h1 style="margin: 0; font-size: 24px; color: #1e293b; letter-spacing: -0.5px;">Botivate</h1>
                                <p style="margin: 4px 0 0; font-size: 13px; color: #64748b; font-style: italic;">Powering Businesses On Autopilot</p>
                            </td>
                            <td align="right" style="text-align: right;">
                                <h2 style="margin: 0; font-size: 12px; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">Botivate Services LLP</h2>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <!-- Main Content Area -->
            <tr>
                <td style="padding: 40px;">
                    <h2 style="margin: 0 0 24px; color: #3b82f6; font-size: 20px; font-weight: 600;">{title}</h2>
                    {content}
                </td>
            </tr>
            <!-- Footer Area -->
            <tr>
                <td style="padding: 30px 40px; background-color: #f8fafc; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; color: #64748b; font-size: 13px; text-align: center;">
                        This is an automated notification from the <strong>Botivate MOM Management System</strong>.<br>
                        Please do not reply directly to this email.
                    </p>
                </td>
            </tr>
            <!-- Bottom Ribbon -->
            <tr>
                <td style="height: 6px; background: linear-gradient(90deg, #4f46e5 0%, #60a5fa 100%); line-height: 6px; font-size: 6px;">&nbsp;</td>
            </tr>
        </table>
    </body>
    </html>
    """

class EmailService:

    @staticmethod
    async def send_email(to_email: str, subject: str, body_html: str, attachment_data: bytes = None, attachment_name: str = None) -> bool:
        """Send an HTML email via SMTP, with optional attachment. Returns True on success."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured – skipping email to %s", to_email)
            return False

        message = MIMEMultipart("mixed")
        message["From"] = settings.EMAIL_FROM
        message["To"] = to_email
        message["Subject"] = subject
        
        # Attach the HTML body part using an alternative wrapper if needed, but simple attaching to mixed works too
        body_part = MIMEText(body_html, "html")
        message.attach(body_part)
        
        if attachment_data and attachment_name:
            part = MIMEApplication(attachment_data)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment_name}"')
            message.attach(part)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                start_tls=True,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
            )
            logger.info("Email sent to %s: %s", to_email, subject)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            return False

    @staticmethod
    async def send_task_assignment(to_email: str, task_title: str, meeting_title: str, deadline: str | None):
        subject = f"New Task Assigned: {task_title}"
        content = f"""
            <p style="font-size: 16px; color: #475569; margin: 0 0 16px;">Dear Team Member,</p>
            <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0 0 24px;">You have been assigned a new task from the meeting <strong>{meeting_title}</strong>.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px; background-color: #f1f5f9; border-radius: 6px; overflow: hidden;">
                <tr>
                    <td style="padding: 12px 16px; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0; width: 100px;">Task</td>
                    <td style="padding: 12px 16px; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{task_title}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 16px; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0;">Meeting</td>
                    <td style="padding: 12px 16px; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{meeting_title}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 16px; font-weight: 600; color: #475569;">Deadline</td>
                    <td style="padding: 12px 16px; color: #0f172a; font-weight: 600;">{deadline or 'Not specified'}</td>
                </tr>
            </table>
            
            <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0;">Please contact the HR Department for any updates or clarifications regarding this task.</p>
        """
        html = get_base_template("New Task Assignment", content)
        await EmailService.send_email(to_email, subject, html)

    @staticmethod
    async def send_deadline_reminder(to_email: str, task_title: str, deadline: str):
        subject = f"Reminder: Task '{task_title}' deadline approaching"
        content = f"""
            <p style="font-size: 16px; color: #475569; margin: 0 0 16px;">Dear Team Member,</p>
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 4px; margin-bottom: 24px;">
                <p style="font-size: 15px; color: #92400e; margin: 0;">This is a friendly reminder that your task <strong>{task_title}</strong> is due on <strong>{deadline}</strong>.</p>
            </div>
            <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0;">Please ensure it is completed on time. If you require any assistance or an extension, please reach out to the HR Department proactively.</p>
        """
        html = get_base_template("Task Deadline Reminder", content)
        html = html.replace('color: #3b82f6;', 'color: #d97706;') # Change title color to amber
        await EmailService.send_email(to_email, subject, html)

    @staticmethod
    async def send_overdue_alert(to_email: str, task_title: str, deadline: str):
        subject = f"OVERDUE: Task '{task_title}'"
        content = f"""
            <p style="font-size: 16px; color: #475569; margin: 0 0 16px;">Dear Team Member,</p>
            <div style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 16px; border-radius: 4px; margin-bottom: 24px;">
                <p style="font-size: 15px; color: #991b1b; margin: 0;"><strong>Critical Alert:</strong> Your task <strong>{task_title}</strong> was due on <strong>{deadline}</strong> and is currently marked as overdue.</p>
            </div>
            <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0;">Kindly contact the HR Department immediately to provide a status update on this pending item.</p>
        """
        html = get_base_template("Overdue Task Alert", content)
        html = html.replace('color: #3b82f6;', 'color: #ef4444;') # Change title color to red
        await EmailService.send_email(to_email, subject, html)

    @staticmethod
    async def send_absence_warning(to_email: str, user_name: str, absent_count: int):
        subject = f"Attendance Notice: {user_name}"
        content = f"""
            <p style="font-size: 16px; color: #475569; margin: 0 0 16px;">Dear HR / Management,</p>
            <div style="background-color: #f1f5f9; padding: 16px; border-radius: 6px; margin-bottom: 24px;">
                <p style="font-size: 15px; color: #334155; margin: 0;">This is an automated notice regarding meeting attendance.</p>
                <p style="font-size: 15px; color: #0f172a; margin: 12px 0 0; font-weight: 500;">
                    Team member <span style="color: #4f46e5;">{user_name}</span> has been marked absent from <span style="color: #ef4444; font-weight: 600;">{absent_count}</span> scheduled meetings.
                </p>
            </div>
            <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0;">Please review their attendance record and take necessary administrative actions.</p>
        """
        html = get_base_template("Attendance Notice", content)
        html = html.replace('color: #3b82f6;', 'color: #8b5cf6;') # Change title color to purple
        await EmailService.send_email(to_email, subject, html)

    @staticmethod
    async def send_meeting_invitation(to_email: str, recipient_name: str, meeting_title: str, date: str, time: str, venue: str):
        subject = f"Meeting Invitation: {meeting_title}"
        content = f"""
            <p style="font-size: 16px; color: #475569; margin: 0 0 16px;">Dear {recipient_name},</p>
            <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0 0 24px;">You have been officially invited to the upcoming scheduled meeting.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;">
                <tr>
                    <td colspan="2" style="background-color: #f8fafc; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #0f172a; font-size: 16px;">
                        {meeting_title}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px 16px; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0; width: 120px;">Date</td>
                    <td style="padding: 12px 16px; color: #0f172a; border-bottom: 1px solid #e2e8f0;"><strong>{date}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 12px 16px; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0;">Time</td>
                    <td style="padding: 12px 16px; color: #0f172a; border-bottom: 1px solid #e2e8f0;"><strong>{time}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 12px 16px; font-weight: 600; color: #475569;">Venue / Link</td>
                    <td style="padding: 12px 16px; color: #0f172a;">{venue}</td>
                </tr>
            </table>
            
            <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0;">Please mark your calendar appropriately. We look forward to your valuable presence and contribution.</p>
        """
        html = get_base_template("Meeting Invitation", content)
        await EmailService.send_email(to_email, subject, html)

    @staticmethod
    async def send_meeting_summary(to_email: str, recipient_name: str, meeting_title: str, is_absent: bool, summary: str, task_html: str, pdf_data: bytes = None, pdf_name: str = None, remarks: str = None):
        subject = f"MOM & Summary: {meeting_title}"
        
        if is_absent:
            greeting_box = f"""
            <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 16px; margin-bottom: 24px;">
                <p style="font-size: 14px; color: #991b1b; margin: 0;"><strong>Note:</strong> You were marked absent in this meeting. Please review the proceedings below to stay updated.</p>
            </div>
            """
        else:
            greeting_box = f"""
            <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0 0 24px;">Please find the Minutes of Meeting (MOM) and summary for our recent discussion.</p>
            """
            
        styled_task_html = task_html.replace(
            '<table border="1"', '<table style="width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; text-align: left;"'
        ).replace(
            '<th', '<th style="background-color: #f1f5f9; padding: 10px; border: 1px solid #cbd5e1; color: #334155;"'
        ).replace(
            '<td', '<td style="padding: 10px; border: 1px solid #e2e8f0; color: #1e293b;"'
        )
        
        attachment_notice = ""
        if pdf_data:
            attachment_notice = """
            <div style="margin-top: 24px; padding: 16px; background-color: #f0fdf4; border-left: 4px solid #22c55e; border-radius: 4px;">
                <p style="font-size: 14px; color: #166534; margin: 0;"><strong>Attached:</strong> You will find the complete, officially formatted MOM PDF attached to this email. You can download it directly.</p>
            </div>
            """

        remarks_html = ""
        if remarks:
            remarks_html = f"""
            <h3 style="color: #1e293b; font-size: 16px; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid #e0f2fe;">Personal Remarks specifically for you</h3>
            <div style="background-color: #f0f9ff; padding: 16px; border-radius: 6px; margin-bottom: 24px; border: 1px solid #bae6fd;">
                <p style="margin: 0; font-size: 14px; color: #0369a1; line-height: 1.6; white-space: pre-wrap;"><strong>HR/Admin Note:</strong> {remarks}</p>
            </div>
            """

        content = f"""
            <p style="font-size: 16px; color: #475569; margin: 0 0 16px;">Dear {recipient_name},</p>
            {greeting_box}
            
            {remarks_html}
            
            <h3 style="color: #1e293b; font-size: 16px; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0;">Discussion Summary</h3>
            <div style="background-color: #f8fafc; padding: 16px; border-radius: 6px; margin-bottom: 24px; border: 1px solid #e2e8f0;">
                <p style="margin: 0; font-size: 14px; color: #334155; line-height: 1.6; white-space: pre-wrap;">{summary or 'No formal summary was documented.'}</p>
            </div>
            
            <h3 style="color: #1e293b; font-size: 16px; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0;">Action Items</h3>
            {styled_task_html}
            {attachment_notice}
        """
        html = get_base_template(f"MOM: {meeting_title}", content)
        await EmailService.send_email(to_email, subject, html, attachment_data=pdf_data, attachment_name=pdf_name)
