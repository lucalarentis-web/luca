from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from engine.bus import Quote


@dataclass
class FakeMarketFeed:
    """Simple random-walk market generator for paper testing."""

    cfg: dict[str, Any]

    def __post_init__(self) -> None:
        self.tick = float(self.cfg.get("engine", {}).get("tick_size", 0.01))
        self.px = float(self.cfg.get("fake_market", {}).get("start_price", 80.00))
        self.spread_ticks = int(self.cfg.get("fake_market", {}).get("spread_ticks", 1))
        self.vol_ticks = float(self.cfg.get("fake_market", {}).get("vol_ticks", 2.0))

    def next_quote(self) -> Quote:
        # random walk
        step = random.gauss(0.0, self.vol_ticks) * self.tick
        self.px = max(self.tick, self.px + step)

        bid = self.px - (self.spread_ticks * self.tick / 2)
        ask = self.px + (self.spread_ticks * self.tick / 2)
        return Quote(ts=time.time(), last=self.px, bid=bid, ask=ask, spread_ticks=self.spread_ticks)
