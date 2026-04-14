import random
import uuid
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import WorkerActivity
from backend.utils.time import utc_now_naive

class LocationSpoofSimulator:
    """Mock generator for GPS adversarial attacks."""

    async def inject_stationary_spoof(
        self, db: AsyncSession, worker_id: uuid.UUID, base_zone: str, intensity: str = "high"
    ) -> dict:
        """
        Simulates a worker using a GPS pin-drop app. 
        The coordinates remain exactly identical down to the 7th decimal degree, 
        which never happens naturally due to GPS drift.
        """
        now = utc_now_naive()
        
        # Hardcoded pin location
        fixed_lat = 28.5355161
        fixed_lon = 77.3910265
        
        events = []
        # Generate 15 points over last 2 hours
        for i in range(15):
            point_time = now - timedelta(minutes=(15 - i) * 8)
            activity = WorkerActivity(
                worker_id=worker_id,
                zone=base_zone,
                latitude=fixed_lat,
                longitude=fixed_lon,
                speed_kmh=random.uniform(10, 40) if intensity == "high" else 0.0,
                has_delivery_stop=True if i % 3 == 0 else False,
                is_simulated=True,
                simulation_type="spoof_stationary",
                recorded_at=point_time
            )
            db.add(activity)
            events.append({
                "time": point_time.isoformat(),
                "lat": fixed_lat,
                "lon": fixed_lon,
                "speed": float(activity.speed_kmh)
            })
            
        return {
            "spoof_type": "stationary_pin_drop",
            "events_injected": len(events),
            "description": "Zero GPS drift detected. 15 pings returned identical coordinates despite speed > 0."
        }

    async def inject_teleportation_attack(
        self, db: AsyncSession, worker_id: uuid.UUID, base_zone: str, intensity: str = "high"
    ) -> dict:
        """
        Simulates impossible travel speed (e.g., jumping between cities in 2 minutes)
        often used by fraudsters sharing accounts across states.
        """
        now = utc_now_naive()
        
        # Point A: Delhi
        delhi_lat = 28.6139
        delhi_lon = 77.2090
        
        # Point B: Mumbai (1400km away)
        mumbai_lat = 19.0760
        mumbai_lon = 72.8777
        
        events = []
        
        # Legitimate working in Delhi 2 hours ago
        for i in range(5):
            point_time = now - timedelta(hours=2) + timedelta(minutes=i*5)
            activity = WorkerActivity(
                worker_id=worker_id,
                zone=base_zone,
                latitude=delhi_lat + random.uniform(-0.01, 0.01),
                longitude=delhi_lon + random.uniform(-0.01, 0.01),
                speed_kmh=random.uniform(20, 50),
                has_delivery_stop=False,
                is_simulated=True,
                simulation_type="spoof_teleport",
                recorded_at=point_time
            )
            db.add(activity)
            events.append({"loc": "Delhi", "time": point_time.isoformat()})
            
        # Suddenly pinging in Mumbai 5 minutes later
        for i in range(5):
            point_time = now - timedelta(hours=2) + timedelta(minutes=25 + i*5)
            activity = WorkerActivity(
                worker_id=worker_id,
                zone="western_suburbs",  # Mumbai zone
                latitude=mumbai_lat + random.uniform(-0.01, 0.01),
                longitude=mumbai_lon + random.uniform(-0.01, 0.01),
                speed_kmh=random.uniform(30, 60),
                has_delivery_stop=True,
                is_simulated=True,
                simulation_type="spoof_teleport",
                recorded_at=point_time
            )
            db.add(activity)
            events.append({"loc": "Mumbai", "time": point_time.isoformat()})

        return {
            "spoof_type": "teleportation",
            "events_injected": len(events),
            "description": "Calculated speed between pings exceeded 16,800 km/h (Delhi -> Mumbai in 5 mins)."
        }

spoof_simulator = LocationSpoofSimulator()
