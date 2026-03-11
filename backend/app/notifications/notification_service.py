"""Unified notification dispatcher."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification, NotificationType, Task
from app.notifications.email_service import EmailService
from app.notifications.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    async def notify_task_assigned(db: AsyncSession, task: Task, meeting_title: str):
        """Send notification when a task is assigned."""
        if task.responsible_email:
            await EmailService.send_task_assignment(
                to_email=task.responsible_email,
                task_title=task.title,
                meeting_title=meeting_title,
                deadline=str(task.deadline) if task.deadline else None,
            )
            db.add(Notification(
                recipient_email=task.responsible_email,
                message=f"Task assigned: {task.title} (Meeting: {meeting_title})",
                notification_type=NotificationType.EMAIL,
            ))
            await db.flush()

    @staticmethod
    async def notify_deadline_reminder(db: AsyncSession, task: Task):
        if task.responsible_email and task.deadline:
            await EmailService.send_deadline_reminder(
                to_email=task.responsible_email,
                task_title=task.title,
                deadline=str(task.deadline),
            )
            db.add(Notification(
                recipient_email=task.responsible_email,
                message=f"Deadline reminder: {task.title} due {task.deadline}",
                notification_type=NotificationType.EMAIL,
            ))
            await db.flush()

    @staticmethod
    async def notify_overdue(db: AsyncSession, task: Task):
        if task.responsible_email and task.deadline:
            await EmailService.send_overdue_alert(
                to_email=task.responsible_email,
                task_title=task.title,
                deadline=str(task.deadline),
            )
            db.add(Notification(
                recipient_email=task.responsible_email,
                message=f"OVERDUE: {task.title} was due {task.deadline}",
                notification_type=NotificationType.EMAIL,
            ))
            await db.flush()

    @staticmethod
    async def notify_absence_warning(db: AsyncSession, email: str, user_name: str, count: int):
        await EmailService.send_absence_warning(email, user_name, count)
        db.add(Notification(
            recipient_email=email,
            message=f"Attendance warning: {user_name} absent {count} times",
            notification_type=NotificationType.EMAIL,
        ))
        await db.flush()

    @staticmethod
    async def notify_meeting_invitation(db: AsyncSession, email: str, user_name: str, meeting_title: str, date: str, time: str, venue: str):
        if email:
            await EmailService.send_meeting_invitation(email, user_name, meeting_title, date, time, venue)
            db.add(Notification(
                recipient_email=email,
                message=f"Invited to meeting: {meeting_title} on {date}",
                notification_type=NotificationType.EMAIL,
            ))
            await db.flush()

    @staticmethod
    async def notify_meeting_summary(db: AsyncSession, email: str, user_name: str, meeting_title: str, is_absent: bool, summary: str, task_html: str, pdf_data: bytes = None, pdf_name: str = None, remarks: str = None):
        if email:
            await EmailService.send_meeting_summary(email, user_name, meeting_title, is_absent, summary, task_html, pdf_data=pdf_data, pdf_name=pdf_name, remarks=remarks)
            db.add(Notification(
                recipient_email=email,
                message=f"Received MOM for meeting: {meeting_title}",
                notification_type=NotificationType.EMAIL,
            ))
            await db.flush()


    @staticmethod
    async def list_notifications(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Notification]:
        from sqlalchemy import select
        result = await db.execute(
            select(Notification).order_by(Notification.sent_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def mark_read(db: AsyncSession, notification_id: int) -> bool:
        from sqlalchemy import select
        result = await db.execute(select(Notification).where(Notification.id == notification_id))
        notif = result.scalar_one_or_none()
        if not notif:
            return False
        notif.is_read = True
        await db.flush()
        return True
