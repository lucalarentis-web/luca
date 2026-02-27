from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


class JsonStateStore:
    """Small helper to persist UI controls + engine snapshot to json files."""

    def __init__(self, state_file: str | Path = "state/ui_state.json", snapshot_file: str | Path = "state/ui_snapshot.json"):
        self.state_file = Path(state_file)
        self.snapshot_file = Path(snapshot_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_file.parent.mkdir(parents=True, exist_ok=True)

    def read_controls(self, defaults: dict[str, Any]) -> dict[str, Any]:
        if not self.state_file.exists():
            return dict(defaults)
        try:
            d = json.loads(self.state_file.read_text(encoding="utf-8"))
            out = dict(defaults)
            if isinstance(d, dict):
                out.update(d)
            return out
        except Exception:
            return dict(defaults)

    def write_snapshot(self, snap: Any) -> None:
        try:
            payload = asdict(snap) if hasattr(snap, "__dataclass_fields__") else snap
            self.snapshot_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            # keep engine loop resilient
            pass
