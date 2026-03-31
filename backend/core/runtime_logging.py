"""
Runtime logging configuration for local backend monitoring.
Creates plain-text log files for general runtime events and trigger-cycle summaries.
"""

from __future__ import annotations

import logging
from pathlib import Path


class PrefixFilter(logging.Filter):
    def __init__(self, prefixes: tuple[str, ...]):
        super().__init__()
        self.prefixes = prefixes

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name.startswith(prefix) for prefix in self.prefixes)


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_rideshield_logging_configured", False):
        return

    log_dir = Path("logs") / "runtime"
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    app_file_handler = logging.FileHandler(log_dir / "app_runtime.txt", encoding="utf-8")
    app_file_handler.setLevel(logging.INFO)
    app_file_handler.setFormatter(formatter)

    cycle_file_handler = logging.FileHandler(log_dir / "trigger_cycles.txt", encoding="utf-8")
    cycle_file_handler.setLevel(logging.INFO)
    cycle_file_handler.setFormatter(formatter)
    cycle_file_handler.addFilter(PrefixFilter(("rideshield.scheduler", "rideshield.cycles")))

    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(app_file_handler)
    root.addHandler(cycle_file_handler)
    root._rideshield_logging_configured = True
