"""Harden revision constraints and ensure SQLite artifacts.

Revision ID: 0002_harden_revision_constraints_and_sqlite_artifacts
Revises: 0001_initial_offline
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_harden_revision_constraints_and_sqlite_artifacts"
down_revision = "0001_initial_offline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE revisions RENAME TO revisions_old")

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
    op.execute(
        """
        INSERT INTO revisions (
            id, topic_id, due_at, status, scheduled_from_revision_id, completed_at, rating,
            interval_days, previous_interval_days, stability, difficulty_adjustment,
            overdue_days, notes, created_at, updated_at
        )
        SELECT
            id, topic_id, due_at, status, scheduled_from_revision_id, completed_at, rating,
            interval_days, previous_interval_days, stability, difficulty_adjustment,
            overdue_days, notes, created_at, updated_at
        FROM revisions_old
        ORDER BY id
        """
    )
    op.drop_table("revisions_old")

    op.create_index("ix_revisions_topic_id", "revisions", ["topic_id"])
    op.create_index("ix_revisions_due_at", "revisions", ["due_at"])
    op.create_index("ix_revisions_status", "revisions", ["status"])
    op.create_index("idx_revisions_due_status", "revisions", ["due_at", "status"])
    op.create_index("idx_revisions_topic_status", "revisions", ["topic_id", "status"])
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_revisions_one_open_per_topic
        ON revisions(topic_id)
        WHERE status = 'open'
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_revisions_open_due
        ON revisions(due_at)
        WHERE status = 'open'
        """
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
    op.drop_index("idx_revisions_open_due", table_name="revisions")
    op.drop_index("idx_revisions_topic_status", table_name="revisions")
    op.drop_index("idx_revisions_due_status", table_name="revisions")
