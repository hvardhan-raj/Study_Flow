from datetime import date, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def generate_uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    """Base SQLAlchemy declarative class for the study system."""


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ConfidenceRating(str, Enum):
    AGAIN = "1"
    HARD = "2"
    GOOD = "3"
    EASY = "4"


class SyncStatus(str, Enum):
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"


class BadgeSlug(str, Enum):
    FIRST_REVIEW = "first_review"
    WEEK_WARRIOR = "week_warrior"
    HUNDRED_TOPICS = "hundred_topics"
    STREAK_7 = "streak_7"
    STREAK_30 = "streak_30"
    PERFECT_WEEK = "perfect_week"
    EARLY_BIRD = "early_bird"
    NIGHT_OWL = "night_owl"
    SPEED_LEARNER = "speed_learner"
    MASTER_MIND = "master_mind"


class NotificationType(str, Enum):
    MORNING_SUMMARY = "morning_summary"
    OVERDUE_ALERT = "overdue_alert"
    EXAM_REMINDER = "exam_reminder"
    STREAK_WARNING = "streak_warning"


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]

DIFFICULTY_ENUM = SqlEnum(
    DifficultyLevel,
    name="difficultylevel",
    native_enum=False,
    values_callable=enum_values,
)
CONFIDENCE_ENUM = SqlEnum(
    ConfidenceRating,
    name="confidencerating",
    native_enum=False,
    values_callable=enum_values,
)
SYNC_STATUS_ENUM = SqlEnum(
    SyncStatus,
    name="syncstatus",
    native_enum=False,
    values_callable=enum_values,
)
BADGE_ENUM = SqlEnum(
    BadgeSlug,
    name="badgeslug",
    native_enum=False,
    values_callable=enum_values,
)
NOTIFICATION_TYPE_ENUM = SqlEnum(
    NotificationType,
    name="notificationtype",
    native_enum=False,
    values_callable=enum_values,
)


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


class SyncMixin(TimestampMixin):
    sync_status: Mapped[SyncStatus] = mapped_column(
        SYNC_STATUS_ENUM,
        nullable=False,
        default=SyncStatus.PENDING,
        server_default=SyncStatus.PENDING.value,
    )
    device_id: Mapped[str] = mapped_column(String(64), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class UserProfile(SyncMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_initials: Mapped[str] = mapped_column(String(3), nullable=True)
    xp_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_activity_date: Mapped[date] = mapped_column(Date, nullable=True)

    preferences: Mapped["UserPreference"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subjects: Mapped[list["Subject"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    study_sessions: Mapped[list["StudySession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    nlp_feedback_items: Mapped[list["NlpFeedback"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    badges: Mapped[list["UserBadge"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserPreference(SyncMixin, Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint("font_size_px BETWEEN 10 AND 24", name="ck_font_size"),
        CheckConstraint("daily_goal_topics >= 1", name="ck_daily_goal"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="system", server_default="system")
    font_size_px: Mapped[int] = mapped_column(Integer, nullable=False, default=14, server_default="14")
    high_contrast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    notification_time: Mapped[str] = mapped_column(String(5), nullable=False, default="08:00", server_default="08:00")
    notify_morning_summary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    notify_overdue_alert: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    notify_exam_reminder_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
    )
    daily_goal_topics: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    default_session_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=25,
        server_default="25",
    )
    pomodoro_break_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )
    cloud_sync_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    supabase_url: Mapped[str] = mapped_column(String(255), nullable=True)
    supabase_anon_key: Mapped[str] = mapped_column(String(255), nullable=True)
    last_full_sync_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user: Mapped["UserProfile"] = relationship(back_populates="preferences")


class Subject(SyncMixin, Base):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_subject_user_name"),
        Index("ix_subjects_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    color_tag: Mapped[str] = mapped_column(String(7), nullable=False, default="#7F77DD", server_default="#7F77DD")
    exam_date: Mapped[date] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    user: Mapped["UserProfile"] = relationship(back_populates="subjects")
    topics: Mapped[list["Topic"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class StudySession(SyncMixin, Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_session_time_order"),
        Index("ix_study_sessions_user_id", "user_id"),
        Index("ix_study_sessions_topic_id", "topic_id"),
        Index("ix_study_sessions_started_at", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    is_pomodoro: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    pomodoro_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    topics_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    topics_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    avg_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    xp_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    user: Mapped["UserProfile"] = relationship(back_populates="study_sessions")
    topic: Mapped["Topic"] = relationship(back_populates="study_sessions")
    revisions: Mapped[list["Revision"]] = relationship(back_populates="study_session")


class Topic(SyncMixin, Base):
    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint("difficulty_score BETWEEN 0.0 AND 1.0", name="ck_difficulty_score"),
        UniqueConstraint("subject_id", "name", name="uq_topics_subject_name"),
        Index("ix_topics_subject_id", "subject_id"),
        Index("ix_topics_fsrs_due_date", "fsrs_due_date"),
        Index("ix_topics_parent_topic_id", "parent_topic_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    parent_topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        DIFFICULTY_ENUM,
        nullable=False,
        default=DifficultyLevel.MEDIUM,
        server_default=DifficultyLevel.MEDIUM.value,
    )
    difficulty_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    difficulty_source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    exam_date: Mapped[date] = mapped_column(Date, nullable=True)
    completion_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    fsrs_stability: Mapped[float] = mapped_column(Float, nullable=True)
    fsrs_difficulty: Mapped[float] = mapped_column(Float, nullable=True)
    fsrs_due_date: Mapped[date] = mapped_column(Date, nullable=True)
    fsrs_last_review: Mapped[date] = mapped_column(Date, nullable=True)
    fsrs_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    parent_topic: Mapped["Topic"] = relationship(
        remote_side=lambda: Topic.id,
        back_populates="child_topics",
    )
    child_topics: Mapped[list["Topic"]] = relationship(back_populates="parent_topic")
    revisions: Mapped[list["Revision"]] = relationship(back_populates="topic", cascade="all, delete-orphan")
    study_sessions: Mapped[list["StudySession"]] = relationship(back_populates="topic", cascade="all, delete-orphan")
    performance_logs: Mapped[list["PerformanceLog"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
    )


class Revision(SyncMixin, Base):
    __tablename__ = "revisions"
    __table_args__ = (
        CheckConstraint(
            "NOT (is_completed = 1 AND confidence_rating IS NULL)",
            name="ck_completed_needs_rating",
        ),
        Index("ix_revisions_topic_id", "topic_id"),
        Index("ix_revisions_scheduled_date", "scheduled_date"),
        Index("ix_revisions_completed_at", "completed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    study_session_id: Mapped[str] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_missed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    confidence_rating: Mapped[ConfidenceRating] = mapped_column(CONFIDENCE_ENUM, nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    interval_days_before: Mapped[int] = mapped_column(Integer, nullable=True)
    interval_days_after: Mapped[int] = mapped_column(Integer, nullable=True)
    fsrs_interval_days: Mapped[int] = mapped_column(Integer, nullable=True)
    personalized_interval_days: Mapped[int] = mapped_column(Integer, nullable=True)
    scheduled_days_overdue: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    scheduler_source: Mapped[str] = mapped_column(String(20), nullable=False, default="fsrs", server_default="fsrs")

    topic: Mapped["Topic"] = relationship(back_populates="revisions")
    study_session: Mapped["StudySession"] = relationship(back_populates="revisions")
    performance_logs: Mapped[list["PerformanceLog"]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
    )


class PerformanceLog(SyncMixin, Base):
    __tablename__ = "performance_logs"
    __table_args__ = (
        Index("ix_perf_log_topic_id", "topic_id"),
        Index("ix_perf_log_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id", ondelete="CASCADE"), nullable=False)
    days_since_last_review: Mapped[int] = mapped_column(Integer, nullable=True)
    review_count_at_time: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty_score_at_time: Mapped[float] = mapped_column(Float, nullable=False)
    scheduled_days_overdue: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=True)
    confidence_rating: Mapped[ConfidenceRating] = mapped_column(CONFIDENCE_ENUM, nullable=False)
    predicted_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    scheduler_source: Mapped[str] = mapped_column(String(20), nullable=False)

    topic: Mapped["Topic"] = relationship(back_populates="performance_logs")
    revision: Mapped["Revision"] = relationship(back_populates="performance_logs")


class NlpFeedback(SyncMixin, Base):
    __tablename__ = "nlp_feedback"
    __table_args__ = (
        Index("ix_nlp_feedback_user_id", "user_id"),
        Index("ix_nlp_feedback_retrain", "used_for_retraining"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    topic_name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_difficulty: Mapped[DifficultyLevel] = mapped_column(DIFFICULTY_ENUM, nullable=False)
    predicted_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    actual_difficulty: Mapped[DifficultyLevel] = mapped_column(DIFFICULTY_ENUM, nullable=False)
    used_for_retraining: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    user: Mapped["UserProfile"] = relationship(back_populates="nlp_feedback_items")


class UserBadge(SyncMixin, Base):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_slug", name="uq_user_badge"),
        Index("ix_user_badges_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    badge_slug: Mapped[BadgeSlug] = mapped_column(BADGE_ENUM, nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    xp_granted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    user: Mapped["UserProfile"] = relationship(back_populates="badges")


class NotificationLog(SyncMixin, Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        Index("ix_notif_log_user_id", "user_id"),
        Index("ix_notif_log_sent_at", "sent_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(NOTIFICATION_TYPE_ENUM, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    was_clicked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    user: Mapped["UserProfile"] = relationship(back_populates="notification_logs")


MODEL_REGISTRY: tuple[type[Base], ...] = (
    UserProfile,
    UserPreference,
    Subject,
    Topic,
    Revision,
    StudySession,
    PerformanceLog,
    NlpFeedback,
    UserBadge,
    NotificationLog,
)
