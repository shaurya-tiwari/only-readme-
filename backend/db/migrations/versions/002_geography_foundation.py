"""Geography foundation tables and zone references

Revision ID: 002
Revises: 001
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_cities_slug", "cities", ["slug"])
    op.create_index("ix_cities_active", "cities", ["active"])

    op.create_table(
        "zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("centroid_lat", sa.Numeric(10, 7)),
        sa.Column("centroid_lon", sa.Numeric(10, 7)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("city_id", "slug", name="uq_zone_city_slug"),
    )
    op.create_index("ix_zones_slug", "zones", ["slug"])
    op.create_index("ix_zones_city_id", "zones", ["city_id"])
    op.create_index("ix_zones_active", "zones", ["active"])

    op.create_table(
        "zone_threshold_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("zones.id"), nullable=False, unique=True),
        sa.Column("rain_threshold_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("heat_threshold_c", sa.Numeric(10, 2), nullable=False),
        sa.Column("aqi_threshold", sa.Integer(), nullable=False),
        sa.Column("traffic_threshold", sa.Numeric(4, 3), nullable=False),
        sa.Column("platform_outage_threshold", sa.Numeric(4, 3), nullable=False),
        sa.Column("social_inactivity_threshold", sa.Numeric(4, 3), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    op.create_table(
        "zone_risk_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("zones.id"), nullable=False, unique=True),
        sa.Column("base_risk", sa.Numeric(4, 3), nullable=False),
        sa.Column("avg_daily_income", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    op.add_column("workers", sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("workers", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_workers_city_id", "workers", ["city_id"])
    op.create_index("ix_workers_zone_id", "workers", ["zone_id"])

    op.add_column("events", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_events_zone_id", "events", ["zone_id"])

    op.add_column("worker_activity", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_worker_activity_zone_id", "worker_activity", ["zone_id"])


def downgrade() -> None:
    op.drop_index("ix_worker_activity_zone_id", table_name="worker_activity")
    op.drop_column("worker_activity", "zone_id")
    op.drop_index("ix_events_zone_id", table_name="events")
    op.drop_column("events", "zone_id")
    op.drop_index("ix_workers_zone_id", table_name="workers")
    op.drop_index("ix_workers_city_id", table_name="workers")
    op.drop_column("workers", "zone_id")
    op.drop_column("workers", "city_id")
    op.drop_table("zone_risk_profiles")
    op.drop_table("zone_threshold_profiles")
    op.drop_index("ix_zones_active", table_name="zones")
    op.drop_index("ix_zones_city_id", table_name="zones")
    op.drop_index("ix_zones_slug", table_name="zones")
    op.drop_table("zones")
    op.drop_index("ix_cities_active", table_name="cities")
    op.drop_index("ix_cities_slug", table_name="cities")
    op.drop_table("cities")
