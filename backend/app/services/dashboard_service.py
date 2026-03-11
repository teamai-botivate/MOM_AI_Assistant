"""Dashboard / analytics service."""

from datetime import date, timedelta, datetime

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Meeting, Task, TaskStatus, User
from app.schemas.schemas import (
    DashboardStats, TaskStatusDistribution, MeetingTrend,
    MeetingListResponse, TaskResponse, AnalyticsResponse, MeetingResponse
)
from app.services.task_service import TaskService
from app.services.meeting_service import MeetingService
from app.services.user_service import UserService


class DashboardService:

    @staticmethod
    async def get_dashboard(db: AsyncSession) -> AnalyticsResponse:
        total_meetings = await MeetingService.count_meetings(db)
        status_counts = await TaskService.count_by_status(db)

        total_tasks = sum(status_counts.values())
        pending = status_counts.get(TaskStatus.PENDING.value, 0)
        in_progress = status_counts.get(TaskStatus.IN_PROGRESS.value, 0)
        completed = status_counts.get(TaskStatus.COMPLETED.value, 0)

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
                task_count=len(m.tasks) if m.tasks else 0,
            )
            for m in recent
        ]

        # Task distribution
        distribution = [
            TaskStatusDistribution(status=s, count=c) for s, c in status_counts.items()
        ]

        # Meeting trends (last 6 months)
        trends = []
        today = date.today()
        import calendar
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            result = await db.execute(
                select(func.count(Meeting.id))
                .where(
                    extract("month", Meeting.date) == m,
                    extract("year", Meeting.date) == y,
                )
            )
            # Create e.g. "Mar 2026"
            month_name = f"{calendar.month_abbr[m]} {y}"
            trends.append(MeetingTrend(month=month_name, count=result.scalar() or 0))

        overdue_resp = [
            TaskResponse.model_validate(t) for t in overdue_list
        ]

        # Latest past meeting and nearest upcoming meeting
        last_meeting = None
        nearest_upcoming = None
        
        # We can find this efficiently:
        today_date = date.today()
        time_now = datetime.now().time()
        
        # nearest upcoming
        nearest_res = await db.execute(
            select(Meeting)
            .where((Meeting.date > today_date) | ((Meeting.date == today_date) & (Meeting.time >= time_now)))
            .order_by(Meeting.date.asc(), Meeting.time.asc())
            .limit(1)
        )
        nearest = nearest_res.scalar_one_or_none()
        if nearest:
            # Re-fetch with full associations
            nearest = await MeetingService.get_meeting(db, nearest.id)
            nearest_upcoming = MeetingResponse.model_validate(nearest)

        # last meeting
        last_res = await db.execute(
            select(Meeting)
            .where((Meeting.date < today_date) | ((Meeting.date == today_date) & (Meeting.time < time_now)))
            .order_by(Meeting.date.desc(), Meeting.time.desc())
            .limit(1)
        )
        last = last_res.scalar_one_or_none()
        if last:
            # Re-fetch with full associations
            last = await MeetingService.get_meeting(db, last.id)
            last_meeting = MeetingResponse.model_validate(last)

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
            nearest_upcoming_meeting=nearest_upcoming,
            last_meeting=last_meeting,
        )
