from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from engine.bus import Quote


@dataclass
class Position:
    side: str = "FLAT"          # LONG/SHORT/FLAT
    qty: int = 0
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    best_price: float = 0.0     # max for long, min for short

    def is_flat(self) -> bool:
        return self.side == "FLAT" or self.qty == 0


class PaperBroker:
    """Very simple paper fills: buys at ask, sells at bid."""

    def __init__(self, tick_size: float):
        self.tick_size = tick_size
        self.pos = Position()
        self.realized_pnl = 0.0

    def mark_unrealized(self, q: Quote) -> float:
        if self.pos.is_flat():
            return 0.0
        if self.pos.side == "LONG":
            return (q.bid - self.pos.entry_price) * self.pos.qty
        if self.pos.side == "SHORT":
            return (self.pos.entry_price - q.ask) * self.pos.qty
        return 0.0

    def enter(self, side: str, qty: int, q: Quote) -> float:
        if not self.pos.is_flat():
            raise RuntimeError("Already in position")
        fill = q.ask if side == "LONG" else q.bid
        self.pos = Position(side=side, qty=qty, entry_price=fill, entry_time=datetime.now(), best_price=fill)
        return fill

    def exit(self, q: Quote) -> float:
        if self.pos.is_flat():
            return 0.0
        fill = q.bid if self.pos.side == "LONG" else q.ask
        # realize
        if self.pos.side == "LONG":
            pnl = (fill - self.pos.entry_price) * self.pos.qty
        else:
            pnl = (self.pos.entry_price - fill) * self.pos.qty
        self.realized_pnl += pnl
        self.pos = Position()
        return pnl

    def flatten(self, q: Quote) -> float:
        return self.exit(q)
