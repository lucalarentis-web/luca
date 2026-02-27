from __future__ import annotations

from typing import Any

from state.store import JsonStateStore


_store = JsonStateStore()


def read_controls(default: dict[str, Any]) -> dict[str, Any]:
    return _store.read_controls(default)


def write_snapshot(snap: Any) -> None:
    _store.write_snapshot(snap)
