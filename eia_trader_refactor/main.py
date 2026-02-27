import time
import json
from pathlib import Path

from engine.config import load_config
from engine.engine import TradingEngine
from engine.bus import SharedBus, Quote


STATE_FILE = Path("ui_state.json")
SNAP_FILE = Path("ui_snapshot.json")


def read_state():
    if not STATE_FILE.exists():
        return {
            "arm": False,
            "kill": False,
            "flatten": False,
            "score": 0.0,
            "event_active": False,
        }
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def main():
    cfg = load_config("config.yaml")
    bus = SharedBus()
    engine = TradingEngine(cfg, bus)

    print("Engine running.")
    print("Stop with Ctrl+C")

    price = 75.0  # prezzo fake iniziale

    try:
        while True:
            # -------------------------
            # 1. Legge controlli UI
            # -------------------------
            state = read_state()
            bus.set_controls(state)

            # -------------------------
            # 2. Simula prezzo (mock)
            # -------------------------
            # piccolo random walk
            price += (0.01 if time.time() % 2 > 1 else -0.01)

            q = Quote(
                ts=time.time(),
                last=price,
                bid=price - 0.01,
                ask=price + 0.01,
                spread_ticks=1,
            )

            bus.set_quote(q)

            # -------------------------
            # 3. Tick engine
            # -------------------------
            engine.tick()

            # -------------------------
            # 4. Scrive snapshot per UI 🔥
            # -------------------------
            snap = bus.get_snapshot()
            if snap:
                SNAP_FILE.write_text(json.dumps(snap.__dict__, indent=2))

            # -------------------------
            # loop speed
            # -------------------------
            time.sleep(0.25)

    except KeyboardInterrupt:
        print("Stopping...")


if __name__ == "__main__":
    main()
