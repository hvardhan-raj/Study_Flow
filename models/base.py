from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    DDL,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative model for the offline single-user schema."""


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ConfidenceRating(str, Enum):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class Subject(TimestampMixin, Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    color: Mapped[str] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(Text, nullable=True)
    exam_date: Mapped[date] = mapped_column(Date, nullable=True)
    archived: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    topics: Mapped[list["Topic"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    study_sessions: Mapped[list["StudySession"]] = relationship(back_populates="subject")
    tasks: Mapped[list["Task"]] = relationship(back_populates="subject")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="subject")


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_topics_difficulty"),
        CheckConstraint("status IN ('active', 'paused', 'completed', 'archived')", name="ck_topics_status"),
        CheckConstraint("mastery_score >= 0", name="ck_topics_mastery_non_negative"),
        CheckConstraint("review_count >= 0", name="ck_topics_review_count_non_negative"),
        Index("ix_topics_subject_id", "subject_id"),
        Index("ix_topics_status", "status"),
        Index("ix_topics_target_date", "target_date"),
        Index("ix_topics_exam_date_override", "exam_date_override"),
        Index("ix_topics_last_reviewed_at", "last_reviewed_at"),
        Index("uq_topics_subject_name", "subject_id", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", server_default="medium")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", server_default="active")
    target_date: Mapped[date] = mapped_column(Date, nullable=True)
    exam_date_override: Mapped[date] = mapped_column(Date, nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    mastery_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    revisions: Mapped[list["Revision"]] = relationship(back_populates="topic", cascade="all, delete-orphan")
    study_sessions: Mapped[list["StudySession"]] = relationship(back_populates="topic")
    performance_logs: Mapped[list["PerformanceLog"]] = relationship(back_populates="topic", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="topic")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="topic")


class Revision(TimestampMixin, Base):
    __tablename__ = "revisions"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'completed', 'missed', 'cancelled')", name="ck_revisions_status"),
        CheckConstraint(
            "rating IS NULL OR rating IN ('again', 'hard', 'good', 'easy')",
            name="ck_revisions_rating",
        ),
        CheckConstraint("interval_days IS NULL OR interval_days >= 0", name="ck_revisions_interval_days_non_negative"),
        CheckConstraint(
            "previous_interval_days IS NULL OR previous_interval_days >= 0",
            name="ck_revisions_previous_interval_days_non_negative",
        ),
        CheckConstraint("stability IS NULL OR stability >= 0", name="ck_revisions_stability_non_negative"),
        CheckConstraint("overdue_days >= 0", name="ck_revisions_overdue_days_non_negative"),
        Index("ix_revisions_topic_id", "topic_id"),
        Index("ix_revisions_due_at", "due_at"),
        Index("ix_revisions_status", "status"),
        Index("idx_revisions_due_status", "due_at", "status"),
        Index("idx_revisions_topic_status", "topic_id", "status"),
        Index(
            "idx_revisions_open_due",
            "due_at",
            sqlite_where=text("status = 'open'"),
        ),
        Index(
            "ux_revisions_one_open_per_topic",
            "topic_id",
            unique=True,
            sqlite_where=text("status = 'open'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", server_default="open")
    scheduled_from_revision_id: Mapped[int] = mapped_column(
        ForeignKey("revisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    rating: Mapped[str] = mapped_column(String(16), nullable=True)
    interval_days: Mapped[float] = mapped_column(Float, nullable=True)
    previous_interval_days: Mapped[float] = mapped_column(Float, nullable=True)
    stability: Mapped[float] = mapped_column(Float, nullable=True)
    difficulty_adjustment: Mapped[float] = mapped_column(Float, nullable=True)
    overdue_days: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    topic: Mapped["Topic"] = relationship(back_populates="revisions")
    source_revision: Mapped["Revision"] = relationship(remote_side=lambda: Revision.id)


class StudySession(TimestampMixin, Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_study_sessions_time_order"),
        Index("ix_study_sessions_subject_id", "subject_id"),
        Index("ix_study_sessions_topic_id", "topic_id"),
        Index("ix_study_sessions_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    session_type: Mapped[str] = mapped_column(String(16), nullable=False, default="study", server_default="study")
    focus_score: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    subject: Mapped["Subject"] = relationship(back_populates="study_sessions")
    topic: Mapped["Topic"] = relationship(back_populates="study_sessions")


class PerformanceLog(Base):
    __tablename__ = "performance_logs"
    __table_args__ = (
        Index("ix_performance_logs_topic_id", "topic_id"),
        Index("ix_performance_logs_logged_at", "logged_at"),
        Index("ix_performance_logs_source", "source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, server_default=func.current_timestamp())
    source: Mapped[str] = mapped_column(String(32), nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    topic: Mapped["Topic"] = relationship(back_populates="performance_logs")


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="ck_tasks_priority"),
        CheckConstraint("status IN ('open', 'in_progress', 'done', 'cancelled')", name="ck_tasks_status"),
        Index("ix_tasks_subject_id", "subject_id"),
        Index("ix_tasks_topic_id", "topic_id"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", server_default="medium")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", server_default="open")
    due_date: Mapped[date] = mapped_column(Date, nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    subject: Mapped["Subject"] = relationship(back_populates="tasks")
    topic: Mapped["Topic"] = relationship(back_populates="tasks")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_related_subject_id", "related_subject_id"),
        Index("ix_notifications_related_topic_id", "related_topic_id"),
        Index("ix_notifications_scheduled_for", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    related_subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    related_topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_dismissed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    subject: Mapped["Subject"] = relationship(back_populates="notifications")
    topic: Mapped["Topic"] = relationship(back_populates="notifications")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


MODEL_REGISTRY: tuple[type[Base], ...] = (
    Subject,
    Topic,
    Revision,
    StudySession,
    PerformanceLog,
    Task,
    Notification,
    AppSetting,
)


event.listen(
    AppSetting.__table__,
    "after_create",
    DDL(
        """
        INSERT OR IGNORE INTO app_settings (key, value)
        VALUES
            ('daily_time_minutes', '120'),
            ('preferred_time', '18:00')
        """
    ),
)

for trigger_name, table_name in (
    ("trg_topics_updated_at", "topics"),
    ("trg_revisions_updated_at", "revisions"),
    ("trg_sessions_updated_at", "study_sessions"),
    ("trg_tasks_updated_at", "tasks"),
    ("trg_settings_updated_at", "app_settings"),
):
    event.listen(
        Base.metadata,
        "after_create",
        DDL(
            f"""
            CREATE TRIGGER IF NOT EXISTS {trigger_name}
            AFTER UPDATE ON {table_name}
            FOR EACH ROW
            WHEN NEW.updated_at = OLD.updated_at
            BEGIN
              UPDATE {table_name}
              SET updated_at = CURRENT_TIMESTAMP
              WHERE rowid = NEW.rowid;
            END;
            """
        ),
    )
