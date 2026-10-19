import duckdb
import holidays
import pandas as pd

con = duckdb.connect()

df = con.sql("""
    SELECT ts, zone_id, n_requests,
           hour(ts) AS hour_of_day,
           isodow(ts) AS dow,
           (isodow(ts) - 1) * 24 + hour(ts) AS hour_of_week,
           month(ts) AS month,
           LAG(n_requests, 24)  OVER w AS lag_24,
           LAG(n_requests, 168) OVER w AS lag_168,
           LAG(n_requests, 336) OVER w AS lag_336,
           LAG(n_requests, 504) OVER w AS lag_504,
           LAG(n_requests, 672) OVER w AS lag_672,
           AVG(n_requests) OVER (
               PARTITION BY zone_id ORDER BY ts
               ROWS BETWEEN 191 PRECEDING AND 24 PRECEDING
           ) AS roll_mean_168
    FROM (
        SELECT hour AS ts, zone_id, n_requests
        FROM 'data/zone_hour_panel.parquet'
    )
    WINDOW w AS (PARTITION BY zone_id ORDER BY ts)
    ORDER BY zone_id, ts
""").df()

# Mean of the same hour over the previous 4 weeks
df["same_hour_mean_4w"] = df[["lag_168", "lag_336", "lag_504", "lag_672"]].mean(axis=1)

# Holidays and special days
us_holidays = pd.to_datetime(list(holidays.US(years=[2024, 2025]).keys()))
hol = holidays.US(years=[2024, 2025])
thanksgiving = [pd.Timestamp(d) for d, name in hol.items() if "Thanksgiving" in name]

special = []
for y in (2024, 2025):
    special += [f"{y}-10-31", f"{y}-12-24", f"{y}-12-26", f"{y}-12-31"]
special = pd.to_datetime(special).union(
    pd.DatetimeIndex([d + pd.Timedelta(days=1) for d in thanksgiving])
)

day = df["ts"].dt.normalize()
df["is_holiday"] = day.isin(us_holidays).astype(int)
df["is_special"] = day.isin(special).astype(int)
m, d = df["ts"].dt.month, df["ts"].dt.day
df["holiday_season"] = (((m == 12) & (d >= 20)) | ((m == 1) & (d <= 2))).astype(int)
off_days = us_holidays.union(special)
df["lag_168_offday"] = (day - pd.Timedelta(days=7)).isin(off_days).astype(int)

# Weather
weather = pd.read_parquet("data/weather.parquet")
df = df.merge(weather, on="ts", how="left")

df.to_parquet("data/features.parquet", index=False)
print(df.shape)
print(df[["temperature_2m", "precipitation", "snowfall"]].isna().sum())