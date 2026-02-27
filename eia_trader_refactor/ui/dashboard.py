from __future__ import annotations
import time
import json
from pathlib import Path

import streamlit as st

STATE_FILE = Path("ui_state.json")


def read_state() -> dict:
    if not STATE_FILE.exists():
        return {"arm": False, "kill": False, "flatten": False, "score": 0.0, "event_active": False}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"arm": False, "kill": False, "flatten": False, "score": 0.0, "event_active": False}


def write_state(d: dict):
    STATE_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def read_snapshot() -> dict | None:
    p = Path("ui_snapshot.json")
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


st.set_page_config(page_title="EIA Reaction Trader", layout="wide")
st.title("EIA Reaction Trader — Dashboard (starter)")

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("Controls")
    s = read_state()

    arm = st.toggle("ARM", value=bool(s.get("arm", False)))
    event_active = st.toggle("EVENT ACTIVE", value=bool(s.get("event_active", False)))
    score = st.number_input("SCORE (pos=LONG, neg=SHORT)", value=float(s.get("score", 0.0)), step=0.1, format="%.2f")

    c1, c2, c3 = st.columns(3)
    flatten = c1.button("FLATTEN", type="secondary")
    kill = c2.button("KILL SWITCH", type="primary")
    reset_kill = c3.button("Reset Kill")

    if flatten:
        s["flatten"] = True
    else:
        s["flatten"] = bool(s.get("flatten", False))

    if kill:
        s["kill"] = True
    if reset_kill:
        s["kill"] = False

    s["arm"] = arm
    s["event_active"] = event_active
    s["score"] = float(score)

    write_state(s)

    st.caption("Starter: shared state via ui_state.json. Next: local API/websockets.")

with right:
    st.subheader("Live Snapshot")
    snap = read_snapshot()
    if snap is None:
        st.info("No snapshot yet. Start the engine: `python main.py`")
    else:
        cols = st.columns(5)
        cols[0].metric("State", snap.get("state", ""))
        cols[1].metric("Label", snap.get("label", ""))
        cols[2].metric("Score", f'{float(snap.get("score", 0.0)):+.2f}')
        cols[3].metric("Trades today", snap.get("trades_today", 0))
        cols[4].metric("Reason", snap.get("reject_reason", ""))

        st.divider()
        cA, cB, cC, cD = st.columns(4)
        cA.metric("Position", f'{snap.get("position_side","")} x{snap.get("position_qty",0)}')
        cB.metric("Entry", f'{float(snap.get("entry_price",0.0)):.2f}')
        cC.metric("Unreal. PnL", f'{float(snap.get("unrealized_pnl",0.0)):.2f}')
        cD.metric("Realized PnL", f'{float(snap.get("realized_pnl",0.0)):.2f}')

        st.divider()
        st.json(snap)

st.sidebar.subheader("Auto-refresh")
auto = st.sidebar.toggle("Refresh every 0.5s", value=True)
if auto:
    time.sleep(0.5)
    st.rerun()
