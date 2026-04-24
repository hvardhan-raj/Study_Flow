"""Initial offline single-user schema.

Revision ID: 0001_initial_offline
Revises: None
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_offline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("archived", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("name", name="uq_subjects_name"),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("exam_date_override", sa.Date(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("mastery_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_topics_difficulty"),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed', 'archived')", name="ck_topics_status"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("subject_id", "name", name="uq_topics_subject_name"),
    )
    op.create_index("ix_topics_subject_id", "topics", ["subject_id"])
    op.create_index("ix_topics_status", "topics", ["status"])
    op.create_index("ix_topics_target_date", "topics", ["target_date"])
    op.create_index("ix_topics_exam_date_override", "topics", ["exam_date_override"])

    op.create_table(
        "revisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("scheduled_from_revision_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("rating", sa.String(length=16), nullable=True),
        sa.Column("interval_days", sa.Float(), nullable=True),
        sa.Column("previous_interval_days", sa.Float(), nullable=True),
        sa.Column("stability", sa.Float(), nullable=True),
        sa.Column("difficulty_adjustment", sa.Float(), nullable=True),
        sa.Column("overdue_days", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("status IN ('open', 'completed', 'missed', 'cancelled')", name="ck_revisions_status"),
        sa.CheckConstraint("rating IS NULL OR rating IN ('again', 'hard', 'good', 'easy')", name="ck_revisions_rating"),
        sa.CheckConstraint("interval_days IS NULL OR interval_days >= 0", name="ck_revisions_interval_days_non_negative"),
        sa.CheckConstraint(
            "previous_interval_days IS NULL OR previous_interval_days >= 0",
            name="ck_revisions_previous_interval_days_non_negative",
        ),
        sa.CheckConstraint("stability IS NULL OR stability >= 0", name="ck_revisions_stability_non_negative"),
        sa.CheckConstraint("overdue_days >= 0", name="ck_revisions_overdue_days_non_negative"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scheduled_from_revision_id"], ["revisions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_revisions_topic_id", "revisions", ["topic_id"])
    op.create_index("ix_revisions_due_at", "revisions", ["due_at"])
    op.create_index("ix_revisions_status", "revisions", ["status"])
    op.create_index("idx_revisions_due_status", "revisions", ["due_at", "status"])
    op.create_index("idx_revisions_topic_status", "revisions", ["topic_id", "status"])
    op.execute(
        """
        CREATE UNIQUE INDEX ux_revisions_one_open_per_topic
        ON revisions(topic_id)
        WHERE status = 'open'
        """
    )
    op.execute(
        """
        CREATE INDEX idx_revisions_open_due
        ON revisions(due_at)
        WHERE status = 'open'
        """
    )

    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("session_type", sa.String(length=16), nullable=False, server_default="study"),
        sa.Column("focus_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_study_sessions_subject_id", "study_sessions", ["subject_id"])
    op.create_index("ix_study_sessions_topic_id", "study_sessions", ["topic_id"])
    op.create_index("ix_study_sessions_started_at", "study_sessions", ["started_at"])

    op.create_table(
        "performance_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("logged_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_performance_logs_topic_id", "performance_logs", ["topic_id"])
    op.create_index("ix_performance_logs_logged_at", "performance_logs", ["logged_at"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high')", name="ck_tasks_priority"),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'done', 'cancelled')", name="ck_tasks_status"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tasks_subject_id", "tasks", ["subject_id"])
    op.create_index("ix_tasks_topic_id", "tasks", ["topic_id"])
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type", sa.String(length=32), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("related_subject_id", sa.Integer(), nullable=True),
        sa.Column("related_topic_id", sa.Integer(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("is_dismissed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["related_subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_topic_id"], ["topics.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_notifications_related_subject_id", "notifications", ["related_subject_id"])
    op.create_index("ix_notifications_related_topic_id", "notifications", ["related_topic_id"])
    op.create_index("ix_notifications_scheduled_for", "notifications", ["scheduled_for"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value) VALUES
        ('daily_time_minutes', '120'),
        ('preferred_time', '18:00')
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_topics_updated_at
        AFTER UPDATE ON topics
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE topics SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_revisions_updated_at
        AFTER UPDATE ON revisions
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE revisions SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_sessions_updated_at
        AFTER UPDATE ON study_sessions
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE study_sessions SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_tasks_updated_at
        AFTER UPDATE ON tasks
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_settings_updated_at
        AFTER UPDATE ON app_settings
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
          UPDATE app_settings SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_settings_updated_at")
    op.execute("DROP TRIGGER IF EXISTS trg_tasks_updated_at")
    op.execute("DROP TRIGGER IF EXISTS trg_sessions_updated_at")
    op.execute("DROP TRIGGER IF EXISTS trg_revisions_updated_at")
    op.execute("DROP TRIGGER IF EXISTS trg_topics_updated_at")
    op.drop_table("app_settings")
    op.drop_index("ix_notifications_scheduled_for", table_name="notifications")
    op.drop_index("ix_notifications_related_topic_id", table_name="notifications")
    op.drop_index("ix_notifications_related_subject_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_due_date", table_name="tasks")
    op.drop_index("ix_tasks_topic_id", table_name="tasks")
    op.drop_index("ix_tasks_subject_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_performance_logs_logged_at", table_name="performance_logs")
    op.drop_index("ix_performance_logs_topic_id", table_name="performance_logs")
    op.drop_table("performance_logs")
    op.drop_index("ix_study_sessions_started_at", table_name="study_sessions")
    op.drop_index("ix_study_sessions_topic_id", table_name="study_sessions")
    op.drop_index("ix_study_sessions_subject_id", table_name="study_sessions")
    op.drop_table("study_sessions")
    op.drop_index("idx_revisions_open_due", table_name="revisions")
    op.drop_index("idx_revisions_topic_status", table_name="revisions")
    op.drop_index("idx_revisions_due_status", table_name="revisions")
    op.drop_index("ux_revisions_one_open_per_topic", table_name="revisions")
    op.drop_index("ix_revisions_status", table_name="revisions")
    op.drop_index("ix_revisions_due_at", table_name="revisions")
    op.drop_index("ix_revisions_topic_id", table_name="revisions")
    op.drop_table("revisions")
    op.drop_index("ix_topics_exam_date_override", table_name="topics")
    op.drop_index("ix_topics_target_date", table_name="topics")
    op.drop_index("ix_topics_status", table_name="topics")
    op.drop_index("ix_topics_subject_id", table_name="topics")
    op.drop_table("topics")
    op.drop_table("subjects")
