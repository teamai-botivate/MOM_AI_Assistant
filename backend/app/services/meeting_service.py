"""Meeting service – CRUD + creation from extracted MOM data."""

from datetime import date, time, datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import (
    Meeting, Attendee, AgendaItem, DiscussionSummary,
    Task, NextMeeting, File, TaskStatus, AttendanceStatus,
)
from app.schemas.schemas import MeetingCreate, ExtractedMOM, MeetingMOMUpdate


class MeetingService:

    @staticmethod
    async def create_meeting(db: AsyncSession, data: MeetingCreate, created_by: int | None = None) -> Meeting:
        import logging
        logger = logging.getLogger("meeting_service")
        logger.info("Creating meeting with data: %s", data.dict())
        meeting = Meeting(
            title=data.title,
            organization=data.organization,
            meeting_type=data.meeting_type,
            meeting_mode=data.meeting_mode,
            date=data.date,
            time=data.time,
            venue=data.venue,
            hosted_by=data.hosted_by,
            created_by=created_by,
        )
        db.add(meeting)
        await db.flush()

        # Attendees
        for att in data.attendees:
            logger.info("Adding attendee: %s", att)
            db.add(Attendee(
                meeting_id=meeting.id,
                user_name=att.user_name,
                email=att.email,
                designation=att.designation,
                whatsapp_number=att.whatsapp_number,
                remarks=att.remarks,
                attendance_status=att.attendance_status,
            ))

        # Agenda
        for ag in data.agenda_items:
            logger.info("Adding agenda item: %s", ag)
            db.add(AgendaItem(meeting_id=meeting.id, topic=ag.topic, description=ag.description))

        # Discussion
        if data.discussion_summary:
            logger.info("Adding discussion summary: %s", data.discussion_summary)
            db.add(DiscussionSummary(meeting_id=meeting.id, summary_text=data.discussion_summary))

        # Tasks
        for t in data.tasks:
            logger.info("Adding task: %s", t)
            db.add(Task(
                meeting_id=meeting.id,
                title=t.title,
                description=t.description,
                responsible_person=t.responsible_person,
                responsible_email=t.responsible_email,
                deadline=t.deadline,
                status=t.status,
            ))

        # Next meeting
        if data.next_meeting:
            logger.info("Adding next meeting: %s", data.next_meeting)
            db.add(NextMeeting(
                meeting_id=meeting.id,
                next_date=data.next_meeting.next_date,
                next_time=data.next_meeting.next_time,
            ))

        await db.flush()
        await db.refresh(meeting)
        logger.info("Meeting fully created and refreshed: %s", meeting)
        return meeting

    @staticmethod
    async def create_from_extraction(db: AsyncSession, extracted: ExtractedMOM, created_by: int | None = None, file_path: str | None = None) -> Meeting:
        """Build a Meeting record from AI-extracted MOM data."""

        def _parse_date(s: str | None) -> date | None:
            if not s:
                return None
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"):
                try:
                    return datetime.strptime(s.strip(), fmt).date()
                except ValueError:
                    continue
            return None

        def _parse_time(s: str | None) -> time | None:
            if not s:
                return None
            for fmt in ("%H:%M", "%I:%M %p", "%H:%M:%S"):
                try:
                    return datetime.strptime(s.strip(), fmt).time()
                except ValueError:
                    continue
            return None

        meeting = Meeting(
            title=extracted.meeting_title or "Untitled Meeting",
            organization=extracted.organization_name,
            meeting_type=extracted.meeting_type,
            meeting_mode=extracted.meeting_mode,
            date=_parse_date(extracted.date),
            time=_parse_time(extracted.time),
            venue=extracted.venue,
            hosted_by=extracted.hosted_by,
            file_path=file_path,
            created_by=created_by,
        )
        db.add(meeting)
        await db.flush()

        # Attendees
        for p in extracted.attendees:
            db.add(Attendee(
                meeting_id=meeting.id,
                user_name=p.name,
                email=p.email,
                designation=p.designation,
                whatsapp_number=p.whatsapp_number,
                remarks=p.remarks,
                attendance_status=AttendanceStatus.PRESENT,
            ))
        for p in extracted.absentees:
            db.add(Attendee(
                meeting_id=meeting.id,
                user_name=p.name,
                email=p.email,
                designation=p.designation,
                whatsapp_number=p.whatsapp_number,
                remarks=p.remarks,
                attendance_status=AttendanceStatus.ABSENT,
            ))

        # Agenda
        for ag in extracted.agenda:
            db.add(AgendaItem(meeting_id=meeting.id, topic=ag.topic, description=ag.description))

        # Discussion
        if extracted.discussion_summary:
            db.add(DiscussionSummary(meeting_id=meeting.id, summary_text=extracted.discussion_summary))

        # Build attendee email map
        attendee_email_map = {p.name: p.email for p in extracted.attendees if p.email}

        # Tasks
        for item in extracted.action_items:
            email = attendee_email_map.get(item.responsible_person)
            db.add(Task(
                meeting_id=meeting.id,
                title=item.task,
                responsible_person=item.responsible_person,
                responsible_email=email,
                deadline=_parse_date(item.deadline),
                status=TaskStatus.PENDING,
            ))

        # Next meeting
        nd = _parse_date(extracted.next_meeting_date)
        nt = _parse_time(extracted.next_meeting_time)
        if nd or nt:
            db.add(NextMeeting(meeting_id=meeting.id, next_date=nd, next_time=nt))

        # File reference
        if file_path:
            ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "unknown"
            db.add(File(meeting_id=meeting.id, file_path=file_path, file_type=ext))

        await db.flush()
        await db.refresh(meeting)
        return meeting

    @staticmethod
    async def get_meeting(db: AsyncSession, meeting_id: int) -> Meeting | None:
        result = await db.execute(
            select(Meeting)
            .options(
                selectinload(Meeting.attendees),
                selectinload(Meeting.agenda_items),
                selectinload(Meeting.discussion),
                selectinload(Meeting.tasks),
                selectinload(Meeting.next_meeting),
                selectinload(Meeting.files),
            )
            .where(Meeting.id == meeting_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def add_mom_to_meeting(db: AsyncSession, meeting_id: int, data: MeetingMOMUpdate) -> Meeting | None:
        meeting = await MeetingService.get_meeting(db, meeting_id)
        if not meeting:
            return None

        # Update Attendees Statuses
        attendee_dict = {a.id: a for a in meeting.attendees}
        for update_a in data.attendees:
            if update_a.id in attendee_dict:
                attendee_dict[update_a.id].attendance_status = update_a.attendance_status

        # Add/Update Discussion
        if data.discussion_summary:
            if meeting.discussion:
                meeting.discussion.summary_text = data.discussion_summary
            else:
                db.add(DiscussionSummary(meeting_id=meeting.id, summary_text=data.discussion_summary))

        # Tasks
        for t in data.tasks:
            db.add(Task(
                meeting_id=meeting.id,
                title=t.title,
                description=t.description,
                responsible_person=t.responsible_person,
                responsible_email=t.responsible_email,
                deadline=t.deadline,
                status=t.status,
            ))

        # Next meeting
        if data.next_meeting:
            if meeting.next_meeting:
                meeting.next_meeting.next_date = data.next_meeting.next_date
                meeting.next_meeting.next_time = data.next_meeting.next_time
            else:
                db.add(NextMeeting(
                    meeting_id=meeting.id,
                    next_date=data.next_meeting.next_date,
                    next_time=data.next_meeting.next_time,
                ))

        await db.flush()
        await db.refresh(meeting)
        return await MeetingService.get_meeting(db, meeting_id)


    @staticmethod
    async def list_meetings(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Meeting]:
        result = await db.execute(
            select(Meeting)
            .options(selectinload(Meeting.tasks))
            .order_by(Meeting.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_meeting(db: AsyncSession, meeting_id: int) -> bool:
        meeting = await MeetingService.get_meeting(db, meeting_id)
        if not meeting:
            return False
        await db.delete(meeting)
        await db.flush()
        return True

    @staticmethod
    async def count_meetings(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(Meeting.id)))
        return result.scalar() or 0

    @staticmethod
    async def upcoming_meetings(db: AsyncSession, limit: int = 5) -> list[Meeting]:
        today = date.today()
        result = await db.execute(
            select(Meeting)
            .where(Meeting.date >= today)
            .order_by(Meeting.date.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
