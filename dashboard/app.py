import json
import os
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
GEO_PATH = Path(__file__).resolve().parent.parent / "serving" / "taxi_zones.geojson"

st.set_page_config(page_title="NYC Lyft Demand Forecast", page_icon="🚗", layout="wide")


@st.cache_data
def load_geojson():
    with open(GEO_PATH) as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def api_get(path, **params):
    r = requests.get(f"{API_URL}{path}", params=params, timeout=90)
    r.raise_for_status()
    return r.json()


# اگه رابط در دسترس نیست، پیام واضح بده
try:
    api_get("/health")
except requests.RequestException:
    st.error(f"Cannot reach the forecast API at {API_URL}. Start it first.")
    st.stop()

# ---------- نوار کناری ----------
st.sidebar.header("Choose a time")
day = st.sidebar.date_input("Date", value=date(2025, 11, 14),
                            min_value=date(2025, 10, 1), max_value=date(2025, 12, 31))
hour = st.sidebar.slider("Hour", 0, 23, 18, format="%d:00")
ts = datetime.combine(day, time(hour))
st.sidebar.caption("Forecasts are made one day ahead. Times are New York local time.")

st.title("NYC Lyft Demand Forecast")
st.caption(f"{ts:%A, %B %d, %Y · %H:00}")

tab_map, tab_zone, tab_about = st.tabs(["City map", "Zone detail", "About the model"])

# ---------- تب ۱: نقشه ----------
with tab_map:
    city = api_get("/predict/city", ts=ts.isoformat())
    df = pd.DataFrame(city["zones"])
    df["error"] = df["predicted"] - df["actual"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted requests (city)", f"{city['total_predicted']:,}")
    c2.metric("Actual requests", f"{city['total_actual']:,}")
    err = (city["total_predicted"] - city["total_actual"]) / city["total_actual"] * 100
    c3.metric("City-wide forecast error", f"{err:+.1f}%")

    layer = st.radio("Show on map", ["Predicted", "Actual", "Error (predicted − actual)"],
                     horizontal=True)
    if layer.startswith("Error"):
        col, scale = "error", "RdBu_r"
        m = df["error"].abs().quantile(0.98)
        rng = (-m, m)
    else:
        col, scale = layer.lower(), "OrRd"
        rng = (0, df[["predicted", "actual"]].max().max())

    fig = px.choropleth_map(
        df, geojson=load_geojson(), locations="zone_id",
        featureidkey="properties.zone_id", color=col,
        color_continuous_scale=scale, range_color=rng,
        map_style="carto-positron", zoom=10, center={"lat": 40.70, "lon": -73.92},
        opacity=0.7, hover_name="zone",
        hover_data={"borough": True, "predicted": True, "actual": True, "zone_id": False},
    )
    fig.update_layout(height=650, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Busiest zones (predicted)")
    st.dataframe(df.nlargest(10, "predicted")[["zone", "borough", "predicted", "actual"]],
                 hide_index=True, use_container_width=True)

# ---------- تب ۲: یک منطقه ----------
with tab_zone:
    zones = pd.DataFrame(api_get("/zones"))
    zones["label"] = (zones["zone_id"].astype(str) + " – " + zones["zone"]
                      + " (" + zones["borough"] + ")")
    default = int(zones.index[zones["zone_id"] == 161][0])
    label = st.selectbox("Zone", zones["label"], index=default)
    zone_id = int(label.split(" – ")[0])

    res = api_get("/predict/day", zone_id=zone_id, day=day.isoformat())
    h = pd.DataFrame(res["hours"])
    h["hour"] = pd.to_datetime(h["ts"]).dt.hour

    wape = (h["predicted"] - h["actual"]).abs().sum() / max(h["actual"].sum(), 1) * 100
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted (day)", f"{h['predicted'].sum():,.0f}")
    c2.metric("Actual (day)", f"{h['actual'].sum():,}")
    c3.metric("Day WAPE", f"{wape:.1f}%")

    long = h.melt(id_vars="hour", value_vars=["predicted", "actual"],
                  var_name="series", value_name="requests")
    fig2 = px.line(long, x="hour", y="requests", color="series", markers=True)
    fig2.add_vline(x=hour, line_dash="dot", line_color="grey")
    fig2.update_layout(height=420, xaxis=dict(dtick=1))
    st.plotly_chart(fig2, use_container_width=True)

# ---------- تب ۳: درباره ----------
with tab_about:
    st.markdown("""
**What this shows.** Day-ahead hourly forecasts of Lyft ride requests for 262 NYC taxi zones,
compared with what actually happened, for October – December 2025.

**Data.** NYC TLC High Volume For-Hire Vehicle trip records, Lyft trips only,
2024 – 2025 (128M requests), aggregated to zone × hour with DuckDB.

**Model.** LightGBM with a Poisson objective. Features: hour, weekday, holidays,
and demand from the same zone yesterday, last week and two weeks ago.

**Accuracy on the test period.** WAPE 18.9%, a 26% lower error than the
"same hour last week" baseline (25.7%). Hardest days: holidays such as Christmas and Halloween.
""")