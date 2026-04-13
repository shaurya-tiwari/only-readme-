"""
AQI API Simulator
Simulates air quality data for zones.
Delhi-specific: AQI regularly exceeds 300 in winter.
"""

import random
from datetime import datetime, timezone
from typing import Optional


class AQISimulator:
    """
    Simulates AQI (Air Quality Index) data.

    Scenarios:
        'normal'     → AQI 50-150 (acceptable)
        'moderate'   → AQI 150-250
        'hazardous'  → AQI 300-500 (trigger fires)
        'severe'     → AQI 400-500
    """

    # City baseline AQI ranges
    CITY_BASELINES = {
        "delhi":     {"min": 80, "max": 200},   # Delhi has bad baseline
        "mumbai":    {"min": 40, "max": 120},
        "bengaluru": {"min": 30, "max": 90},
        "chennai":   {"min": 40, "max": 100}
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

    def get_aqi(self, zone: str, city: str = "delhi") -> dict:
        """Get current AQI for a zone."""

        city = city.lower()
        baseline = self.CITY_BASELINES.get(city, {"min": 50, "max": 150})

        if self.override:
            aqi_value = int(self.override.get("aqi_value", baseline["max"]) or baseline["max"])
            if aqi_value < 50:
                category = "good"
            elif aqi_value < 100:
                category = "moderate"
            elif aqi_value < 150:
                category = "unhealthy_sensitive"
            elif aqi_value < 300:
                category = "unhealthy"
            elif aqi_value < 400:
                category = "hazardous"
            else:
                category = "severe"
        elif self.scenario == "hazardous":
            aqi_value = random.randint(300, 500)
            category = "hazardous"
        elif self.scenario == "severe":
            aqi_value = random.randint(400, 500)
            category = "severe"
        elif self.scenario == "moderate":
            aqi_value = random.randint(150, 250)
            category = "unhealthy"
        else:
            aqi_value = random.randint(baseline["min"], baseline["max"])
            if aqi_value < 50:
                category = "good"
            elif aqi_value < 100:
                category = "moderate"
            elif aqi_value < 150:
                category = "unhealthy_sensitive"
            else:
                category = "unhealthy"

        return {
            "zone": zone,
            "city": city,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "aqi_value": aqi_value,
            "category": category,
            "dominant_pollutant": self.override.get("dominant_pollutant") if self.override and self.override.get("dominant_pollutant") else random.choice(["PM2.5", "PM10", "NO2", "O3"]),
            "pm25": round(float(self.override.get("pm25")) if self.override and self.override.get("pm25") is not None else random.uniform(20, aqi_value * 0.8), 1),
            "pm10": round(float(self.override.get("pm10")) if self.override and self.override.get("pm10") is not None else random.uniform(30, aqi_value * 1.2), 1),
            "api_source": "aqi_simulator",
            "scenario": "lab_override" if self.override else (self.scenario or "normal")
        }


# Singleton
aqi_simulator = AQISimulator(scenario="normal")
