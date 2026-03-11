"""SQLAlchemy ORM models for the MOM AI Assistant."""

import enum
from datetime import datetime, date, time

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, Time,
    ForeignKey, Enum as SAEnum, Boolean,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


# ── Enums ──────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    CEO = "CEO"
    MANAGER = "Manager"
    HR = "HR"
    EMPLOYEE = "Employee"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "Present"
    ABSENT = "Absent"
    EXCUSED = "Excused"


class TaskStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


class NotificationType(str, enum.Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"


# ── Models ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    notifications = relationship("Notification", back_populates="user")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    organization = Column(String(255), nullable=True)
    meeting_type = Column(String(100), nullable=True)
    meeting_mode = Column(String(50), nullable=True)  # Online or Offline
    date = Column(Date, nullable=True)
    time = Column(Time, nullable=True)
    venue = Column(String(255), nullable=True)
    hosted_by = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    attendees = relationship("Attendee", back_populates="meeting", cascade="all, delete-orphan")
    agenda_items = relationship("AgendaItem", back_populates="meeting", cascade="all, delete-orphan")
    discussion = relationship("DiscussionSummary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="meeting", cascade="all, delete-orphan")
    next_meeting = relationship("NextMeeting", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    files = relationship("File", back_populates="meeting", cascade="all, delete-orphan")


class Attendee(Base):
    __tablename__ = "attendees"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    user_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    designation = Column(String(255), nullable=True)
    whatsapp_number = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)
    attendance_status = Column(SAEnum(AttendanceStatus), default=AttendanceStatus.PRESENT)

    meeting = relationship("Meeting", back_populates="attendees")


class AgendaItem(Base):
    __tablename__ = "agenda_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    topic = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="agenda_items")


class DiscussionSummary(Base):
    __tablename__ = "discussion_summary"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=False)

    meeting = relationship("Meeting", back_populates="discussion")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    responsible_person = Column(String(255), nullable=True)
    responsible_email = Column(String(255), nullable=True)
    deadline = Column(Date, nullable=True)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="tasks")
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")


class TaskHistory(Base):
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    previous_status = Column(SAEnum(TaskStatus), nullable=True)
    new_status = Column(SAEnum(TaskStatus), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(String(255), nullable=True)

    task = relationship("Task", back_populates="history")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    notification_type = Column(SAEnum(NotificationType), default=NotificationType.EMAIL)
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class NextMeeting(Base):
    __tablename__ = "next_meetings"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, unique=True)
    next_date = Column(Date, nullable=True)
    next_time = Column(Time, nullable=True)

    meeting = relationship("Meeting", back_populates="next_meeting")


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="files")
