from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """Load YAML config and apply safe defaults."""

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing config file: {p}")

    with p.open("r", encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f) or {}

    # defaults
    cfg.setdefault("mode", "PAPER")
    cfg.setdefault("symbol", "CL")

    cfg.setdefault("engine", {})
    cfg["engine"].setdefault("tick_size", 0.01)
    cfg["engine"].setdefault("loop_hz", 4)
    cfg["engine"].setdefault("log_path", "logs/engine.log")

    cfg.setdefault("risk", {})
    cfg["risk"].setdefault("base_size", 1)
    cfg["risk"].setdefault("max_trades_per_day", 3)
    cfg["risk"].setdefault("max_daily_loss", 500)

    cfg.setdefault("event", {})
    cfg["event"].setdefault("neutral_z", 0.5)
    cfg["event"].setdefault("signif_z", 1.0)
    cfg["event"].setdefault("shock_z", 2.0)

    cfg.setdefault("execution", {})
    cfg["execution"].setdefault("max_spread_ticks", 4)
    cfg["execution"].setdefault("confirm_seconds", 8)
    cfg["execution"].setdefault("hold_max_min", 60)
    cfg["execution"].setdefault("cooldown_seconds", 120)

    return cfg
