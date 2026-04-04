"""Add normalized signal snapshot storage

Revision ID: 004
Revises: 003
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city", sa.String(length=50), nullable=False),
        sa.Column("zone", sa.String(length=80), nullable=False),
        sa.Column("signal_type", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_mode", sa.String(length=20), nullable=False, server_default="mock"),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("normalized_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("quality_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_envelope", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_fallback", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signal_snapshots_city", "signal_snapshots", ["city"], unique=False)
    op.create_index("ix_signal_snapshots_zone", "signal_snapshots", ["zone"], unique=False)
    op.create_index("ix_signal_snapshots_signal_type", "signal_snapshots", ["signal_type"], unique=False)
    op.create_index("ix_signal_snapshots_captured_at", "signal_snapshots", ["captured_at"], unique=False)
    op.create_index(
        "idx_signal_snapshot_zone_type_time",
        "signal_snapshots",
        ["zone", "signal_type", "captured_at"],
        unique=False,
    )
    op.create_index(
        "idx_signal_snapshot_city_time",
        "signal_snapshots",
        ["city", "captured_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_signal_snapshot_city_time", table_name="signal_snapshots")
    op.drop_index("idx_signal_snapshot_zone_type_time", table_name="signal_snapshots")
    op.drop_index("ix_signal_snapshots_captured_at", table_name="signal_snapshots")
    op.drop_index("ix_signal_snapshots_signal_type", table_name="signal_snapshots")
    op.drop_index("ix_signal_snapshots_zone", table_name="signal_snapshots")
    op.drop_index("ix_signal_snapshots_city", table_name="signal_snapshots")
    op.drop_table("signal_snapshots")
