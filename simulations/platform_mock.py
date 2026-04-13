"""
Platform API Simulator
Simulates Zomato/Swiggy order density and platform health.
"""

import random
from datetime import datetime, timezone
from typing import Optional


class PlatformSimulator:
    """
    Simulates delivery platform order density per zone.

    Scenarios:
        'normal'         → 30-60 orders/hr, healthy
        'low_demand'     → 10-20 orders/hr
        'platform_outage'→ 0-5 orders/hr (trigger fires at >60% drop)
        'peak_demand'    → 60-100 orders/hr
    """

    NORMAL_ORDER_RANGE = {"min": 30, "max": 60}

    def __init__(self, scenario: Optional[str] = None):
        self.scenario = scenario
        self.override = None

    def set_scenario(self, scenario: str):
        self.scenario = scenario

    def set_override(self, payload: dict | None):
        self.override = payload or None

    def clear_override(self):
        self.override = None

    def get_platform_status(self, zone: str) -> dict:
        """Get current platform order density for a zone."""

        normal_avg = (self.NORMAL_ORDER_RANGE["min"] + self.NORMAL_ORDER_RANGE["max"]) / 2

        if self.override:
            density_drop = min(1.0, max(0.0, float(self.override.get("order_density_drop", 0) or 0)))
            orders_per_hour = int(round(normal_avg * (1 - density_drop)))
            active_restaurants = int(self.override.get("active_restaurants", max(1, 20 - density_drop * 12)) or max(1, 20 - density_drop * 12))
            platform_status = str(self.override.get("platform_status", "degraded" if density_drop >= 0.6 else "operational"))
        elif self.scenario == "platform_outage":
            orders_per_hour = random.randint(0, 5)
            active_restaurants = random.randint(1, 5)
            platform_status = "degraded"
        elif self.scenario == "low_demand":
            orders_per_hour = random.randint(10, 20)
            active_restaurants = random.randint(10, 20)
            platform_status = "operational"
        elif self.scenario == "peak_demand":
            orders_per_hour = random.randint(60, 100)
            active_restaurants = random.randint(25, 40)
            platform_status = "operational"
        else:
            orders_per_hour = random.randint(
                self.NORMAL_ORDER_RANGE["min"],
                self.NORMAL_ORDER_RANGE["max"]
            )
            active_restaurants = random.randint(20, 35)
            platform_status = "operational"

        density_drop = max(0, 1 - (orders_per_hour / normal_avg))

        return {
            "zone": zone,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "orders_per_hour": orders_per_hour,
            "normal_avg_orders": int(normal_avg),
            "order_density_drop": round(density_drop, 2),
            "active_restaurants": active_restaurants,
            "active_riders": int(self.override.get("active_riders")) if self.override and self.override.get("active_riders") is not None else random.randint(
                max(1, orders_per_hour // 3),
                max(2, orders_per_hour // 2)
            ),
            "avg_delivery_time_min": round(float(self.override.get("avg_delivery_time_min")) if self.override and self.override.get("avg_delivery_time_min") is not None else random.uniform(20, 45 + (density_drop * 30)), 1),
            "platform_status": platform_status,
            "api_source": "platform_simulator",
            "scenario": "lab_override" if self.override else (self.scenario or "normal")
        }


# Singleton
platform_simulator = PlatformSimulator(scenario="normal")
