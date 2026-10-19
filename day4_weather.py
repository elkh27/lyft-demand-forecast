import json
import urllib.request
import pandas as pd

url = (
    "https://archive-api.open-meteo.com/v1/archive"
    "?latitude=40.75&longitude=-73.98"
    "&start_date=2023-12-31&end_date=2026-01-01"
    "&hourly=temperature_2m,precipitation,snowfall"
    "&timezone=GMT"
)
with urllib.request.urlopen(url) as r:
    data = json.load(r)

w = pd.DataFrame(data["hourly"])

# Convert UTC to New York local time to match the trip data
w["ts"] = (pd.to_datetime(w["time"])
             .dt.tz_localize("UTC")
             .dt.tz_convert("America/New_York")
             .dt.tz_localize(None))
w = w.drop(columns="time").groupby("ts", as_index=False).mean()

w.to_parquet("data/weather.parquet", index=False)
print(w.shape)
print(w.describe().round(2))