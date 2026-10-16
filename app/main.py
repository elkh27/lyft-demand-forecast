from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Annotated

import lightgbm as lgb
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
import lightgbm as lgb
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse

ROOT = Path(__file__).resolve().parent.parent
FEATURES = ["zone_id", "hour_of_day", "dow", "hour_of_week", "month",
            "is_holiday", "is_special", "holiday_season", "lag_168_offday",
            "lag_24", "lag_168", "lag_336", "roll_mean_168"]

booster = lgb.Booster(model_file=str(ROOT / "models" / "lgbm_demand.txt"))
data = pd.read_parquet(ROOT / "serving" / "features_q4_2025.parquet")
zones = pd.read_csv(ROOT / "serving" / "zones.csv")
ZONE_IDS = set(zones["zone_id"])
TS_MIN, TS_MAX = data["ts"].min(), data["ts"].max()

app = FastAPI(
    title="NYC Lyft Demand Forecast API",
    version="1.0",
    description="""
Day-ahead hourly forecasts of Lyft ride requests for 262 NYC taxi zones,
with the actual demand for comparison. Available period: **Oct 1 – Dec 31, 2025**.

**How to use**
1. Find a zone: call `/zones` (filter by borough or search by name) and note its `zone_id`.
2. Forecast one hour: `/predict` with a `zone_id` and a time like `2025-11-14T18:00`.
3. Forecast a whole day: `/predict/day` with a `zone_id` and a date like `2025-11-14`.
4. Forecast the whole city for one hour: `/predict/city`.

Times are New York local time. Minutes are rounded down to the hour.

Popular zones: 161 Midtown Center, 237 Upper East Side South, 132 JFK Airport,
138 LaGuardia Airport, 79 East Village.
""",
)


class Borough(str, Enum):
    manhattan = "Manhattan"
    brooklyn = "Brooklyn"
    queens = "Queens"
    bronx = "Bronx"
    staten_island = "Staten Island"


ZoneId = Annotated[int, Query(
    description="Taxi zone id. Use `/zones` to look it up. Example: 161 = Midtown Center.",
    ge=1, le=263,
)]
Ts = Annotated[datetime, Query(
    description="Local NYC time, format `YYYY-MM-DDTHH:MM`, between 2025-10-01T00:00 and 2025-12-31T23:00.",
)]
Day = Annotated[date, Query(
    description="Date, format `YYYY-MM-DD`, between 2025-10-01 and 2025-12-31.",
)]


def to_local_hour(ts: datetime) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("America/New_York").tz_localize(None)
    return ts.floor("h")


def check_zone(zone_id: int):
    if zone_id not in ZONE_IDS:
        raise HTTPException(404, f"Unknown zone_id: {zone_id}. Use /zones to find valid ids.")


def check_ts(ts: pd.Timestamp):
    if not (TS_MIN <= ts <= TS_MAX):
        raise HTTPException(422, f"Time must be between {TS_MIN} and {TS_MAX}.")


def predict(rows: pd.DataFrame) -> pd.DataFrame:
    X = rows[FEATURES].copy()
    X["zone_id"] = X["zone_id"].astype("category")
    out = rows[["ts", "zone_id", "n_requests"]].rename(columns={"n_requests": "actual"})
    out["predicted"] = booster.predict(X).round(1)
    out["actual"] = out["actual"].astype(int)
    return out

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")
@app.get("/health", summary="Check that the API is running")
def health():
    return {"status": "ok", "data_range": [str(TS_MIN), str(TS_MAX)]}


@app.get("/zones", summary="List zones, filter by borough or search by name")
def list_zones(
    borough: Annotated[Borough | None, Query(description="Pick a borough")] = None,
    search: Annotated[str | None, Query(description="Part of a zone name, e.g. `Midtown` or `Airport`")] = None,
):
    z = zones
    if borough:
        z = z[z["borough"] == borough.value]
    if search:
        z = z[z["zone"].str.contains(search, case=False, na=False)]
    return z.to_dict(orient="records")


@app.get("/predict", summary="Forecast one zone for one hour")
def predict_one(zone_id: ZoneId = 161, ts: Ts = datetime(2025, 11, 14, 18)):
    check_zone(zone_id)
    ts = to_local_hour(ts)
    check_ts(ts)
    row = predict(data[(data["zone_id"] == zone_id) & (data["ts"] == ts)]).iloc[0]
    name = zones.loc[zones["zone_id"] == zone_id, "zone"].iloc[0]
    return {"zone_id": zone_id, "zone": name, "ts": str(ts),
            "predicted": float(row["predicted"]), "actual": int(row["actual"])}


@app.get("/predict/day", summary="Forecast one zone for all 24 hours of a day")
def predict_day(zone_id: ZoneId = 161, day: Day = date(2025, 11, 14)):
    check_zone(zone_id)
    start = pd.Timestamp(day)
    check_ts(start)
    rows = data[(data["zone_id"] == zone_id) &
                (data["ts"] >= start) & (data["ts"] < start + timedelta(days=1))]
    out = predict(rows)
    out["ts"] = out["ts"].astype(str)
    name = zones.loc[zones["zone_id"] == zone_id, "zone"].iloc[0]
    return {"zone_id": zone_id, "zone": name, "day": str(day),
            "hours": out[["ts", "predicted", "actual"]].to_dict(orient="records")}


@app.get("/predict/city", summary="Forecast all zones for one hour")
def predict_city(ts: Ts = datetime(2025, 11, 14, 18)):
    ts = to_local_hour(ts)
    check_ts(ts)
    out = predict(data[data["ts"] == ts]).merge(zones, on="zone_id")
    return {"ts": str(ts),
            "total_predicted": round(float(out["predicted"].sum())),
            "total_actual": int(out["actual"].sum()),
            "zones": out[["zone_id", "borough", "zone", "predicted", "actual"]]
                       .to_dict(orient="records")}