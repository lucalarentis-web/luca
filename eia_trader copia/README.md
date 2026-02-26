# EIA Reaction Trader (starter)
Event-driven intraday engine (PAPER by default) with a small web dashboard (Streamlit).
No prediction: trade the *surprise/score* + market confirmation.

## Quickstart
1) Create venv + install deps
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

2) Run the engine (paper + fake market)
```bash
python main.py
```

3) Run the dashboard (separate terminal)
```bash
streamlit run ui/dashboard.py
```

## What you can do now
- Arm/disarm engine from the dashboard
- Trigger an "event" by setting SCORE (positive=LONG, negative=SHORT)
- Engine will wait for confirmation (price impulse) and then enter
- Holds up to HOLD_MAX_MIN minutes, supports manual FLATTEN, kill switch, cooldown

## Next upgrades (we’ll do after this boots)
- Replace fake market with broker/datafeed
- Replace manual SCORE with real EIA parser + consensus
- Add real execution (IBKR/Tradovate) + brackets + robust slippage model
