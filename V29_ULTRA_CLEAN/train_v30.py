
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
import joblib
import os
import logging

logging.basicConfig(level=logging.INFO, format="[V30 TRAIN] %(message)s")

def trova_colonna_date(df):
    possibili = ["date", "data", "timestamp"]
    cols_norm = {c.lower(): c for c in df.columns}
    for p in possibili:
        if p in cols_norm:
            return cols_norm[p]
    raise Exception("❌ ERRORE: nessuna colonna data trovata nei dati!")

def main():
    data_path = "data_v30/dataset_v30.csv"
    if not os.path.exists(data_path):
        logging.error("❌ dataset_v30 mancante → esegui prima prepare_dataset_v30.py")
        return

    df = pd.read_csv(data_path)
    df.columns = [c.strip().lower() for c in df.columns]

    col_date = trova_colonna_date(df)

    if "target" not in df.columns:
        raise Exception("❌ ERRORE: nel dataset_v30 non esiste la colonna 'target'!")

    # Features = tutte tranne data, target e future_return_5d
    drop_cols = [col_date, "target", "future_return_5d", "target_return_1d"]
    features = [c for c in df.columns if c not in drop_cols and not c.startswith("unnamed")]

    X = df[features].copy()
    y = df["target"].astype(int)

    # Gestione NaN
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(method="ffill").fillna(method="bfill")

    # Train/Test split temporale (no shuffle)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, shuffle=False
    )

    logging.info(f"✅ Train size: {len(X_train)}  |  Test size: {len(X_test)}")

    models = {}

    # Random Forest
    logging.info("🌲 Alleno RandomForest...")
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    models["rf"] = rf

    # Gradient Boosting (come XGB light)
    logging.info("🔥 Alleno GradientBoost (XGB-light)...")
    xgb = GradientBoostingClassifier(random_state=42)
    xgb.fit(X_train, y_train)
    models["xgb"] = xgb

    # Logistic Regression
    logging.info("📈 Alleno Logistic Regression...")
    lr = LogisticRegression(max_iter=2000)
    lr.fit(X_train, y_train)
    models["lr"] = lr

    # Valutazione ensemble
    def proba(m):
        try:
            return m.predict_proba(X_test)[:, 1]
        except Exception:
            return m.predict(X_test)

    preds_rf = proba(rf)
    preds_xgb = proba(xgb)
    preds_lr = proba(lr)

    ensemble = (preds_rf + preds_xgb + preds_lr) / 3.0
    y_pred_class = (ensemble > 0.5).astype(int)

    acc = accuracy_score(y_test, y_pred_class)
    try:
        auc = roc_auc_score(y_test, ensemble)
    except Exception:
        auc = float("nan")

    logging.info(f"✅ Accuracy (test): {acc:.3f}")
    logging.info(f"✅ AUC (test): {auc:.3f}")

    # Salva modelli
    out_dir = "models_v30"
    os.makedirs(out_dir, exist_ok=True)
    joblib.dump(rf, os.path.join(out_dir, "model_rf.pkl"))
    joblib.dump(xgb, os.path.join(out_dir, "model_xgb.pkl"))
    joblib.dump(lr, os.path.join(out_dir, "model_lr.pkl"))
    logging.info(f"💾 Modelli salvati in {out_dir}/")

if __name__ == "__main__":
    main()
