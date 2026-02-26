from __future__ import annotations
import time
from pathlib import Path

from engine.config import load_config
from engine.engine import TradingEngine
from engine.bus import SharedBus
from engine.ui_bridge import read_controls, write_snapshot
from data.fake_market import FakeMarketFeed


def main():
    cfg = load_config("config.yaml")
    Path("logs").mkdir(exist_ok=True)

    bus = SharedBus()
    market = FakeMarketFeed(cfg)
    engine = TradingEngine(cfg, bus)

    default_controls = {
        "arm": False,
        "kill": False,
        "flatten": False,
        "score": 0.0,
        "event_active": False,
    }
    bus.set_controls(default_controls)

    loop_dt = 1.0 / max(1, int(cfg["engine"]["loop_hz"]))

    print("Engine running. Open dashboard in another terminal: streamlit run ui/dashboard.py")
    print("Stop with Ctrl+C")
    try:
        while True:
            # pull UI controls from file (starter bridge)
            bus.set_controls(read_controls(default_controls))

            quote = market.next_quote()
            bus.set_quote(quote)
            engine.tick()

            # write snapshot for dashboard
            snap = bus.get_snapshot()
            if snap is not None:
                write_snapshot(snap)

            time.sleep(loop_dt)
    except KeyboardInterrupt:
        print("\nStopping...")


if __name__ == "__main__":
    main()
