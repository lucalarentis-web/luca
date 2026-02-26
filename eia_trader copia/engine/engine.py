from __future__ import annotations
from datetime import datetime, timedelta
import time
from collections import deque
import statistics

from engine.bus import SharedBus, EngineSnapshot
from engine.execution import PaperBroker
from engine.logger import Logger
from engine.strategy import label_from_score


class TradingEngine:
    def __init__(self, cfg: dict, bus: SharedBus):
        self.cfg = cfg
        self.bus = bus
        self.log = Logger(cfg["engine"]["log_path"])

        self.state = "IDLE"
        self.cooldown_until: datetime | None = None
        self.trades_today = 0
        self.day = datetime.now().date()

        self.broker = PaperBroker(tick_size=float(cfg["engine"]["tick_size"]))

        # Event ref
        self._event_ref_price: float | None = None
        self._event_ref_time: datetime | None = None
        self._event_peak_ticks: int = 0
        self._event_trough_ticks: int = 0

        # Initial range
        self._range_high: float | None = None
        self._range_low: float | None = None
        self._range_done: bool = False

        self._last_prices = deque(maxlen=60)

        # Debug
        self._reject_reason: str = "IDLE"

        self.log.info("Engine initialized")

    # ---------------- helpers ----------------
    def _set_reason(self, s: str):
        self._reject_reason = s

    def _roll_day_if_needed(self):
        today = datetime.now().date()
        if today != self.day:
            self.day = today
            self.trades_today = 0
            self.log.info("New day: trades counter reset")

    def _in_cooldown(self) -> bool:
        return self.cooldown_until is not None and datetime.now() < self.cooldown_until

    def _set_cooldown(self):
        sec = int(self.cfg["execution"].get("cooldown_seconds", 120))
        self.cooldown_until = datetime.now() + timedelta(seconds=sec)

    def _reset_event_ref(self):
        self._event_ref_price = None
        self._event_ref_time = None
        self._event_peak_ticks = 0
        self._event_trough_ticks = 0
        self._range_high = None
        self._range_low = None
        self._range_done = False

    def _persistence_ok(self, want_side: str, n: int) -> bool:
        if n <= 1:
            return True
        if len(self._last_prices) < n:
            return False
        arr = list(self._last_prices)[-n:]
        if want_side == "LONG":
            return all(arr[i] > arr[i - 1] for i in range(1, n))
        return all(arr[i] < arr[i - 1] for i in range(1, n))

    def _vol_ticks(self, tick_size: float) -> float:
        if len(self._last_prices) < 12:
            return 0.0
        px = list(self._last_prices)[-30:]
        rets = [px[i] - px[i - 1] for i in range(1, len(px))]
        try:
            st = statistics.pstdev(rets)
        except Exception:
            st = 0.0
        return float(st / tick_size) if tick_size > 0 else 0.0

    # ---------------- main loop ----------------
    def tick(self):
        self._roll_day_if_needed()

        q = self.bus.get_quote()
        ctl = self.bus.get_controls()
        if q is None:
            return

        self._last_prices.append(float(q.last))

        arm = bool(ctl.get("arm", False))
        kill = bool(ctl.get("kill", False))
        flatten = bool(ctl.get("flatten", False))
        score = float(ctl.get("score", 0.0))
        event_active = bool(ctl.get("event_active", False))

        neutral_z = float(self.cfg["event"]["neutral_z"])
        signif_z = float(self.cfg["event"]["signif_z"])
        shock_z = float(self.cfg["event"]["shock_z"])
        label = label_from_score(score, neutral_z, signif_z, shock_z)

        # KILL
        if kill:
            if not self.broker.pos.is_flat():
                pnl = self.broker.flatten(q)
                self.log.warn(f"KILL: flattened. realized_pnl_delta={pnl:.2f}")
            self.state = "HALT"
            self._set_reason("KILL -> HALT")
            self._publish_snapshot(q, label, score, event_active, arm, kill, flatten)
            return

        # FLATTEN
        if flatten and not self.broker.pos.is_flat():
            pnl = self.broker.flatten(q)
            self.log.warn(f"FLATTEN: realized_pnl_delta={pnl:.2f}")
            self._set_cooldown()
            self.bus.set_controls({"flatten": False})
            self._set_reason("Manual FLATTEN")

        # daily loss
        max_daily_loss = float(self.cfg["risk"]["max_daily_loss"])
        if self.broker.realized_pnl <= -max_daily_loss:
            if not self.broker.pos.is_flat():
                pnl = self.broker.flatten(q)
                self.log.warn(f"MAX_DAILY_LOSS: flattened. delta={pnl:.2f}")
            self.state = "HALT"
            self._set_reason("Max daily loss -> HALT")
            self._publish_snapshot(q, label, score, event_active, arm, kill, False)
            return

        # ARM gate
        if not arm:
            self.state = "IDLE"
            self._reset_event_ref()
            self._set_reason("ARM is OFF")
            self._publish_snapshot(q, label, score, event_active, arm, kill, False)
            return

        # cooldown
        if self._in_cooldown():
            self.state = "COOLDOWN"
            self._set_reason("Cooldown active")
            self._publish_snapshot(q, label, score, event_active, arm, kill, False)
            return

        # spread gate
        max_spread = int(self.cfg["execution"].get("max_spread_ticks", 4))
        if q.spread_ticks > max_spread and self.broker.pos.is_flat():
            self.state = "ARMED"
            self._set_reason(f"Spread too wide ({q.spread_ticks}t > {max_spread}t)")
            self._publish_snapshot(q, label, score, event_active, arm, kill, False)
            return

        tick_size = float(self.cfg["engine"]["tick_size"])

        # =========================
        # FLAT -> ENTRY
        # =========================
        if self.broker.pos.is_flat():
            self.state = "ARMED"

            if not event_active:
                self._reset_event_ref()
                self._set_reason("Waiting EVENT_ACTIVE")
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            if self._event_ref_price is None:
                self._event_ref_price = float(q.last)
                self._event_ref_time = datetime.now()
                self._event_peak_ticks = 0
                self._event_trough_ticks = 0
                self._range_high = float(q.last)
                self._range_low = float(q.last)
                self._range_done = False
                self._set_reason("Event started: ref set, building range")
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            # max trades/day
            if self.trades_today >= int(self.cfg["risk"]["max_trades_per_day"]):
                self.state = "HALT"
                self._set_reason("Max trades/day -> HALT")
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            # only signif/shock
            if label == "NEUTRAL":
                self._set_reason("Label NEUTRAL -> no trade")
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            # params
            confirm_sec = int(self.cfg["execution"].get("confirm_seconds", 10))
            impulse_shock = int(self.cfg["execution"].get("impulse_ticks_shock", 8))
            impulse_signif = int(self.cfg["execution"].get("impulse_ticks_signif", 10))
            velocity_thr = float(self.cfg["execution"].get("velocity_ticks_per_sec", 1.5))

            range_build_sec = float(self.cfg["execution"].get("range_build_sec", 3))
            range_break_ticks = int(self.cfg["execution"].get("range_break_ticks", 2))

            retrace_ticks = int(self.cfg["execution"].get("retrace_ticks", 3))
            persistence_n = int(self.cfg["execution"].get("persistence_n", 3))

            elapsed = (datetime.now() - (self._event_ref_time or datetime.now())).total_seconds()

            if elapsed > confirm_sec:
                self._set_reason(f"Expired confirm window ({elapsed:.1f}s > {confirm_sec}s) -> cooldown")
                self._set_cooldown()
                self._reset_event_ref()
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            # build initial range
            if not self._range_done:
                self._range_high = max(float(self._range_high), float(q.last)) if self._range_high is not None else float(q.last)
                self._range_low = min(float(self._range_low), float(q.last)) if self._range_low is not None else float(q.last)

                if elapsed >= range_build_sec:
                    self._range_done = True
                    self._set_reason("Range built -> waiting breakout")
                else:
                    self._set_reason(f"Building range ({elapsed:.1f}/{range_build_sec:.1f}s)")
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            want_side = "LONG" if score > 0 else "SHORT"
            impulse_ticks = impulse_shock if label == "SHOCK" else impulse_signif

            move = float(q.last) - float(self._event_ref_price)
            move_ticks = int(round(move / tick_size))

            self._event_peak_ticks = max(self._event_peak_ticks, move_ticks)
            self._event_trough_ticks = min(self._event_trough_ticks, move_ticks)

            velocity = abs(move_ticks) / max(elapsed, 0.001)

            # (1) impulse
            move_ok = (want_side == "LONG" and move_ticks >= impulse_ticks) or \
                      (want_side == "SHORT" and move_ticks <= -impulse_ticks)
            if not move_ok:
                self._set_reason(f"Reject: impulse {move_ticks}t need {impulse_ticks}t")
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            # (2) velocity
            if velocity < velocity_thr:
                self._set_reason(f"Reject: velocity {velocity:.2f}t/s < {velocity_thr:.2f}")
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            # (3) persistence
            if not self._persistence_ok(want_side, persistence_n):
                self._set_reason(f"Reject: persistence < {persistence_n} ticks")
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            # (4) breakout
            rb = range_break_ticks * tick_size
            if want_side == "LONG":
                need = (float(self._range_high) + rb) if self._range_high is not None else float(q.last)
                if float(q.last) < need:
                    self._set_reason(f"Reject: no breakout LONG (last {q.last:.2f} < {need:.2f})")
                    self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                    return
            else:
                need = (float(self._range_low) - rb) if self._range_low is not None else float(q.last)
                if float(q.last) > need:
                    self._set_reason(f"Reject: no breakout SHORT (last {q.last:.2f} > {need:.2f})")
                    self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                    return

            # (5) anti-fake retrace
            if want_side == "LONG":
                retr = self._event_peak_ticks - move_ticks
            else:
                retr = move_ticks - self._event_trough_ticks

            if retr > retrace_ticks:
                self._set_reason(f"Reject: retrace {retr}t > {retrace_ticks}t -> cooldown")
                self._set_cooldown()
                self._reset_event_ref()
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

            # ENTER
            qty = max(1, int(self.cfg["risk"]["base_size"]))
            fill = self.broker.enter(want_side, qty, q)
            self.trades_today += 1
            self.state = "IN_TRADE"
            self._set_reason(f"ENTER {want_side} @ {fill:.2f}")
            self.log.info(self._reject_reason)

            self._reset_event_ref()
            self._publish_snapshot(q, label, score, event_active, arm, kill, False)
            return

        # =========================
        # IN_TRADE management (same as before)
        # =========================
        self.state = "IN_TRADE"
        pos = self.broker.pos
        now = datetime.now()

        unreal = self.broker.mark_unrealized(q)
        time_in_trade = (now - pos.entry_time).total_seconds() if pos.entry_time else 0.0

        fail_fast_sec = float(self.cfg["execution"].get("fail_fast_sec", 15))
        no_follow_sec = float(self.cfg["execution"].get("no_follow_sec", 25))
        no_follow_min_pnl = float(self.cfg["execution"].get("no_follow_min_pnl", 0.05))

        trail_min_ticks = float(self.cfg["execution"].get("trail_min_ticks", 10))
        trail_vol_mult = float(self.cfg["execution"].get("trail_vol_mult", 1.5))
        breakeven_after_ticks = float(self.cfg["execution"].get("breakeven_after_ticks", 8))

        tighten_after_sec = float(self.cfg["execution"].get("tighten_after_sec", 120))
        trail_min_ticks_tight = float(self.cfg["execution"].get("trail_min_ticks_tight", 6))

        hold_max_min = float(self.cfg["execution"].get("hold_max_min", 60))

        # update best price
        if pos.side == "LONG":
            pos.best_price = max(pos.best_price, q.bid)
        elif pos.side == "SHORT":
            pos.best_price = min(pos.best_price, q.ask)

        # fail fast
        if time_in_trade >= fail_fast_sec and unreal < 0:
            self._set_reason("EXIT: fail-fast")
            pnl = self.broker.exit(q)
            self.log.info(f"{self._reject_reason} pnl_delta={pnl:.2f}")
            self._set_cooldown()
            self._publish_snapshot(q, label, score, event_active, arm, kill, False)
            return

        # no follow through
        if time_in_trade >= no_follow_sec and unreal < no_follow_min_pnl:
            self._set_reason("EXIT: no follow-through")
            pnl = self.broker.exit(q)
            self.log.info(f"{self._reject_reason} pnl_delta={pnl:.2f}")
            self._set_cooldown()
            self._publish_snapshot(q, label, score, event_active, arm, kill, False)
            return

        # dynamic trailing
        vol_ticks = self._vol_ticks(tick_size)
        dyn_trail_ticks = max(trail_min_ticks, trail_vol_mult * vol_ticks)
        if time_in_trade >= tighten_after_sec:
            dyn_trail_ticks = max(trail_min_ticks_tight, dyn_trail_ticks * 0.8)
        trail_price = dyn_trail_ticks * tick_size

        # breakeven
        be_ok = False
        be_price = pos.entry_price

        if pos.side == "LONG":
            if (pos.best_price - pos.entry_price) >= (breakeven_after_ticks * tick_size):
                be_ok = True
            if q.bid < pos.best_price - trail_price:
                self._set_reason("EXIT: trailing long")
                pnl = self.broker.exit(q)
                self.log.info(f"{self._reject_reason} pnl_delta={pnl:.2f}")
                self._set_cooldown()
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return
            if be_ok and q.bid <= be_price:
                self._set_reason("EXIT: breakeven long")
                pnl = self.broker.exit(q)
                self.log.info(f"{self._reject_reason} pnl_delta={pnl:.2f}")
                self._set_cooldown()
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

        elif pos.side == "SHORT":
            if (pos.entry_price - pos.best_price) >= (breakeven_after_ticks * tick_size):
                be_ok = True
            if q.ask > pos.best_price + trail_price:
                self._set_reason("EXIT: trailing short")
                pnl = self.broker.exit(q)
                self.log.info(f"{self._reject_reason} pnl_delta={pnl:.2f}")
                self._set_cooldown()
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return
            if be_ok and q.ask >= be_price:
                self._set_reason("EXIT: breakeven short")
                pnl = self.broker.exit(q)
                self.log.info(f"{self._reject_reason} pnl_delta={pnl:.2f}")
                self._set_cooldown()
                self._publish_snapshot(q, label, score, event_active, arm, kill, False)
                return

        # time exit
        if time_in_trade >= hold_max_min * 60:
            self._set_reason("EXIT: time")
            pnl = self.broker.exit(q)
            self.log.info(f"{self._reject_reason} pnl_delta={pnl:.2f}")
            self._set_cooldown()
            self._publish_snapshot(q, label, score, event_active, arm, kill, False)
            return

        self._set_reason("IN_TRADE managing")
        self._publish_snapshot(q, label, score, event_active, arm, kill, False)

    # ---------------- snapshot ----------------
    def _publish_snapshot(self, q, label, score, event_active, arm, kill, flatten):
        unreal = self.broker.mark_unrealized(q)
        snap = EngineSnapshot(
            ts=time.time(),
            state=self.state,
            position_side=self.broker.pos.side,
            position_qty=self.broker.pos.qty,
            entry_price=self.broker.pos.entry_price,
            unrealized_pnl=unreal,
            realized_pnl=self.broker.realized_pnl,
            trades_today=self.trades_today,
            label=label,
            score=score,
            event_active=event_active,
            arm=arm,
            kill=kill,
            flatten=flatten,
            reject_reason=self._reject_reason,
        )
        self.bus.set_snapshot(snap)
