"""Initial migration - create all Smart Study tables.

Revision ID: 0001_initial
Revises: None
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


difficulty_enum = sa.Enum(
    "easy",
    "medium",
    "hard",
    name="difficultylevel",
    native_enum=False,
    create_constraint=True,
)
confidence_enum = sa.Enum(
    "1",
    "2",
    "3",
    "4",
    name="confidencerating",
    native_enum=False,
    create_constraint=True,
)
sync_status_enum = sa.Enum(
    "synced",
    "pending",
    "conflict",
    name="syncstatus",
    native_enum=False,
    create_constraint=True,
)
badge_slug_enum = sa.Enum(
    "first_review",
    "week_warrior",
    "hundred_topics",
    "streak_7",
    "streak_30",
    "perfect_week",
    "early_bird",
    "night_owl",
    "speed_learner",
    "master_mind",
    name="badgeslug",
    native_enum=False,
    create_constraint=True,
)
notification_type_enum = sa.Enum(
    "morning_summary",
    "overdue_alert",
    "exam_reminder",
    "streak_warning",
    name="notificationtype",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("avatar_initials", sa.String(length=3), nullable=True),
        sa.Column("xp_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_date", sa.Date(), nullable=True),
        sa.Column("sync_status", sync_status_enum, nullable=False, server_default="pending"),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("theme", sa.String(length=20), nullable=False, server_default="system"),
        sa.Column("font_size_px", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("high_contrast", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notification_time", sa.String(length=5), nullable=False, server_default="08:00"),
        sa.Column("notify_morning_summary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_overdue_alert", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_exam_reminder_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("daily_goal_topics", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("default_session_minutes", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("pomodoro_break_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("cloud_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supabase_url", sa.String(length=255), nullable=True),
        sa.Column("supabase_anon_key", sa.String(length=255), nullable=True),
        sa.Column("last_full_sync_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("font_size_px BETWEEN 10 AND 24", name="ck_font_size"),
        sa.CheckConstraint("daily_goal_topics >= 1", name="ck_daily_goal"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "subjects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("color_tag", sa.String(length=7), nullable=False, server_default="#7F77DD"),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sync_status", sync_status_enum, nullable=False, server_default="pending"),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_subject_user_name"),
    )
    op.create_index("ix_subjects_user_id", "subjects", ["user_id"])

    op.create_table(
        "study_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("topic_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("is_pomodoro", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pomodoro_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("topics_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("topics_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_confidence", sa.Float(), nullable=True),
        sa.Column("xp_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sync_status", sync_status_enum, nullable=False, server_default="pending"),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_session_time_order"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_study_sessions_user_id", "study_sessions", ["user_id"])
    op.create_index("ix_study_sessions_topic_id", "study_sessions", ["topic_id"])
    op.create_index("ix_study_sessions_started_at", "study_sessions", ["started_at"])

    op.create_table(
        "topics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("parent_topic_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("difficulty", difficulty_enum, nullable=False, server_default="medium"),
        sa.Column("difficulty_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("difficulty_source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fsrs_stability", sa.Float(), nullable=True),
        sa.Column("fsrs_difficulty", sa.Float(), nullable=True),
        sa.Column("fsrs_due_date", sa.Date(), nullable=True),
        sa.Column("fsrs_last_review", sa.Date(), nullable=True),
        sa.Column("fsrs_review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sync_status", sync_status_enum, nullable=False, server_default="pending"),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("difficulty_score BETWEEN 0.0 AND 1.0", name="ck_difficulty_score"),
        sa.ForeignKeyConstraint(["parent_topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("subject_id", "name", name="uq_topics_subject_name"),
    )
    op.create_index("ix_topics_subject_id", "topics", ["subject_id"])
    op.create_index("ix_topics_fsrs_due_date", "topics", ["fsrs_due_date"])
    op.create_index("ix_topics_parent_topic_id", "topics", ["parent_topic_id"])

    op.create_table(
        "revisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("topic_id", sa.String(length=36), nullable=False),
        sa.Column("study_session_id", sa.String(length=36), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_missed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence_rating", confidence_enum, nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("interval_days_before", sa.Integer(), nullable=True),
        sa.Column("interval_days_after", sa.Integer(), nullable=True),
        sa.Column("fsrs_interval_days", sa.Integer(), nullable=True),
        sa.Column("personalized_interval_days", sa.Integer(), nullable=True),
        sa.Column("scheduled_days_overdue", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduler_source", sa.String(length=20), nullable=False, server_default="fsrs"),
        sa.Column("sync_status", sync_status_enum, nullable=False, server_default="pending"),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "NOT (is_completed = 1 AND confidence_rating IS NULL)",
            name="ck_completed_needs_rating",
        ),
        sa.ForeignKeyConstraint(["study_session_id"], ["study_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_revisions_topic_id", "revisions", ["topic_id"])
    op.create_index("ix_revisions_scheduled_date", "revisions", ["scheduled_date"])
    op.create_index("ix_revisions_completed_at", "revisions", ["completed_at"])

    op.create_table(
        "performance_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("topic_id", sa.String(length=36), nullable=False),
        sa.Column("revision_id", sa.String(length=36), nullable=False),
        sa.Column("days_since_last_review", sa.Integer(), nullable=True),
        sa.Column("review_count_at_time", sa.Integer(), nullable=False),
        sa.Column("difficulty_score_at_time", sa.Float(), nullable=False),
        sa.Column("scheduled_days_overdue", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hour_of_day", sa.Integer(), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("confidence_rating", confidence_enum, nullable=False),
        sa.Column("predicted_confidence", sa.Float(), nullable=True),
        sa.Column("scheduler_source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["revision_id"], ["revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_perf_log_topic_id", "performance_logs", ["topic_id"])
    op.create_index("ix_perf_log_created_at", "performance_logs", ["created_at"])

    op.create_table(
        "nlp_feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("topic_name_raw", sa.Text(), nullable=False),
        sa.Column("predicted_difficulty", difficulty_enum, nullable=False),
        sa.Column("predicted_confidence", sa.Float(), nullable=False),
        sa.Column("actual_difficulty", difficulty_enum, nullable=False),
        sa.Column("used_for_retraining", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_nlp_feedback_user_id", "nlp_feedback", ["user_id"])
    op.create_index("ix_nlp_feedback_retrain", "nlp_feedback", ["used_for_retraining"])

    op.create_table(
        "user_badges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("badge_slug", badge_slug_enum, nullable=False),
        sa.Column("awarded_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("xp_granted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "badge_slug", name="uq_user_badge"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("was_clicked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notif_log_user_id", "notification_logs", ["user_id"])
    op.create_index("ix_notif_log_sent_at", "notification_logs", ["sent_at"])


def downgrade() -> None:
    op.drop_index("ix_notif_log_sent_at", table_name="notification_logs")
    op.drop_index("ix_notif_log_user_id", table_name="notification_logs")
    op.drop_table("notification_logs")

    op.drop_index("ix_user_badges_user_id", table_name="user_badges")
    op.drop_table("user_badges")

    op.drop_index("ix_nlp_feedback_retrain", table_name="nlp_feedback")
    op.drop_index("ix_nlp_feedback_user_id", table_name="nlp_feedback")
    op.drop_table("nlp_feedback")

    op.drop_index("ix_perf_log_created_at", table_name="performance_logs")
    op.drop_index("ix_perf_log_topic_id", table_name="performance_logs")
    op.drop_table("performance_logs")

    op.drop_index("ix_revisions_completed_at", table_name="revisions")
    op.drop_index("ix_revisions_scheduled_date", table_name="revisions")
    op.drop_index("ix_revisions_topic_id", table_name="revisions")
    op.drop_table("revisions")

    op.drop_index("ix_topics_parent_topic_id", table_name="topics")
    op.drop_index("ix_topics_fsrs_due_date", table_name="topics")
    op.drop_index("ix_topics_subject_id", table_name="topics")
    op.drop_table("topics")

    op.drop_index("ix_study_sessions_started_at", table_name="study_sessions")
    op.drop_index("ix_study_sessions_topic_id", table_name="study_sessions")
    op.drop_index("ix_study_sessions_user_id", table_name="study_sessions")
    op.drop_table("study_sessions")

    op.drop_index("ix_subjects_user_id", table_name="subjects")
    op.drop_table("subjects")

    op.drop_table("user_preferences")
    op.drop_table("user_profiles")
