"""
Tests for Sprint 2 trigger engine helpers.
"""

from backend.core.trigger_engine import trigger_engine
from backend.providers.registry import provider_registry


class TestThresholdEvaluation:
    def test_rain_above_threshold_fires(self):
        signals = {"rain": 30.0, "heat": 30, "aqi": 100, "traffic": 0.3, "platform_outage": 0.1, "social": 0.0}
        assert "rain" in trigger_engine.evaluate_thresholds(signals)

    def test_multiple_triggers_fire_together(self):
        signals = {"rain": 30.0, "heat": 46.0, "aqi": 350, "traffic": 0.8, "platform_outage": 0.7, "social": 0.0}
        assert set(trigger_engine.evaluate_thresholds(signals)) == {"rain", "heat", "aqi", "traffic", "platform_outage"}

    def test_no_triggers_fire_normal_conditions(self):
        signals = {"rain": 5.0, "heat": 30, "aqi": 100, "traffic": 0.3, "platform_outage": 0.1, "social": 0.0}
        assert trigger_engine.evaluate_thresholds(signals) == []


class TestDisruptionScore:
    def test_compound_disaster_gives_high_score(self):
        signals = {"rain": 60.0, "heat": 46, "aqi": 400, "traffic": 0.95, "platform_outage": 0.9, "social": 0.8}
        assert trigger_engine.calculate_disruption_score(signals) > 0.7

    def test_score_between_zero_and_one(self):
        signals = {"rain": 100.0, "heat": 50, "aqi": 500, "traffic": 1.0, "platform_outage": 1.0, "social": 1.0}
        score = trigger_engine.calculate_disruption_score(signals)
        assert 0.0 <= score <= 1.0


class TestSignalModes:
    def test_demo_mode_forces_mock_providers(self):
        assert provider_registry.configured_source("weather", source_mode="demo") == "mock"
        assert provider_registry.configured_source("aqi", source_mode="demo") == "mock"
        assert provider_registry.configured_source("traffic", source_mode="demo") == "mock"
        assert provider_registry.configured_source("platform", source_mode="demo") == "mock"
