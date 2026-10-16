from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb

df = pd.read_parquet("data/features.parquet")
df = df.dropna(subset=["lag_336", "roll_mean_168"])   # دو هفته‌ی اول تاریخچه نداره
df["zone_id"] = df["zone_id"].astype("category")

FEATURES = ["zone_id", "hour_of_day", "dow", "hour_of_week", "month",
            "is_holiday", "is_special", "holiday_season", "lag_168_offday",
            "lag_24", "lag_168", "lag_336", "roll_mean_168"]
TARGET = "n_requests"

train = df[df["ts"] < "2025-09-01"]
valid = df[(df["ts"] >= "2025-09-01") & (df["ts"] < "2025-10-01")]
test  = df[df["ts"] >= "2025-10-01"]
print(f"train={len(train):,}  valid={len(valid):,}  test={len(test):,}")

def report(name, y, pred):
    err = y - pred
    mae = np.mean(np.abs(err))
    rmse = np.sqrt(np.mean(err ** 2))
    wape = np.sum(np.abs(err)) / np.sum(y) * 100
    print(f"{name:22s} MAE={mae:6.2f}  RMSE={rmse:7.2f}  WAPE={wape:5.1f}%")

y_test = test[TARGET].values

# مدل‌های مبنا
report("baseline: yesterday", y_test, test["lag_24"].values)
report("baseline: last week", y_test, test["lag_168"].values)

# مدل اصلی
model = lgb.LGBMRegressor(
    objective="poisson",
    n_estimators=2000,
    learning_rate=0.05,
    num_leaves=63,
    verbose=-1,
)
model.fit(
    train[FEATURES], train[TARGET],
    eval_set=[(valid[FEATURES], valid[TARGET])],
    callbacks=[lgb.early_stopping(100), lgb.log_evaluation(100)],
)

pred = model.predict(test[FEATURES])
report("LightGBM", y_test, pred)

# اهمیت ویژگی‌ها
imp = pd.Series(model.booster_.feature_importance("gain"), index=FEATURES)
print((imp / imp.sum() * 100).sort_values(ascending=False).round(1))

# ذخیره برای روز ۵
Path("models").mkdir(exist_ok=True)
model.booster_.save_model("models/lgbm_demand.txt")


import matplotlib.pyplot as plt

test = test.assign(pred=pred, abs_err=np.abs(test[TARGET] - pred))

# خطا در هر روز
daily = test.groupby(test["ts"].dt.date).agg(err=("abs_err", "sum"), y=(TARGET, "sum"))
daily["wape"] = daily["err"] / daily["y"] * 100
print(daily["wape"].sort_values(ascending=False).head(8).round(1))

# پیش‌بینی در مقابل واقعیت برای میدتاون، هفته‌ی شکرگزاری
zone = test[(test["zone_id"] == 161) &
            (test["ts"] >= "2025-11-23") & (test["ts"] < "2025-11-30")]
plt.figure(figsize=(12, 4))
plt.plot(zone["ts"], zone[TARGET], label="actual")
plt.plot(zone["ts"], zone["pred"], label="predicted")
plt.legend()
plt.title("Midtown Center, Thanksgiving week 2025")
plt.tight_layout()
plt.savefig("figures/thanksgiving_midtown.png")
plt.show()