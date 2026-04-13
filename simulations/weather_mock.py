"""
Weather API Simulator
Simulates OpenWeatherMap-style responses for Delhi zones.
Supports forced scenarios for demo and testing.
"""

import random
from datetime import datetime, timezone
from typing import Optional


class WeatherSimulator:
    """
    Returns realistic weather data for supported zones.
    Can be forced into specific scenarios for demos.

    Scenarios:
        'normal'       → typical weather, no triggers fire
        'heavy_rain'   → 40-60mm/hr rainfall
        'extreme_heat' → 44-48°C temperature
        'monsoon'      → rain + high humidity + wind
        'winter'       → cold, dry, clear
    """

    ZONE_COORDS = {
        # Delhi
        "south_delhi":   {"lat": 28.52, "lon": 77.22},
        "north_delhi":   {"lat": 28.70, "lon": 77.10},
        "east_delhi":    {"lat": 28.63, "lon": 77.30},
        "west_delhi":    {"lat": 28.65, "lon": 77.05},
        "central_delhi": {"lat": 28.64, "lon": 77.21},
        # Mumbai
        "south_mumbai":     {"lat": 18.93, "lon": 72.83},
        "western_suburbs":  {"lat": 19.10, "lon": 72.84},
        "eastern_suburbs":  {"lat": 19.07, "lon": 72.90},
        "navi_mumbai":      {"lat": 19.03, "lon": 73.02},
        # Bengaluru
        "koramangala":      {"lat": 12.93, "lon": 77.62},
        "whitefield":       {"lat": 12.97, "lon": 77.75},
        "indiranagar":      {"lat": 12.97, "lon": 77.64},
        "jayanagar":        {"lat": 12.93, "lon": 77.58},
        "electronic_city":  {"lat": 12.84, "lon": 77.67},
        # Chennai
        "t_nagar":    {"lat": 13.04, "lon": 80.23},
        "anna_nagar": {"lat": 13.09, "lon": 80.21},
        "adyar":      {"lat": 13.00, "lon": 80.26},
        "velachery":  {"lat": 12.98, "lon": 80.22},
    }

    def __init__(self, scenario: Optional[str] = None):
        self.scenario = scenario
        self.override = None

    def set_scenario(self, scenario: str):
        """Change the active scenario."""
        self.scenario = scenario

    def set_override(self, payload: dict | None):
        self.override = payload or None

    def clear_override(self):
        self.override = None

    def get_weather(self, zone: str) -> dict:
        """
        Get current weather for a zone.
        Returns OpenWeatherMap-compatible structure.
        """
        coords = self.ZONE_COORDS.get(zone, {"lat": 28.61, "lon": 77.20})

        if self.override:
            rainfall = round(float(self.override.get("rainfall_mm_hr", 0) or 0), 1)
            temperature = round(float(self.override.get("temperature_c", 30) or 30), 1)
            return {
                "zone": zone,
                "coordinates": coords,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rainfall_mm_hr": rainfall,
                "temperature_c": temperature,
                "humidity_percent": int(self.override.get("humidity_percent", 68) or 68),
                "wind_speed_kmh": round(float(self.override.get("wind_speed_kmh", 14) or 14), 1),
                "visibility_km": round(float(self.override.get("visibility_km", 5.0) or 5.0), 1),
                "condition": str(self.override.get("condition", "lab_override")),
                "api_source": "weather_simulator",
                "scenario": "lab_override",
            }

        if self.scenario == "heavy_rain":
            return self._heavy_rain(zone, coords)
        elif self.scenario == "extreme_heat":
            return self._extreme_heat(zone, coords)
        elif self.scenario == "monsoon":
            return self._monsoon(zone, coords)
        elif self.scenario == "winter":
            return self._winter(zone, coords)
        else:
            return self._normal(zone, coords)

    def _normal(self, zone: str, coords: dict) -> dict:
        """Normal day — no triggers should fire."""
        return {
            "zone": zone,
            "coordinates": coords,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rainfall_mm_hr": round(random.uniform(0, 10), 1),
            "temperature_c": round(random.uniform(25, 35), 1),
            "humidity_percent": random.randint(40, 70),
            "wind_speed_kmh": round(random.uniform(5, 20), 1),
            "visibility_km": round(random.uniform(5, 10), 1),
            "condition": "partly_cloudy",
            "api_source": "weather_simulator",
            "scenario": "normal"
        }

    def _heavy_rain(self, zone: str, coords: dict) -> dict:
        """Heavy rainfall — rain trigger should fire."""
        return {
            "zone": zone,
            "coordinates": coords,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rainfall_mm_hr": round(random.uniform(30, 60), 1),
            "temperature_c": round(random.uniform(22, 28), 1),
            "humidity_percent": random.randint(85, 98),
            "wind_speed_kmh": round(random.uniform(25, 45), 1),
            "visibility_km": round(random.uniform(0.5, 3), 1),
            "condition": "heavy_rain",
            "api_source": "weather_simulator",
            "scenario": "heavy_rain"
        }

    def _extreme_heat(self, zone: str, coords: dict) -> dict:
        """Extreme heat — heat trigger should fire."""
        return {
            "zone": zone,
            "coordinates": coords,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rainfall_mm_hr": 0.0,
            "temperature_c": round(random.uniform(44, 48), 1),
            "humidity_percent": random.randint(10, 25),
            "wind_speed_kmh": round(random.uniform(5, 15), 1),
            "visibility_km": round(random.uniform(3, 8), 1),
            "condition": "extreme_heat",
            "api_source": "weather_simulator",
            "scenario": "extreme_heat"
        }

    def _monsoon(self, zone: str, coords: dict) -> dict:
        """Monsoon — rain trigger fires, potentially flooding."""
        return {
            "zone": zone,
            "coordinates": coords,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rainfall_mm_hr": round(random.uniform(35, 80), 1),
            "temperature_c": round(random.uniform(24, 30), 1),
            "humidity_percent": random.randint(90, 100),
            "wind_speed_kmh": round(random.uniform(30, 60), 1),
            "visibility_km": round(random.uniform(0.2, 2), 1),
            "condition": "monsoon_heavy",
            "api_source": "weather_simulator",
            "scenario": "monsoon"
        }

    def _winter(self, zone: str, coords: dict) -> dict:
        """Winter — no triggers, low risk."""
        return {
            "zone": zone,
            "coordinates": coords,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rainfall_mm_hr": 0.0,
            "temperature_c": round(random.uniform(8, 18), 1),
            "humidity_percent": random.randint(50, 75),
            "wind_speed_kmh": round(random.uniform(3, 12), 1),
            "visibility_km": round(random.uniform(1, 5), 1),
            "condition": "cold_clear",
            "api_source": "weather_simulator",
            "scenario": "winter"
        }


# Singleton instance
weather_simulator = WeatherSimulator(scenario="normal")
