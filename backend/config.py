"""
RideShield Configuration
Loads all settings from environment variables with sensible defaults.
"""

import os
from typing import Any, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV = os.getenv("ENV", "dev").strip().lower()
ENV_FILE = ".env.test" if ENV == "test" else ".env"


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "RideShield"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SQL_ECHO: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SESSION_SECRET: str = "rideshield-sprint3-demo-secret"
    SESSION_DURATION_HOURS: int = 72
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "rideshield-admin"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rideshield:rideshield123@localhost:5433/rideshield_db"
    DATABASE_URL_SYNC: str = "postgresql://rideshield:rideshield123@localhost:5433/rideshield_db"

    # Simulation
    SIMULATION_MODE: bool = True
    ENABLE_TRIGGER_SCHEDULER: bool = True
    TRIGGER_CHECK_INTERVAL_SECONDS: int = 300

    # External APIs
    OPENWEATHER_API_KEY: Optional[str] = None
    WAQI_API_KEY: Optional[str] = None
    TOMTOM_API_KEY: Optional[str] = None

    # Payments
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None

    # Insurance Config
    ACTIVATION_DELAY_HOURS: int = 24
    POLICY_DURATION_DAYS: int = 7
    MAX_PREMIUM_CHANGE_PERCENT: int = 20
    CLUSTER_FRAUD_THRESHOLD: int = 5

    # Trigger Thresholds
    RAIN_THRESHOLD_MM: float = 25.0
    HEAT_THRESHOLD_C: float = 44.0
    AQI_THRESHOLD: int = 300
    TRAFFIC_THRESHOLD: float = 0.75
    PLATFORM_OUTAGE_THRESHOLD: float = 0.60
    SOCIAL_INACTIVITY_THRESHOLD: float = 0.60

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return True

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False

        return bool(value)

    # City Risk Profiles
    CITY_RISK_PROFILES: dict = {
        "delhi": {
            "base_risk": 0.65,
            "avg_daily_income": 900,
            "zones": ["south_delhi", "north_delhi", "east_delhi", "west_delhi", "central_delhi"]
        },
        "mumbai": {
            "base_risk": 0.60,
            "avg_daily_income": 850,
            "zones": ["south_mumbai", "western_suburbs", "eastern_suburbs", "navi_mumbai"]
        },
        "bengaluru": {
            "base_risk": 0.30,
            "avg_daily_income": 800,
            "zones": ["koramangala", "whitefield", "indiranagar", "jayanagar", "electronic_city"]
        },
        "chennai": {
            "base_risk": 0.50,
            "avg_daily_income": 750,
            "zones": ["t_nagar", "anna_nagar", "adyar", "velachery"]
        }
    }

    # Plan Definitions
    PLAN_DEFINITIONS: dict = {
        "basic_protect": {
            "display_name": "Basic Protect",
            "base_price": 29,
            "plan_factor": 1.0,
            "coverage_cap": 300,
            "triggers_covered": ["platform_outage"],
            "description": "Entry-level protection against platform outages",
            "color": "green"
        },
        "smart_protect": {
            "display_name": "Smart Protect",
            "base_price": 39,
            "plan_factor": 1.5,
            "coverage_cap": 600,
            "triggers_covered": ["rain", "heat", "aqi", "traffic", "platform_outage"],
            "description": "Weather + platform protection for active riders",
            "color": "yellow"
        },
        "assured_plan": {
            "display_name": "Assured Plan",
            "base_price": 49,
            "plan_factor": 2.0,
            "coverage_cap": 800,
            "triggers_covered": ["rain", "heat", "aqi", "traffic", "platform_outage", "social"],
            "description": "All triggers with guaranteed minimum payout floor",
            "color": "red"
        },
        "pro_max": {
            "display_name": "Pro Max",
            "base_price": 59,
            "plan_factor": 2.5,
            "coverage_cap": 1000,
            "triggers_covered": ["rain", "heat", "aqi", "traffic", "platform_outage", "social"],
            "description": "Full protection with predictive alerts and fastest payouts",
            "color": "purple"
        }
    }

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
    )


settings = Settings()
