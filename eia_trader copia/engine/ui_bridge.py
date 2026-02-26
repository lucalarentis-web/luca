from __future__ import annotations
import json
from pathlib import Path
from dataclasses import asdict

STATE_FILE = Path("ui_state.json")
SNAP_FILE = Path("ui_snapshot.json")


def read_controls(default: dict) -> dict:
    if not STATE_FILE.exists():
        return default
    try:
        d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        # ensure keys exist
        out = dict(default)
        out.update(d)
        return out
    except Exception:
        return default


def write_snapshot(snap) -> None:
    try:
        SNAP_FILE.write_text(json.dumps(asdict(snap), indent=2), encoding="utf-8")
    except Exception:
        pass
