"""Trigger scheduler budget guard tests."""

from backend.core.trigger_scheduler import TriggerScheduler


def test_scheduler_clamps_interval_for_real_traffic_budget(monkeypatch):
    monkeypatch.setattr("backend.core.trigger_scheduler.settings.TRIGGER_CHECK_INTERVAL_SECONDS", 60)
    monkeypatch.setattr("backend.core.trigger_scheduler.settings.TRAFFIC_SOURCE", "real")
    monkeypatch.setattr("backend.core.trigger_scheduler.settings.TOMTOM_API_KEY", "test-key")
    monkeypatch.setattr("backend.core.trigger_scheduler.settings.TRAFFIC_DAILY_REQUEST_BUDGET", 2400)

    scheduler = TriggerScheduler()

    effective = scheduler._budgeted_interval_seconds(zone_count=31)

    assert effective >= 1116


def test_scheduler_keeps_configured_interval_when_traffic_is_not_live(monkeypatch):
    monkeypatch.setattr("backend.core.trigger_scheduler.settings.TRIGGER_CHECK_INTERVAL_SECONDS", 300)
    monkeypatch.setattr("backend.core.trigger_scheduler.settings.TRAFFIC_SOURCE", "mock")
    monkeypatch.setattr("backend.core.trigger_scheduler.settings.TOMTOM_API_KEY", None)

    scheduler = TriggerScheduler()

    assert scheduler._budgeted_interval_seconds(zone_count=31) == 300
