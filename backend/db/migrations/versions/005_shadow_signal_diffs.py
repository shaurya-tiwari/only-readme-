"""Add shadow signal diff storage

Revision ID: 005
Revises: 004
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shadow_signal_diffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city", sa.String(length=50), nullable=False),
        sa.Column("zone", sa.String(length=80), nullable=False),
        sa.Column("signal_type", sa.String(length=50), nullable=False),
        sa.Column("primary_provider", sa.String(length=100), nullable=False),
        sa.Column("shadow_provider", sa.String(length=100), nullable=False),
        sa.Column("compared_at", sa.DateTime(), nullable=False),
        sa.Column("max_delta", sa.Numeric(8, 3), nullable=False),
        sa.Column("metric_deltas", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("threshold_crossed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("alert_triggered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("threshold_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shadow_signal_diffs_city", "shadow_signal_diffs", ["city"], unique=False)
    op.create_index("ix_shadow_signal_diffs_zone", "shadow_signal_diffs", ["zone"], unique=False)
    op.create_index("ix_shadow_signal_diffs_signal_type", "shadow_signal_diffs", ["signal_type"], unique=False)
    op.create_index("ix_shadow_signal_diffs_compared_at", "shadow_signal_diffs", ["compared_at"], unique=False)
    op.create_index(
        "idx_shadow_diff_zone_type_time",
        "shadow_signal_diffs",
        ["zone", "signal_type", "compared_at"],
        unique=False,
    )
    op.create_index(
        "idx_shadow_diff_city_time",
        "shadow_signal_diffs",
        ["city", "compared_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_shadow_diff_city_time", table_name="shadow_signal_diffs")
    op.drop_index("idx_shadow_diff_zone_type_time", table_name="shadow_signal_diffs")
    op.drop_index("ix_shadow_signal_diffs_compared_at", table_name="shadow_signal_diffs")
    op.drop_index("ix_shadow_signal_diffs_signal_type", table_name="shadow_signal_diffs")
    op.drop_index("ix_shadow_signal_diffs_zone", table_name="shadow_signal_diffs")
    op.drop_index("ix_shadow_signal_diffs_city", table_name="shadow_signal_diffs")
    op.drop_table("shadow_signal_diffs")
