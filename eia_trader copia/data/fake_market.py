from __future__ import annotations
import time
import math
from engine.bus import Quote


class FakeMarketFeed:
    """Deterministic-ish fake quotes for wiring/testing."""

    def __init__(self, cfg: dict):
        self.tick = float(cfg["engine"]["tick_size"])
        self.t0 = time.time()
        self.last = 75.00

    def next_quote(self) -> Quote:
        t = time.time() - self.t0
        # smooth drift + wiggle
        self.last = 75.0 + 0.25 * math.sin(t / 7.0) + 0.10 * math.sin(t / 1.5)
        bid = round(self.last - 0.01, 2)
        ask = round(self.last + 0.01, 2)
        spread_ticks = int(round((ask - bid) / self.tick))
        return Quote(ts=time.time(), last=round(self.last, 2), bid=bid, ask=ask, spread_ticks=spread_ticks)
