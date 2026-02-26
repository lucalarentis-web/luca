
import pandas as pd
import os

import logging
logging.basicConfig(level=logging.INFO, format="[V30 PREP] %(message)s")

def trova_colonna_date(df):
    possibili = ["date", "data", "timestamp"]
    cols_norm = {c.lower(): c for c in df.columns}
    for p in possibili:
        if p in cols_norm:
            return cols_norm[p]
    raise Exception("❌ ERRORE: nessuna colonna data trovata nel dataset!")

def main():
    # Base: dataset_v29 già creato dalla pipeline V29
    src_path = "data_v29/dataset_v29.csv"
    out_dir = "data_v30"
    os.makedirs(out_dir, exist_ok=True)
    out_raw = os.path.join(out_dir, "data_v30_raw.csv")
    out_final = os.path.join(out_dir, "dataset_v30.csv")

    if not os.path.exists(src_path):
        logging.error(f"File sorgente mancante: {src_path} → esegui prima V29.")
        return

    logging.info(f"Carico dataset base: {src_path}")
    df = pd.read_csv(src_path)

    # Normalizza nomi colonne
    df.columns = [c.strip().lower() for c in df.columns]

    col_date = trova_colonna_date(df)
    if "close" not in df.columns:
        raise Exception("❌ ERRORE: nel dataset_v29 non esiste la colonna 'close' richiesta per v30.")

    # NO LEAKAGE: futuro rendimento 5 giorni
    # Rendimento tra prezzo di oggi e prezzo tra 5 giorni
    df["future_return_5d"] = (df["close"].shift(-5) / df["close"] - 1.0)

    # Target binario: long se rendimento futuro > 0
    df["target"] = (df["future_return_5d"] > 0).astype(int)

    # Salva grezzo (prima del dropna) per analisi
    df.to_csv(out_raw, index=False)
    logging.info(f"📁 File grezzo salvato → {out_raw}")

    # Pulisci NaN (ffill + bfill)
    df_final = df.copy()
    df_final = df_final.fillna(method="ffill").fillna(method="bfill")

    # Elimina prime / ultime righe dove future_return_5d non è definito
    df_final = df_final.dropna(subset=["future_return_5d", "target"])

    df_final.to_csv(out_final, index=False)
    logging.info(f"✅ Dataset finale creato → {out_final}")
    logging.info(f"📊 Righe finali: {len(df_final)}")

if __name__ == "__main__":
    main()
