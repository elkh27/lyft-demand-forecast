import numpy as np
import pandas as pd
import lightgbm as lgb

df = pd.read_parquet("data/features.parquet")
df = df.dropna(subset=["lag_672", "roll_mean_168"])
df["zone_id"] = df["zone_id"].astype("category")

BASE = ["zone_id", "hour_of_day", "dow", "hour_of_week", "month",
        "is_holiday", "is_special", "holiday_season", "lag_168_offday",
        "lag_24", "lag_168", "lag_336", "roll_mean_168"]
MULTIWEEK = ["lag_504", "lag_672", "same_hour_mean_4w"]
WEATHER = ["temperature_2m", "precipitation", "snowfall"]

experiments = {
    "base":       BASE,
    "+multiweek": BASE + MULTIWEEK,
    "+weather":   BASE + WEATHER,
    "+both":      BASE + MULTIWEEK + WEATHER,
}

train = df[df["ts"] < "2025-09-01"]
valid = df[(df["ts"] >= "2025-09-01") & (df["ts"] < "2025-10-01")]
y = valid["n_requests"].values
rainy = (valid["precipitation"] > 0.5).values
print(f"rainy hours in validation: {rainy.sum() // 262}")

def wape(y, p):
    return np.abs(y - p).sum() / y.sum() * 100

for name, feats in experiments.items():
    model = lgb.LGBMRegressor(objective="poisson", n_estimators=1000,
                              learning_rate=0.1, num_leaves=63, verbose=-1)
    model.fit(train[feats], train["n_requests"],
              eval_set=[(valid[feats], valid["n_requests"])],
              callbacks=[lgb.early_stopping(50, verbose=False)])
    pred = model.predict(valid[feats])
    mae = np.abs(y - pred).mean()
    print(f"{name:12s} MAE={mae:5.2f}  WAPE={wape(y, pred):5.2f}%  "
          f"WAPE rainy={wape(y[rainy], pred[rainy]):5.2f}%")