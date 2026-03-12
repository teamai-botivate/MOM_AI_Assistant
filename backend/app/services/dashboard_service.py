"""Dashboard / analytics service – reads from Google Sheets."""

from datetime import date, datetime
import calendar
import logging

from app.services.google_sheets_service import SheetsDB, _to_int
from app.services.meeting_service import (
    MeetingService, _row_to_meeting_obj, _row_to_task,
    _parse_date, _parse_time, _load_meeting_relations, DotDict,
)
from app.services.task_service import TaskService
from app.services.user_service import UserService

from app.schemas.schemas import (
    DashboardStats, TaskStatusDistribution, MeetingTrend,
    MeetingListResponse, TaskResponse, AnalyticsResponse, MeetingResponse,
)

logger = logging.getLogger(__name__)


class DashboardService:

    @staticmethod
    async def get_dashboard(db) -> AnalyticsResponse:
        total_meetings = await MeetingService.count_meetings(db)
        status_counts = await TaskService.count_by_status(db)

        total_tasks = sum(status_counts.values())
        pending = status_counts.get("Pending", 0)
        in_progress = status_counts.get("In Progress", 0)
        completed = status_counts.get("Completed", 0)

        overdue_list = await TaskService.overdue_tasks(db)
        upcoming = await MeetingService.upcoming_meetings(db)
        total_users = await UserService.count_users(db)

        # Recent meetings
        recent = await MeetingService.list_meetings(db, limit=5)
        recent_resp = [
            MeetingListResponse(
                id=m.id,
                title=m.title,
                organization=m.organization,
                date=m.date,
                time=m.time,
                venue=m.venue,
                created_at=m.created_at,
                task_count=len(m.tasks) if hasattr(m, 'tasks') and m.tasks else 0,
                status=m.status,
                pdf_link=m.pdf_link,
                recording_link=m.recording_link,
            )
            for m in recent
        ]

        # Task distribution
        distribution = [
            TaskStatusDistribution(status=s, count=c) for s, c in status_counts.items()
        ]

        # Meeting trends (last 6 months)
        all_meetings = SheetsDB.get_all("Meetings")
        trends = []
        today = date.today()
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            month_count = 0
            for mtg in all_meetings:
                d = _parse_date(mtg.get("date"))
                if d and d.month == m and d.year == y:
                    month_count += 1
            month_name = f"{calendar.month_abbr[m]} {y}"
            trends.append(MeetingTrend(month=month_name, count=month_count))

        overdue_resp = []
        for t in overdue_list:
            overdue_resp.append(TaskResponse(
                id=t.id, meeting_id=t.meeting_id, title=t.title,
                description=t.description, responsible_person=t.responsible_person,
                responsible_email=t.responsible_email, deadline=t.deadline,
                status=t.status, created_at=t.created_at,
            ))

        # Nearest upcoming and last meeting
        today_date = date.today()
        time_now = datetime.now().time()
        nearest_upcoming = None
        last_meeting = None

        for mtg in all_meetings:
            d = _parse_date(mtg.get("date"))
            t = _parse_time(mtg.get("time"))
            if d:
                if d > today_date or (d == today_date and t and t >= time_now):
                    # Candidates for upcoming
                    if nearest_upcoming is None:
                        nearest_upcoming = mtg
                    else:
                        nd = _parse_date(nearest_upcoming.get("date"))
                        nt = _parse_time(nearest_upcoming.get("time"))
                        if d < nd or (d == nd and t and nt and t < nt):
                            nearest_upcoming = mtg
                elif d < today_date or (d == today_date and t and t < time_now):
                    if last_meeting is None:
                        last_meeting = mtg
                    else:
                        ld = _parse_date(last_meeting.get("date"))
                        lt = _parse_time(last_meeting.get("time"))
                        if d > ld or (d == ld and t and lt and t > lt):
                            last_meeting = mtg

        nearest_resp = None
        if nearest_upcoming:
            mid = _to_int(str(nearest_upcoming.get("id", "")))
            if mid:
                m_obj = await MeetingService.get_meeting(db, mid)
                if m_obj:
                    nearest_resp = _meeting_obj_to_response(m_obj)

        last_resp = None
        if last_meeting:
            mid = _to_int(str(last_meeting.get("id", "")))
            if mid:
                m_obj = await MeetingService.get_meeting(db, mid)
                if m_obj:
                    last_resp = _meeting_obj_to_response(m_obj)

        return AnalyticsResponse(
            stats=DashboardStats(
                total_meetings=total_meetings,
                total_tasks=total_tasks,
                pending_tasks=pending,
                in_progress_tasks=in_progress,
                completed_tasks=completed,
                overdue_tasks=len(overdue_list),
                upcoming_meetings=len(upcoming),
                total_users=total_users,
            ),
            task_distribution=distribution,
            meeting_trends=trends,
            recent_meetings=recent_resp,
            overdue_tasks=overdue_resp,
            nearest_upcoming_meeting=nearest_resp,
            last_meeting=last_resp,
        )


def _meeting_obj_to_response(m) -> MeetingResponse:
    """Convert a DotDict meeting object to MeetingResponse schema."""
    from app.schemas.schemas import (
        AttendeeResponse, AgendaItemResponse, DiscussionResponse,
        TaskResponse as TR, NextMeetingResponse, FileResponse,
    )

    attendees_resp = [
        AttendeeResponse(
            id=a.id, meeting_id=a.meeting_id, user_name=a.user_name,
            email=a.email, designation=a.designation,
            whatsapp_number=a.whatsapp_number, remarks=a.remarks,
            attendance_status=a.attendance_status,
        ) for a in (m.attendees or [])
    ]
    agenda_resp = [
        AgendaItemResponse(
            id=a.id, meeting_id=a.meeting_id, topic=a.topic, description=a.description,
        ) for a in (m.agenda_items or [])
    ]
    disc_resp = None
    if m.discussion:
        disc_resp = DiscussionResponse(
            id=m.discussion.id, meeting_id=m.discussion.meeting_id,
            summary_text=m.discussion.summary_text,
        )
    tasks_resp = [
        TR(
            id=t.id, meeting_id=t.meeting_id, title=t.title,
            description=t.description, responsible_person=t.responsible_person,
            responsible_email=t.responsible_email, deadline=t.deadline,
            status=t.status, created_at=t.created_at,
        ) for t in (m.tasks or [])
    ]
    nm_resp = None
    if m.next_meeting:
        nm_resp = NextMeetingResponse(
            id=m.next_meeting.id, meeting_id=m.next_meeting.meeting_id,
            next_date=m.next_meeting.next_date, next_time=m.next_meeting.next_time,
        )
    
    files_resp = [
        FileResponse(
            id=f.id, meeting_id=f.meeting_id, file_path=f.file_path,
            file_type=f.file_type, uploaded_at=f.uploaded_at,
        ) for f in (getattr(m, 'supporting_documents', []) or [])
    ]

    return MeetingResponse(
        id=m.id, title=m.title, organization=m.organization,
        meeting_type=m.meeting_type, meeting_mode=m.meeting_mode,
        date=m.date, time=m.time, venue=m.venue, hosted_by=m.hosted_by,
        file_path=m.file_path, created_by=m.created_by, created_at=m.created_at,
        attendees=attendees_resp, agenda_items=agenda_resp,
        discussion=disc_resp, tasks=tasks_resp, next_meeting=nm_resp,
        status=m.status,
        pdf_link=getattr(m, 'pdf_link', None),
        drive_file_id=getattr(m, 'drive_file_id', None),
        drive_folder_id=getattr(m, 'drive_folder_id', None),
        recording_link=getattr(m, 'recording_link', None),
        drive_recording_id=getattr(m, 'drive_recording_id', None),
        drive_transcript_id=getattr(m, 'drive_transcript_id', None),
        ai_summary_link=getattr(m, 'ai_summary_link', None),
        supporting_documents=files_resp
    )
