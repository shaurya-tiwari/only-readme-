"""
DB-backed geography bootstrap and lookup helpers.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import City, Zone, ZoneRiskProfile, ZoneThresholdProfile

logger = logging.getLogger("rideshield.locations")

ZONE_CENTROIDS: dict[str, tuple[Decimal, Decimal]] = {
    "south_delhi": (Decimal("28.5200000"), Decimal("77.2200000")),
    "north_delhi": (Decimal("28.7000000"), Decimal("77.1000000")),
    "east_delhi": (Decimal("28.6300000"), Decimal("77.3000000")),
    "west_delhi": (Decimal("28.6500000"), Decimal("77.0500000")),
    "central_delhi": (Decimal("28.6400000"), Decimal("77.2100000")),
    "south_mumbai": (Decimal("18.9300000"), Decimal("72.8300000")),
    "western_suburbs": (Decimal("19.1700000"), Decimal("72.8400000")),
    "eastern_suburbs": (Decimal("19.0800000"), Decimal("72.9100000")),
    "navi_mumbai": (Decimal("19.0300000"), Decimal("73.0200000")),
    "koramangala": (Decimal("12.9300000"), Decimal("77.6200000")),
    "whitefield": (Decimal("12.9700000"), Decimal("77.7500000")),
    "indiranagar": (Decimal("12.9700000"), Decimal("77.6400000")),
    "jayanagar": (Decimal("12.9300000"), Decimal("77.5800000")),
    "electronic_city": (Decimal("12.8400000"), Decimal("77.6700000")),
    "t_nagar": (Decimal("13.0418000"), Decimal("80.2337000")),
    "anna_nagar": (Decimal("13.0850000"), Decimal("80.2101000")),
    "adyar": (Decimal("13.0067000"), Decimal("80.2576000")),
    "velachery": (Decimal("12.9791000"), Decimal("80.2212000")),
    "banjara_hills": (Decimal("17.4126000"), Decimal("78.4347000")),
    "hitech_city": (Decimal("17.4504000"), Decimal("78.3802000")),
    "gachibowli": (Decimal("17.4401000"), Decimal("78.3489000")),
    "kukatpally": (Decimal("17.4948000"), Decimal("78.3996000")),
    "hinjawadi": (Decimal("18.5912000"), Decimal("73.7389000")),
    "kothrud": (Decimal("18.5074000"), Decimal("73.8077000")),
    "viman_nagar": (Decimal("18.5679000"), Decimal("73.9143000")),
    "hadapsar": (Decimal("18.5089000"), Decimal("73.9260000")),
    "salt_lake": (Decimal("22.5877000"), Decimal("88.4173000")),
    "new_town": (Decimal("22.5750000"), Decimal("88.4790000")),
    "park_street": (Decimal("22.5539000"), Decimal("88.3526000")),
    "howrah": (Decimal("22.5958000"), Decimal("88.2636000")),
}


def city_display_name(slug: str) -> str:
    return slug.replace("_", " ").title()


def zone_display_name(slug: str) -> str:
    return slug.replace("_", " ").title()


class LocationService:
    async def ensure_runtime_schema(self, db: AsyncSession) -> None:
        """
        Add geography tables and columns for existing dev databases where create_all
        cannot evolve the schema. Safe to run multiple times.
        """
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS cities (
                id UUID PRIMARY KEY,
                slug VARCHAR(50) NOT NULL UNIQUE,
                display_name VARCHAR(100) NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS zones (
                id UUID PRIMARY KEY,
                city_id UUID NOT NULL REFERENCES cities(id),
                slug VARCHAR(80) NOT NULL UNIQUE,
                display_name VARCHAR(120) NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                centroid_lat NUMERIC(10,7),
                centroid_lon NUMERIC(10,7),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS zone_threshold_profiles (
                id UUID PRIMARY KEY,
                zone_id UUID NOT NULL UNIQUE REFERENCES zones(id),
                rain_threshold_mm NUMERIC(10,2) NOT NULL,
                heat_threshold_c NUMERIC(10,2) NOT NULL,
                aqi_threshold INTEGER NOT NULL,
                traffic_threshold NUMERIC(4,3) NOT NULL,
                platform_outage_threshold NUMERIC(4,3) NOT NULL,
                social_inactivity_threshold NUMERIC(4,3) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS zone_risk_profiles (
                id UUID PRIMARY KEY,
                zone_id UUID NOT NULL UNIQUE REFERENCES zones(id),
                base_risk NUMERIC(4,3) NOT NULL,
                avg_daily_income NUMERIC(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """,
            "ALTER TABLE workers ADD COLUMN IF NOT EXISTS city_id UUID",
            "ALTER TABLE workers ADD COLUMN IF NOT EXISTS zone_id UUID",
            "ALTER TABLE events ADD COLUMN IF NOT EXISTS zone_id UUID",
            "ALTER TABLE worker_activity ADD COLUMN IF NOT EXISTS zone_id UUID",
            "CREATE INDEX IF NOT EXISTS ix_workers_city_id ON workers (city_id)",
            "CREATE INDEX IF NOT EXISTS ix_workers_zone_id ON workers (zone_id)",
            "CREATE INDEX IF NOT EXISTS ix_events_zone_id ON events (zone_id)",
            "CREATE INDEX IF NOT EXISTS ix_worker_activity_zone_id ON worker_activity (zone_id)",
        ]
        for statement in ddl:
            await db.execute(text(statement))

    async def bootstrap_geography(self, db: AsyncSession) -> None:
        """
        Seed canonical cities/zones/profiles from config. This is now infrastructure,
        not demo-only data.
        """
        city_rows: dict[str, City] = {}
        for slug, profile in settings.CITY_RISK_PROFILES.items():
            city = (await db.execute(select(City).where(City.slug == slug))).scalar_one_or_none()
            if city is None:
                city = City(slug=slug, display_name=city_display_name(slug), active=True)
                db.add(city)
                await db.flush()
            else:
                city.display_name = city_display_name(slug)
                city.active = True
            city_rows[slug] = city

            for zone_slug in profile.get("zones", []):
                zone = (await db.execute(select(Zone).where(Zone.slug == zone_slug))).scalar_one_or_none()
                lat, lon = ZONE_CENTROIDS.get(zone_slug, (None, None))
                if zone is None:
                    zone = Zone(
                        city_id=city.id,
                        slug=zone_slug,
                        display_name=zone_display_name(zone_slug),
                        active=True,
                        centroid_lat=lat,
                        centroid_lon=lon,
                    )
                    db.add(zone)
                    await db.flush()
                else:
                    zone.city_id = city.id
                    zone.display_name = zone_display_name(zone_slug)
                    zone.active = True
                    zone.centroid_lat = lat
                    zone.centroid_lon = lon

                threshold = (
                    await db.execute(select(ZoneThresholdProfile).where(ZoneThresholdProfile.zone_id == zone.id))
                ).scalar_one_or_none()
                threshold_payload = {
                    "rain_threshold_mm": Decimal(str(settings.RAIN_THRESHOLD_MM)),
                    "heat_threshold_c": Decimal(str(settings.HEAT_THRESHOLD_C)),
                    "aqi_threshold": int(settings.AQI_THRESHOLD),
                    "traffic_threshold": Decimal(str(settings.TRAFFIC_THRESHOLD)),
                    "platform_outage_threshold": Decimal(str(settings.PLATFORM_OUTAGE_THRESHOLD)),
                    "social_inactivity_threshold": Decimal(str(settings.SOCIAL_INACTIVITY_THRESHOLD)),
                }
                if threshold is None:
                    db.add(ZoneThresholdProfile(zone_id=zone.id, **threshold_payload))
                else:
                    for key, value in threshold_payload.items():
                        setattr(threshold, key, value)

                risk_profile = (
                    await db.execute(select(ZoneRiskProfile).where(ZoneRiskProfile.zone_id == zone.id))
                ).scalar_one_or_none()
                risk_payload = {
                    "base_risk": Decimal(str(profile["base_risk"])),
                    "avg_daily_income": Decimal(str(profile["avg_daily_income"])),
                }
                if risk_profile is None:
                    db.add(ZoneRiskProfile(zone_id=zone.id, **risk_payload))
                else:
                    for key, value in risk_payload.items():
                        setattr(risk_profile, key, value)

        active_city_slugs = set(settings.CITY_RISK_PROFILES.keys())
        for city in (await db.execute(select(City))).scalars().all():
            city.active = city.slug in active_city_slugs
        await db.flush()

    async def backfill_zone_references(self, db: AsyncSession, strict: bool = True) -> None:
        """
        Sync legacy city/zone string columns to zone_id. Fail loudly if unmapped rows exist.
        """
        zone_map = {
            (zone.city_ref.slug, zone.slug): zone
            for zone in (
                await db.execute(
                    select(Zone).join(City, Zone.city_id == City.id).where(City.active == True)  # noqa: E712
                )
            ).scalars().all()
        }
        checks = [
            ("workers", "workers", "id", "city", "zone"),
            ("events", "events", "id", "city", "zone"),
            ("worker_activity", "worker_activity", "id", None, "zone"),
        ]
        unmapped: dict[str, list[str]] = {table: [] for table, *_ in checks}

        worker_rows = (
            await db.execute(text("SELECT id, city, zone FROM workers"))
        ).mappings().all()
        for row in worker_rows:
            if not row["zone"] or not row["city"]:
                continue
            zone = zone_map.get((str(row["city"]).lower(), str(row["zone"]).lower()))
            if zone is None:
                unmapped["workers"].append(f"{row['id']}:{row['city']}:{row['zone']}")
                continue
            await db.execute(
                text("UPDATE workers SET city_id = :city_id, zone_id = :zone_id WHERE id = :id"),
                {"id": row["id"], "city_id": zone.city_id, "zone_id": zone.id},
            )

        event_rows = (
            await db.execute(text("SELECT id, city, zone FROM events"))
        ).mappings().all()
        for row in event_rows:
            if not row["zone"] or not row["city"]:
                continue
            zone = zone_map.get((str(row["city"]).lower(), str(row["zone"]).lower()))
            if zone is None:
                unmapped["events"].append(f"{row['id']}:{row['city']}:{row['zone']}")
                continue
            await db.execute(
                text("UPDATE events SET zone_id = :zone_id WHERE id = :id"),
                {"id": row["id"], "zone_id": zone.id},
            )

        activity_rows = (
            await db.execute(
                text(
                    """
                    SELECT wa.id, wa.zone, w.city
                    FROM worker_activity wa
                    JOIN workers w ON wa.worker_id = w.id
                    """
                )
            )
        ).mappings().all()
        for row in activity_rows:
            if not row["zone"] or not row["city"]:
                continue
            zone = zone_map.get((str(row["city"]).lower(), str(row["zone"]).lower()))
            if zone is None:
                unmapped["worker_activity"].append(f"{row['id']}:{row['city']}:{row['zone']}")
                continue
            await db.execute(
                text("UPDATE worker_activity SET zone_id = :zone_id WHERE id = :id"),
                {"id": row["id"], "zone_id": zone.id},
            )

        mismatch_count = sum(len(entries) for entries in unmapped.values())
        if mismatch_count:
            for table, entries in unmapped.items():
                if entries:
                    logger.error("Unmapped %s rows during zone backfill: %s", table, entries[:10])
            if strict:
                raise RuntimeError(
                    f"Geography backfill failed with {mismatch_count} unmapped rows. "
                    "Fix slug mismatches before continuing."
                )
        logger.info("Geography backfill complete. Unmapped rows=%s", mismatch_count)

    async def ensure_bootstrap(self, db: AsyncSession, strict_backfill: bool = True) -> None:
        await self.ensure_runtime_schema(db)
        await self.bootstrap_geography(db)
        await self.backfill_zone_references(db, strict=strict_backfill)

    async def get_active_cities(self, db: AsyncSession) -> List[City]:
        return (
            await db.execute(select(City).where(City.active == True).order_by(City.display_name))  # noqa: E712
        ).scalars().all()

    async def get_active_zones(self, db: AsyncSession, city_slug: Optional[str] = None) -> List[Zone]:
        query = select(Zone).join(City, Zone.city_id == City.id).where(Zone.active == True, City.active == True)  # noqa: E712
        if city_slug:
            query = query.where(City.slug == city_slug.lower())
        query = query.order_by(City.display_name, Zone.display_name)
        return (await db.execute(query)).scalars().all()

    async def resolve_zone(self, db: AsyncSession, city_slug: str, zone_slug: str) -> Zone:
        city_slug = city_slug.lower().strip()
        zone_slug = zone_slug.lower().strip()
        zone = (
            await db.execute(
                select(Zone).join(City, Zone.city_id == City.id).where(City.slug == city_slug, Zone.slug == zone_slug, Zone.active == True)  # noqa: E712
            )
        ).scalar_one_or_none()
        if zone is None:
            raise ValueError(f"Zone '{zone_slug}' is not valid for city '{city_slug}'.")
        return zone

    async def get_city_zone_map(self, db: AsyncSession) -> Dict[str, List[str]]:
        zones = await self.get_active_zones(db)
        city_map: Dict[str, List[str]] = {}
        for zone in zones:
            city_map.setdefault(zone.city_ref.slug, []).append(zone.slug)
        return city_map


location_service = LocationService()
