"""GPS spoofing simulation for adversarial fraud detection testing.

Generates mathematically anomalous WorkerActivity records to test
the fraud pipeline's ability to detect location spoofing attacks.
All generated records are tagged with is_simulated=True for data isolation.
"""

from __future__ import annotations

import math
import random
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import WorkerActivity
from backend.utils.time import utc_now_naive


# Reference coordinates for zones (lat, lon)
ZONE_COORDS: dict[str, tuple[float, float]] = {
    "south_delhi": (28.5200, 77.2200),
    "east_delhi": (28.6300, 77.3000),
    "north_delhi": (28.7100, 77.2100),
    "west_delhi": (28.6500, 77.1000),
    "koramangala": (12.9352, 77.6245),
    "whitefield": (12.9698, 77.7500),
    "indiranagar": (12.9716, 77.6412),
    "t_nagar": (13.0418, 80.2341),
    "banjara_hills": (17.4100, 78.4300),
    "hinjawadi": (18.5912, 73.7390),
    "salt_lake": (22.5800, 88.4100),
}

# Teleport targets — far enough to make velocity physically impossible
TELEPORT_TARGETS: list[tuple[str, float, float]] = [
    ("navi_mumbai", 19.0330, 73.0297),
    ("jaipur", 26.9124, 75.7873),
    ("chennai_central", 13.0827, 80.2707),
    ("kolkata_central", 22.5726, 88.3639),
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class SpoofSimulator:
    """Generates anomalous GPS footprints for adversarial testing."""

    async def inject_teleportation_attack(
        self,
        db: AsyncSession,
        worker_id: UUID,
        base_zone: str,
        intensity: str = "high",
    ) -> dict:
        """Inject a teleportation attack — impossible velocity between pings.

        Pattern: base zone → distant city → back to base zone
        Resulting velocity: 500-2000+ km/h (physically impossible)
        """
        base_lat, base_lon = ZONE_COORDS.get(base_zone, (28.5200, 77.2200))
        target_name, target_lat, target_lon = random.choice(TELEPORT_TARGETS)
        now = utc_now_naive()

        record_count = 8 if intensity == "high" else 6
        window_minutes = 30
        step_minutes = window_minutes / (record_count - 1)

        records = []
        for i in range(record_count):
            timestamp = now - timedelta(minutes=window_minutes) + timedelta(minutes=i * step_minutes)

            if intensity == "high":
                # High: rapid oscillation between base and target
                if i % 2 == 0:
                    lat = base_lat + random.uniform(-0.005, 0.005)
                    lon = base_lon + random.uniform(-0.005, 0.005)
                    speed = random.uniform(10, 30)
                else:
                    lat = target_lat + random.uniform(-0.003, 0.003)
                    lon = target_lon + random.uniform(-0.003, 0.003)
                    speed = random.uniform(5, 25)
            else:
                # Medium: single jump in the middle
                if i < record_count // 3 or i > 2 * record_count // 3:
                    lat = base_lat + random.uniform(-0.003, 0.003)
                    lon = base_lon + random.uniform(-0.003, 0.003)
                    speed = random.uniform(12, 28)
                else:
                    lat = target_lat + random.uniform(-0.003, 0.003)
                    lon = target_lon + random.uniform(-0.003, 0.003)
                    speed = random.uniform(8, 20)

            record = WorkerActivity(
                worker_id=worker_id,
                zone=base_zone,
                latitude=Decimal(str(round(lat, 7))),
                longitude=Decimal(str(round(lon, 7))),
                speed_kmh=Decimal(str(round(speed, 1))),
                has_delivery_stop=(i % 3 == 0),
                is_simulated=True,
                simulation_type="gps_teleportation",
                recorded_at=timestamp,
            )
            db.add(record)
            records.append(record)

        await db.flush()

        # Calculate actual implied velocities for the report
        velocities = []
        for j in range(1, len(records)):
            dist = _haversine_km(
                float(records[j - 1].latitude), float(records[j - 1].longitude),
                float(records[j].latitude), float(records[j].longitude),
            )
            dt_hours = step_minutes / 60
            velocities.append(round(dist / dt_hours, 1) if dt_hours > 0 else 0)

        return {
            "spoof_type": "teleportation",
            "intensity": intensity,
            "records_injected": len(records),
            "base_zone": base_zone,
            "teleport_target": target_name,
            "implied_velocities_kmh": velocities,
            "max_velocity_kmh": max(velocities) if velocities else 0,
            "distance_km": round(_haversine_km(base_lat, base_lon, target_lat, target_lon), 1),
        }

    async def inject_stationary_spoof(
        self,
        db: AsyncSession,
        worker_id: UUID,
        base_zone: str,
        intensity: str = "high",
    ) -> dict:
        """Inject a stationary spoof — fixed GPS with fake delivery activity.

        Pattern: All coordinates within ±0.000001° (spoofer jitter),
        but with has_delivery_stop=True and alternating fake speeds.
        Real delivery would drift GPS by 0.001-0.01°.
        """
        base_lat, base_lon = ZONE_COORDS.get(base_zone, (28.5200, 77.2200))
        now = utc_now_naive()

        record_count = 12 if intensity == "high" else 8
        window_minutes = 45
        step_minutes = window_minutes / (record_count - 1)

        # Jitter range: realistic spoofer tries to look natural
        jitter = 0.000001 if intensity == "high" else 0.00005

        records = []
        for i in range(record_count):
            timestamp = now - timedelta(minutes=window_minutes) + timedelta(minutes=i * step_minutes)

            lat = base_lat + random.uniform(-jitter, jitter)
            lon = base_lon + random.uniform(-jitter, jitter)

            # Fake speeds that contradict zero movement
            if intensity == "high":
                speed = random.choice([0.0, 0.0, 15.0, 18.0, 22.0, 25.0])
            else:
                speed = random.uniform(0, 12)

            record = WorkerActivity(
                worker_id=worker_id,
                zone=base_zone,
                latitude=Decimal(str(round(lat, 7))),
                longitude=Decimal(str(round(lon, 7))),
                speed_kmh=Decimal(str(round(speed, 1))),
                has_delivery_stop=True,  # Claims delivery but GPS is static
                is_simulated=True,
                simulation_type="gps_stationary",
                recorded_at=timestamp,
            )
            db.add(record)
            records.append(record)

        await db.flush()

        # Calculate coordinate spread
        lats = [float(r.latitude) for r in records]
        lons = [float(r.longitude) for r in records]
        spread_deg = max(max(lats) - min(lats), max(lons) - min(lons))

        return {
            "spoof_type": "stationary",
            "intensity": intensity,
            "records_injected": len(records),
            "base_zone": base_zone,
            "coordinate_spread_degrees": round(spread_deg, 8),
            "delivery_stops_claimed": sum(1 for r in records if r.has_delivery_stop),
            "nonzero_speeds": sum(1 for r in records if float(r.speed_kmh or 0) > 0),
        }


spoof_simulator = SpoofSimulator()
