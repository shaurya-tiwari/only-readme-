"""Add decision memory logs

Revision ID: 006
Revises: 005
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lifecycle_stage", sa.String(length=50), nullable=False),
        sa.Column("decision_source", sa.String(length=50), nullable=False),
        sa.Column("system_decision", sa.String(length=20), nullable=True),
        sa.Column("resulting_status", sa.String(length=20), nullable=False),
        sa.Column("final_label", sa.String(length=20), nullable=True),
        sa.Column("label_source", sa.String(length=50), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("payout_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("review_wait_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("fraud_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("trust_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("final_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("decision_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("model_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("decision_policy_version", sa.String(length=50), nullable=False),
        sa.Column("signal_snapshot_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("feature_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_logs_claim_id", "decision_logs", ["claim_id"], unique=False)
    op.create_index("ix_decision_logs_worker_id", "decision_logs", ["worker_id"], unique=False)
    op.create_index("ix_decision_logs_policy_id", "decision_logs", ["policy_id"], unique=False)
    op.create_index("ix_decision_logs_event_id", "decision_logs", ["event_id"], unique=False)
    op.create_index("ix_decision_logs_lifecycle_stage", "decision_logs", ["lifecycle_stage"], unique=False)
    op.create_index("ix_decision_logs_decision_source", "decision_logs", ["decision_source"], unique=False)
    op.create_index("ix_decision_logs_system_decision", "decision_logs", ["system_decision"], unique=False)
    op.create_index("ix_decision_logs_resulting_status", "decision_logs", ["resulting_status"], unique=False)
    op.create_index("ix_decision_logs_final_label", "decision_logs", ["final_label"], unique=False)
    op.create_index("ix_decision_logs_created_at", "decision_logs", ["created_at"], unique=False)
    op.create_index(
        "idx_decision_log_claim_stage_time",
        "decision_logs",
        ["claim_id", "lifecycle_stage", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_decision_log_worker_time",
        "decision_logs",
        ["worker_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_decision_log_worker_time", table_name="decision_logs")
    op.drop_index("idx_decision_log_claim_stage_time", table_name="decision_logs")
    op.drop_index("ix_decision_logs_created_at", table_name="decision_logs")
    op.drop_index("ix_decision_logs_final_label", table_name="decision_logs")
    op.drop_index("ix_decision_logs_resulting_status", table_name="decision_logs")
    op.drop_index("ix_decision_logs_system_decision", table_name="decision_logs")
    op.drop_index("ix_decision_logs_decision_source", table_name="decision_logs")
    op.drop_index("ix_decision_logs_lifecycle_stage", table_name="decision_logs")
    op.drop_index("ix_decision_logs_event_id", table_name="decision_logs")
    op.drop_index("ix_decision_logs_policy_id", table_name="decision_logs")
    op.drop_index("ix_decision_logs_worker_id", table_name="decision_logs")
    op.drop_index("ix_decision_logs_claim_id", table_name="decision_logs")
    op.drop_table("decision_logs")
