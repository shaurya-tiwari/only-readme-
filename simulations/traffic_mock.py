"""
Traffic API Simulator
Simulates TomTom/HERE Maps congestion data.
"""

import random
from datetime import datetime, timezone
from typing import Optional


class TrafficSimulator:
    """
    Simulates traffic congestion index per zone.

    Congestion index: 0.0 (free flow) to 1.0 (gridlock)
    Trigger threshold: 0.75

    Scenarios:
        'normal'    → 0.2-0.5 congestion
        'rush_hour' → 0.5-0.7
        'severe'    → 0.75-0.95 (trigger fires)
        'gridlock'  → 0.9-1.0
    """

    # Peak hour patterns (hour: base congestion multiplier)
    PEAK_HOURS = {
        8: 1.3, 9: 1.5, 10: 1.2,         # morning rush
        12: 1.1, 13: 1.2,                  # lunch
        17: 1.3, 18: 1.5, 19: 1.6, 20: 1.4,  # evening rush
        21: 1.2
    }

    def __init__(self, scenario: Optional[str] = None):
        self.scenario = scenario
        self.override = None

    def set_scenario(self, scenario: str):
        self.scenario = scenario

    def set_override(self, payload: dict | None):
        self.override = payload or None

    def clear_override(self):
        self.override = None

    def get_traffic(self, zone: str) -> dict:
        """Get current traffic congestion for a zone."""
        hour = datetime.now(timezone.utc).hour
        peak_mult = self.PEAK_HOURS.get(hour, 1.0)

        if self.override:
            congestion = round(min(1.0, max(0.0, float(self.override.get("congestion_index", 0) or 0))), 2)
        elif self.scenario == "severe":
            congestion = round(random.uniform(0.75, 0.95), 2)
        elif self.scenario == "gridlock":
            congestion = round(random.uniform(0.90, 1.00), 2)
        elif self.scenario == "rush_hour":
            congestion = round(random.uniform(0.50, 0.70) * peak_mult, 2)
            congestion = min(congestion, 0.95)
        else:
            base = random.uniform(0.15, 0.45)
            congestion = round(base * peak_mult, 2)
            congestion = min(congestion, 0.70)

        if congestion > 0.75:
            level = "severe"
        elif congestion > 0.50:
            level = "heavy"
        elif congestion > 0.30:
            level = "moderate"
        else:
            level = "free_flow"

        return {
            "zone": zone,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "congestion_index": congestion,
            "congestion_level": level,
            "average_speed_kmh": round(float(self.override.get("average_speed_kmh")) if self.override and self.override.get("average_speed_kmh") is not None else max(5, 40 * (1 - congestion)), 1),
            "delay_minutes": round(float(self.override.get("delay_minutes")) if self.override and self.override.get("delay_minutes") is not None else (congestion * 30), 1),
            "incidents": int(self.override.get("incidents")) if self.override and self.override.get("incidents") is not None else (random.randint(0, 3) if congestion > 0.5 else 0),
            "api_source": "traffic_simulator",
            "scenario": "lab_override" if self.override else (self.scenario or "normal")
        }


# Singleton
traffic_simulator = TrafficSimulator(scenario="normal")
