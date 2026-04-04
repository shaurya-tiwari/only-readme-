"""RideShield configuration."""

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
    ENV: str = ENV
    DEBUG: bool = ENV != "prod"
    SQL_ECHO: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    FILE_LOGGING_ENABLED: bool = ENV != "prod"
    SESSION_SECRET: str
    SESSION_DURATION_HOURS: int = 72
    SESSION_COOKIE_SAMESITE: str = "none" if ENV == "prod" else "lax"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    AUTH_RATE_LIMIT_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    ML_ENABLED: bool = True
    ML_ARTIFACT_DIR: str = "backend/ml/artifacts"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rideshield:rideshield123@localhost:5433/rideshield_db"
    DATABASE_URL_SYNC: str = "postgresql://rideshield:rideshield123@localhost:5433/rideshield_db"

    # Simulation
    SIMULATION_MODE: bool = True
    ENABLE_TRIGGER_SCHEDULER: bool = True
    TRIGGER_CHECK_INTERVAL_SECONDS: int = 300
    SIGNAL_SOURCE_MODE: str = "mock"
    WEATHER_SOURCE: str = "mock"
    AQI_SOURCE: str = "mock"
    TRAFFIC_SOURCE: str = "mock"
    PLATFORM_SOURCE: str = "mock"
    ENABLE_PROVIDER_SNAPSHOT_PERSISTENCE: bool = True
    ENABLE_SHADOW_DIFF_LOGGING: bool = True
    ENABLE_SHADOW_DIFF_PERSISTENCE: bool = True
    SIGNAL_SNAPSHOT_RETENTION_DAYS: int = 14
    SHADOW_DIFF_RETENTION_DAYS: int = 14
    SIGNAL_RETENTION_CLEANUP_INTERVAL: int = 100
    SHADOW_DIFF_ALERT_DELTA: float = 0.15
    FORECAST_SNAPSHOT_LOOKBACK_HOURS: int = 24
    FORECAST_SNAPSHOT_HISTORY_LIMIT: int = 12
    FORECAST_SIGNAL_SMOOTHING_WEIGHT: float = 0.7

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
    OPERATING_COST_FACTOR: float = 0.85

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

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ALLOWED_ORIGINS.split(",") if item.strip()]


    @field_validator("SESSION_COOKIE_SAMESITE", mode="before")
    @classmethod
    def validate_cookie_samesite(cls, value: Any) -> str:
        normalized = str(value or "lax").strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("SESSION_COOKIE_SAMESITE must be one of: lax, strict, none")
        return normalized


    @field_validator("SIGNAL_SOURCE_MODE", mode="before")
    @classmethod
    def validate_signal_source_mode(cls, value: Any) -> str:
        normalized = str(value or "mock").strip().lower()
        allowed = {"mock", "real", "shadow"}
        if normalized not in allowed:
            raise ValueError(f"SIGNAL_SOURCE_MODE must be one of {sorted(allowed)}")
        return normalized

    @field_validator("WEATHER_SOURCE", "AQI_SOURCE", "TRAFFIC_SOURCE", mode="before")
    @classmethod
    def validate_standard_signal_source(cls, value: Any) -> str:
        normalized = str(value or "mock").strip().lower()
        allowed = {"mock", "real"}
        if normalized not in allowed:
            raise ValueError(f"Signal source must be one of {sorted(allowed)}")
        return normalized

    @field_validator("PLATFORM_SOURCE", mode="before")
    @classmethod
    def validate_platform_source(cls, value: Any) -> str:
        normalized = str(value or "mock").strip().lower()
        allowed = {"mock", "db", "partner"}
        if normalized not in allowed:
            raise ValueError(f"PLATFORM_SOURCE must be one of {sorted(allowed)}")
        return normalized

    @field_validator(
        "SIGNAL_SNAPSHOT_RETENTION_DAYS",
        "SHADOW_DIFF_RETENTION_DAYS",
        "SIGNAL_RETENTION_CLEANUP_INTERVAL",
        "FORECAST_SNAPSHOT_LOOKBACK_HOURS",
        "FORECAST_SNAPSHOT_HISTORY_LIMIT",
        mode="before",
    )
    @classmethod
    def validate_positive_ints(cls, value: Any) -> int:
        parsed = int(value or 0)
        if parsed < 1:
            raise ValueError("Value must be >= 1")
        return parsed

    @field_validator("SHADOW_DIFF_ALERT_DELTA", "FORECAST_SIGNAL_SMOOTHING_WEIGHT", mode="before")
    @classmethod
    def validate_unit_interval(cls, value: Any) -> float:
        parsed = float(value or 0)
        if not 0 <= parsed <= 1:
            raise ValueError("Value must be between 0 and 1")
        return parsed

    @property
    def signal_runtime_config(self) -> dict[str, Any]:
        return {
            "mode": self.SIGNAL_SOURCE_MODE,
            "providers": {
                "weather": {"source": self.WEATHER_SOURCE},
                "aqi": {"source": self.AQI_SOURCE},
                "traffic": {"source": self.TRAFFIC_SOURCE},
                "platform": {"source": self.PLATFORM_SOURCE},
            },
            "shadow_diff": {
                "logging_enabled": self.ENABLE_SHADOW_DIFF_LOGGING,
                "persistence_enabled": self.ENABLE_SHADOW_DIFF_PERSISTENCE,
                "alert_delta": self.SHADOW_DIFF_ALERT_DELTA,
                "retention_days": self.SHADOW_DIFF_RETENTION_DAYS,
            },
            "snapshots": {
                "persistence_enabled": self.ENABLE_PROVIDER_SNAPSHOT_PERSISTENCE,
                "retention_days": self.SIGNAL_SNAPSHOT_RETENTION_DAYS,
                "cleanup_interval": self.SIGNAL_RETENTION_CLEANUP_INTERVAL,
            },
            "forecast_preprocessing": {
                "lookback_hours": self.FORECAST_SNAPSHOT_LOOKBACK_HOURS,
                "history_limit": self.FORECAST_SNAPSHOT_HISTORY_LIMIT,
                "smoothing_weight": self.FORECAST_SIGNAL_SMOOTHING_WEIGHT,
            },
        }


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
