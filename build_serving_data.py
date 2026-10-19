from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb

FEATURES = ["zone_id", "hour_of_day", "dow", "hour_of_week", "month",
            "is_holiday", "is_special", "holiday_season", "lag_168_offday",
            "lag_24", "lag_168", "lag_336", "roll_mean_168"]

df = pd.read_parquet("data/features.parquet", columns=["ts", "n_requests"] + FEATURES)
df = df[df["ts"] >= "2025-10-01"].reset_index(drop=True)

Path("serving").mkdir(exist_ok=True)
df.to_parquet("serving/features_q4_2025.parquet", index=False, compression="zstd")

zones = (pd.read_csv("data/taxi_zone_lookup.csv")
           .rename(columns={"LocationID": "zone_id", "Borough": "borough", "Zone": "zone"}))
zones = zones[zones["zone_id"].isin(df["zone_id"].unique())][["zone_id", "borough", "zone"]]
zones.to_csv("serving/zones.csv", index=False)

# Sanity check: the saved model must reproduce the test WAPE from training
booster = lgb.Booster(model_file="models/lgbm_demand.txt")
X = df[FEATURES].copy()
X["zone_id"] = X["zone_id"].astype("category")
pred = booster.predict(X)
y = df["n_requests"].values
print(f"rows={len(df):,}  zones={len(zones)}")
print(f"file size: {Path('serving/features_q4_2025.parquet').stat().st_size / 1e6:.1f} MB")
print(f"WAPE check: {np.abs(y - pred).sum() / y.sum() * 100:.1f}%  (expected 18.9%)")