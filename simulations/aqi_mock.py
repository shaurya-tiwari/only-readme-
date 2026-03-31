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

    def set_scenario(self, scenario: str):
        self.scenario = scenario

    def get_aqi(self, zone: str, city: str = "delhi") -> dict:
        """Get current AQI for a zone."""

        city = city.lower()
        baseline = self.CITY_BASELINES.get(city, {"min": 50, "max": 150})

        if self.scenario == "hazardous":
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
            "dominant_pollutant": random.choice(["PM2.5", "PM10", "NO2", "O3"]),
            "pm25": round(random.uniform(20, aqi_value * 0.8), 1),
            "pm10": round(random.uniform(30, aqi_value * 1.2), 1),
            "api_source": "aqi_simulator",
            "scenario": self.scenario or "normal"
        }


# Singleton
aqi_simulator = AQISimulator(scenario="normal")