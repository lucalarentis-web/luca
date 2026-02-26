from __future__ import annotations
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class Quote:
    ts: float
    last: float
    bid: float
    ask: float
    spread_ticks: int


@dataclass
class EngineSnapshot:
    ts: float
    state: str
    position_side: str
    position_qty: int
    entry_price: float
    unrealized_pnl: float
    realized_pnl: float
    trades_today: int
    label: str
    score: float
    event_active: bool
    arm: bool
    kill: bool
    flatten: bool
    reject_reason: str = ""


class SharedBus:
    """Tiny in-memory shared state between engine and UI."""

    def __init__(self):
        self._lock = Lock()
        self._quote: Quote | None = None
        self._controls: dict[str, Any] = {}
        self._snapshot: EngineSnapshot | None = None

    def set_quote(self, quote: Quote):
        with self._lock:
            self._quote = quote

    def get_quote(self) -> Quote | None:
        with self._lock:
            return self._quote

    def set_controls(self, controls: dict[str, Any]):
        with self._lock:
            self._controls.update(controls)

    def get_controls(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._controls)

    def set_snapshot(self, snap: EngineSnapshot):
        with self._lock:
            self._snapshot = snap

    def get_snapshot(self) -> EngineSnapshot | None:
        with self._lock:
            return self._snapshot
