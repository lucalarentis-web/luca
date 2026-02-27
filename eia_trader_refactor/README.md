# EIA Trader (refactor)

Questo è un refactor strutturale del progetto: stessi concetti, ma con cartelle e import puliti.

## Struttura

- `main.py` entry-point
- `engine/` logica core (bus, engine, execution, strategy, config)
- `data/` feed di mercato (fake)
- `state/` persistenza json (ui_state / ui_snapshot)
- `logs/` log file

## Avvio

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

I controlli UI (per ora) sono in `state/ui_state.json`.
Lo snapshot motore è in `state/ui_snapshot.json`.
