"""Add sync metadata to remaining tables.

Revision ID: 0002_sync_metadata
Revises: 0001_initial
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_sync_metadata"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


sync_status_enum = sa.Enum(
    "synced",
    "pending",
    "conflict",
    name="syncstatus",
    native_enum=False,
    create_constraint=True,
)

TABLES = (
    "user_preferences",
    "performance_logs",
    "nlp_feedback",
    "user_badges",
    "notification_logs",
)


def upgrade() -> None:
    for table_name in TABLES:
        op.add_column(table_name, sa.Column("sync_status", sync_status_enum, nullable=False, server_default="pending"))
        op.add_column(table_name, sa.Column("device_id", sa.String(length=64), nullable=True))
        op.add_column(table_name, sa.Column("last_synced_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table_name in reversed(TABLES):
        op.drop_column(table_name, "last_synced_at")
        op.drop_column(table_name, "device_id")
        op.drop_column(table_name, "sync_status")
