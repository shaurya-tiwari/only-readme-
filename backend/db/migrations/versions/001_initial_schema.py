"""Initial schema — all 8 tables

Revision ID: 001
Revises: None
Create Date: 2025-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Workers
    op.create_table(
        'workers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(15), unique=True, nullable=False),
        sa.Column('city', sa.String(50), nullable=False),
        sa.Column('zone', sa.String(50)),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('self_reported_income', sa.Numeric(10, 2)),
        sa.Column('working_hours', sa.Numeric(4, 1)),
        sa.Column('device_fingerprint', sa.String(255)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('consent_given', sa.Boolean, default=False),
        sa.Column('consent_timestamp', sa.DateTime),
        sa.Column('risk_score', sa.Numeric(4, 3)),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )
    op.create_index('ix_workers_phone', 'workers', ['phone'])
    op.create_index('ix_workers_city', 'workers', ['city'])
    op.create_index('ix_workers_status', 'workers', ['status'])

    # Policies
    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workers.id'), nullable=False),
        sa.Column('plan_name', sa.String(50), nullable=False),
        sa.Column('plan_display_name', sa.String(100), nullable=False),
        sa.Column('base_price', sa.Numeric(8, 2), nullable=False),
        sa.Column('plan_factor', sa.Numeric(3, 1), nullable=False),
        sa.Column('risk_score_at_purchase', sa.Numeric(4, 3), nullable=False),
        sa.Column('weekly_premium', sa.Numeric(8, 2), nullable=False),
        sa.Column('coverage_cap', sa.Numeric(8, 2), nullable=False),
        sa.Column('triggers_covered', postgresql.ARRAY(sa.String), nullable=False),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('purchased_at', sa.DateTime),
        sa.Column('activates_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime),
    )
    op.create_index('ix_policies_worker_id', 'policies', ['worker_id'])
    op.create_index('ix_policies_status', 'policies', ['status'])

    # Events
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('zone', sa.String(50), nullable=False),
        sa.Column('city', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('ended_at', sa.DateTime),
        sa.Column('severity', sa.Numeric(4, 3)),
        sa.Column('raw_value', sa.Numeric(10, 2)),
        sa.Column('threshold', sa.Numeric(10, 2)),
        sa.Column('disruption_score', sa.Numeric(4, 3)),
        sa.Column('event_confidence', sa.Numeric(4, 3)),
        sa.Column('api_source', sa.String(100)),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('metadata_json', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )
    op.create_index('ix_events_type', 'events', ['event_type'])
    op.create_index('ix_events_zone', 'events', ['zone'])
    op.create_index('ix_events_city', 'events', ['city'])
    op.create_index('ix_events_status', 'events', ['status'])
    op.create_index('idx_event_zone_type_time', 'events', ['event_type', 'zone', 'started_at'])

    # Claims
    op.create_table(
        'claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workers.id'), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('policies.id'), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id'), nullable=False),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('disruption_hours', sa.Numeric(4, 1)),
        sa.Column('income_per_hour', sa.Numeric(8, 2)),
        sa.Column('peak_multiplier', sa.Numeric(3, 1), default=1.0),
        sa.Column('calculated_payout', sa.Numeric(8, 2)),
        sa.Column('final_payout', sa.Numeric(8, 2)),
        sa.Column('disruption_score', sa.Numeric(4, 3)),
        sa.Column('event_confidence', sa.Numeric(4, 3)),
        sa.Column('fraud_score', sa.Numeric(4, 3)),
        sa.Column('trust_score', sa.Numeric(4, 3)),
        sa.Column('final_score', sa.Numeric(4, 3)),
        sa.Column('decision_breakdown', postgresql.JSONB),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('rejection_reason', sa.Text),
        sa.Column('review_deadline', sa.DateTime),
        sa.Column('reviewed_by', sa.String(100)),
        sa.Column('reviewed_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )
    op.create_index('ix_claims_worker_id', 'claims', ['worker_id'])
    op.create_index('ix_claims_status', 'claims', ['status'])
    op.create_unique_constraint('uq_claim_dedup', 'claims', ['worker_id', 'event_id', 'trigger_type'])

    # Payouts
    op.create_table(
        'payouts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('claims.id'), unique=True, nullable=False),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workers.id'), nullable=False),
        sa.Column('amount', sa.Numeric(8, 2), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('transaction_id', sa.String(100)),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('initiated_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
    )
    op.create_index('ix_payouts_worker_id', 'payouts', ['worker_id'])

    # Trust Scores
    op.create_table(
        'trust_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workers.id'), unique=True, nullable=False),
        sa.Column('score', sa.Numeric(4, 3), default=0.100),
        sa.Column('total_claims', sa.Integer, default=0),
        sa.Column('approved_claims', sa.Integer, default=0),
        sa.Column('fraud_flags', sa.Integer, default=0),
        sa.Column('account_age_days', sa.Integer, default=0),
        sa.Column('device_stability', sa.Numeric(4, 3), default=0.500),
        sa.Column('last_updated', sa.DateTime),
    )

    # Fraud Logs
    op.create_table(
        'fraud_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('claims.id')),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workers.id'), nullable=False),
        sa.Column('fraud_type', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Numeric(4, 3)),
        sa.Column('signals', postgresql.JSONB),
        sa.Column('action_taken', sa.String(20)),
        sa.Column('created_at', sa.DateTime),
    )
    op.create_index('ix_fraud_logs_worker_id', 'fraud_logs', ['worker_id'])

    # Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('details', postgresql.JSONB),
        sa.Column('performed_by', sa.String(100), default='system'),
        sa.Column('created_at', sa.DateTime),
    )
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])

    # Worker Activity
    op.create_table(
        'worker_activity',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workers.id'), nullable=False),
        sa.Column('zone', sa.String(50), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 7)),
        sa.Column('longitude', sa.Numeric(10, 7)),
        sa.Column('speed_kmh', sa.Numeric(5, 1)),
        sa.Column('has_delivery_stop', sa.Boolean, default=False),
        sa.Column('recorded_at', sa.DateTime),
    )
    op.create_index('idx_activity_zone_time', 'worker_activity', ['zone', 'recorded_at'])
    op.create_index('idx_activity_worker_time', 'worker_activity', ['worker_id', 'recorded_at'])


def downgrade() -> None:
    op.drop_table('worker_activity')
    op.drop_table('audit_logs')
    op.drop_table('fraud_logs')
    op.drop_table('trust_scores')
    op.drop_table('payouts')
    op.drop_table('claims')
    op.drop_table('events')
    op.drop_table('policies')
    op.drop_table('workers')