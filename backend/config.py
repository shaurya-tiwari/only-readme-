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
    SESSION_COOKIE_SECURE: bool = ENV == "prod"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    AUTH_RATE_LIMIT_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    ML_ENABLED: bool = True
    ML_ARTIFACT_DIR: str = "backend/ml/artifacts"
    RISK_ML_ARTIFACT_DIR: str | None = "backend/ml/artifacts_v2"
    FRAUD_ML_ARTIFACT_DIR: str | None = "backend/ml/artifacts"
    
    # Meta WhatsApp Integration
    META_ACCESS_TOKEN: Optional[str] = None
    PHONE_NUMBER_ID: Optional[str] = None
    VERIFY_TOKEN: str = "rideshield_verify_token"
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None


    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rideshield:rideshield123@localhost:5433/rideshield_db"
    DATABASE_URL_SYNC: str = "postgresql://rideshield:rideshield123@localhost:5433/rideshield_db"

    # Simulation
    SIMULATION_MODE: bool = True
    ENABLE_TRIGGER_SCHEDULER: bool = True
    SCHEDULER_IN_PROCESS: bool = False
    SCHEDULER_FETCH_CONCURRENCY: int = 6
    TRIGGER_CHECK_INTERVAL_SECONDS: int = 300
    TRAFFIC_DAILY_REQUEST_BUDGET: int = 2400
    SIGNAL_SOURCE_MODE: str = "mock"
    WEATHER_SOURCE: str = "mock"
    AQI_SOURCE: str = "mock"
    TRAFFIC_SOURCE: str = "mock"
    PLATFORM_SOURCE: str = "mock"
    ENABLE_PROVIDER_SNAPSHOT_PERSISTENCE: bool = True
    ENABLE_SHADOW_DIFF_LOGGING: bool = True
    ENABLE_SHADOW_DIFF_PERSISTENCE: bool = True
    ENABLE_DECISION_MEMORY: bool = True
    DECISION_POLICY_VERSION: str = "decision-policy-v3-wave1"
    DECISION_APPROVED_THRESHOLD: float = 0.62
    DECISION_BORDERLINE_APPROVED_THRESHOLD: float = 0.58
    DECISION_DELAYED_THRESHOLD: float = 0.42
    DECISION_LOW_PAYOUT_CONFIDENT_CAP: int = 175
    DECISION_WEAK_SIGNAL_CONFIDENT_CAP: int = 200
    DECISION_BORDERLINE_CONFIDENT_CAP: int = 220
    DECISION_FALSE_REVIEW_PAYOUT_CAP: int = 125
    DECISION_FALSE_REVIEW_SCORE_FLOOR: float = 0.60
    DECISION_DEVICE_MICRO_PAYOUT_CAP: int = 40
    DECISION_CLUSTER_MICRO_PAYOUT_CAP: int = 35
    DECISION_LOW_PAYOUT_THRESHOLD: int = 100
    DECISION_HIGH_PAYOUT_THRESHOLD: int = 200
    DECISION_HIGH_TRUST_THRESHOLD: float = 0.75
    DECISION_LOW_CONFIDENCE_THRESHOLD: float = 0.45
    DECISION_GRAY_BAND_LOW: float = 0.58
    DECISION_GRAY_BAND_HIGH: float = 0.62
    DECISION_HIGH_CONFIDENCE_THRESHOLD: float = 0.70
    DECISION_MODERATE_CONFIDENCE_THRESHOLD: float = 0.45
    DECISION_REASON_LIMIT: int = 3
    POLICY_TRUTH_TRAFFIC_SOURCES: str = "baseline"
    POLICY_SYNTHETIC_TRAFFIC_SOURCES: str = "simulation_pressure,scenario,replay_amplified"
    SIGNAL_SNAPSHOT_RETENTION_DAYS: int = 1
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

    @field_validator("SESSION_COOKIE_SECURE", mode="before")
    @classmethod
    def parse_cookie_secure(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False

        return bool(value)

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ALLOWED_ORIGINS.split(",") if item.strip()]

    @property
    def policy_truth_traffic_sources(self) -> list[str]:
        return [item.strip() for item in self.POLICY_TRUTH_TRAFFIC_SOURCES.split(",") if item.strip()]

    @property
    def policy_synthetic_traffic_sources(self) -> list[str]:
        return [item.strip() for item in self.POLICY_SYNTHETIC_TRAFFIC_SOURCES.split(",") if item.strip()]


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
        allowed = {"mock", "real", "shadow", "demo"}
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
        "DECISION_LOW_PAYOUT_CONFIDENT_CAP",
        "DECISION_WEAK_SIGNAL_CONFIDENT_CAP",
        "DECISION_BORDERLINE_CONFIDENT_CAP",
        "DECISION_FALSE_REVIEW_PAYOUT_CAP",
        "DECISION_DEVICE_MICRO_PAYOUT_CAP",
        "DECISION_CLUSTER_MICRO_PAYOUT_CAP",
        "DECISION_LOW_PAYOUT_THRESHOLD",
        "DECISION_HIGH_PAYOUT_THRESHOLD",
        "DECISION_REASON_LIMIT",
        "TRAFFIC_DAILY_REQUEST_BUDGET",
        mode="before",
    )
    @classmethod
    def validate_positive_ints(cls, value: Any) -> int:
        parsed = int(value or 0)
        if parsed < 1:
            raise ValueError("Value must be >= 1")
        return parsed

    @field_validator(
        "SHADOW_DIFF_ALERT_DELTA",
        "FORECAST_SIGNAL_SMOOTHING_WEIGHT",
        "DECISION_APPROVED_THRESHOLD",
        "DECISION_BORDERLINE_APPROVED_THRESHOLD",
        "DECISION_DELAYED_THRESHOLD",
        "DECISION_FALSE_REVIEW_SCORE_FLOOR",
        "DECISION_HIGH_TRUST_THRESHOLD",
        "DECISION_LOW_CONFIDENCE_THRESHOLD",
        "DECISION_GRAY_BAND_LOW",
        "DECISION_GRAY_BAND_HIGH",
        "DECISION_HIGH_CONFIDENCE_THRESHOLD",
        "DECISION_MODERATE_CONFIDENCE_THRESHOLD",
        mode="before",
    )
    @classmethod
    def validate_unit_interval(cls, value: Any) -> float:
        parsed = float(value or 0)
        if not 0 <= parsed <= 1:
            raise ValueError("Value must be between 0 and 1")
        return parsed

    @field_validator("DECISION_REASON_LIMIT")
    @classmethod
    def validate_reason_limit(cls, value: Any) -> int:
        parsed = int(value or 0)
        if parsed < 1 or parsed > 5:
            raise ValueError("DECISION_REASON_LIMIT must be between 1 and 5")
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
            "decision_memory": {
                "enabled": self.ENABLE_DECISION_MEMORY,
                "decision_policy_version": self.DECISION_POLICY_VERSION,
                "truth_traffic_sources": self.policy_truth_traffic_sources,
                "synthetic_traffic_sources": self.policy_synthetic_traffic_sources,
            },
            "decision_policy": {
                "thresholds": {
                    "approved": self.DECISION_APPROVED_THRESHOLD,
                    "borderline_approved": self.DECISION_BORDERLINE_APPROVED_THRESHOLD,
                    "delayed": self.DECISION_DELAYED_THRESHOLD,
                },
                "payout_caps": {
                    "low_payout_confident": self.DECISION_LOW_PAYOUT_CONFIDENT_CAP,
                    "weak_signal_confident": self.DECISION_WEAK_SIGNAL_CONFIDENT_CAP,
                    "borderline_confident": self.DECISION_BORDERLINE_CONFIDENT_CAP,
                    "false_review_safe_lane": self.DECISION_FALSE_REVIEW_PAYOUT_CAP,
                    "device_micro_payout": self.DECISION_DEVICE_MICRO_PAYOUT_CAP,
                    "cluster_micro_payout": self.DECISION_CLUSTER_MICRO_PAYOUT_CAP,
                },
                "guardrails": {
                    "low_payout": self.DECISION_LOW_PAYOUT_THRESHOLD,
                    "high_payout": self.DECISION_HIGH_PAYOUT_THRESHOLD,
                    "high_trust": self.DECISION_HIGH_TRUST_THRESHOLD,
                    "low_confidence": self.DECISION_LOW_CONFIDENCE_THRESHOLD,
                    "gray_band_low": self.DECISION_GRAY_BAND_LOW,
                    "gray_band_high": self.DECISION_GRAY_BAND_HIGH,
                },
                "confidence_bands": {
                    "high": self.DECISION_HIGH_CONFIDENCE_THRESHOLD,
                    "moderate": self.DECISION_MODERATE_CONFIDENCE_THRESHOLD,
                },
                "false_review_floor": self.DECISION_FALSE_REVIEW_SCORE_FLOOR,
                "reason_limit": self.DECISION_REASON_LIMIT,
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
        },
        "hyderabad": {
            "base_risk": 0.44,
            "avg_daily_income": 780,
            "zones": ["banjara_hills", "hitech_city", "gachibowli", "kukatpally"]
        },
        "pune": {
            "base_risk": 0.38,
            "avg_daily_income": 760,
            "zones": ["hinjawadi", "kothrud", "viman_nagar", "hadapsar"]
        },
        "kolkata": {
            "base_risk": 0.41,
            "avg_daily_income": 730,
            "zones": ["salt_lake", "new_town", "park_street", "howrah"]
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
