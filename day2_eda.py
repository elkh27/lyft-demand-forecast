from pathlib import Path
import matplotlib.pyplot as plt
from db import get_con

con = get_con()
Path("figures").mkdir(exist_ok=True)


daily = con.sql("""
    WITH daily AS (
        SELECT CAST(request_datetime AS DATE) AS day,
               COUNT(*) AS n
        FROM lyft
        GROUP BY day
    )
    SELECT day, n,
           AVG(n) OVER (
               ORDER BY day
               ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
           ) AS ma7
    FROM daily
    ORDER BY day
""").df()

plt.figure(figsize=(12, 4))
plt.plot(daily["day"], daily["n"], alpha=0.5, label="daily")
plt.plot(daily["day"], daily["ma7"], linewidth=2, label="7-day average")
plt.legend()
plt.title("Lyft requests per day, NYC, Jan-Mar 2025")
plt.tight_layout()
plt.savefig("figures/daily_trend.png")


heat = con.sql("""
    SELECT isodow(request_datetime) AS dow,
           hour(request_datetime) AS hour,
           COUNT(*) / COUNT(DISTINCT CAST(request_datetime AS DATE)) AS avg_n
    FROM lyft
    GROUP BY dow, hour
""").df()

pivot = heat.pivot(index="dow", columns="hour", values="avg_n")

plt.figure(figsize=(12, 4))
plt.imshow(pivot, aspect="auto", cmap="viridis")
plt.colorbar(label="avg requests")
plt.yticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
plt.xticks(range(24))
plt.xlabel("hour")
plt.title("Average Lyft requests by weekday and hour")
plt.tight_layout()
plt.savefig("figures/weekday_hour_heatmap.png")



print(con.sql("""
    SELECT z.Borough,
           COUNT(*) AS n,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
    FROM lyft l
    JOIN zones z ON l.PULocationID = z.LocationID
    GROUP BY z.Borough
    ORDER BY n DESC
""").df().to_string())

print(con.sql("""
    WITH zone_counts AS (
        SELECT PULocationID, COUNT(*) AS n
        FROM lyft
        GROUP BY PULocationID
    ),
    ranked AS (
        SELECT PULocationID, n,
               ROW_NUMBER() OVER (ORDER BY n DESC) AS rank,
               SUM(n) OVER (ORDER BY n DESC
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                   * 1.0 / SUM(n) OVER () AS cum_share
        FROM zone_counts
    )
    SELECT MIN(rank) FILTER (WHERE cum_share >= 0.5) AS zones_for_50pct,
           MIN(rank) FILTER (WHERE cum_share >= 0.8) AS zones_for_80pct,
           COUNT(*) AS total_zones
    FROM ranked
""").df().to_string())


import geopandas as gpd
from matplotlib.colors import LogNorm

zone_demand = con.sql("""
    SELECT PULocationID AS LocationID,
           COUNT(*) / COUNT(DISTINCT CAST(request_datetime AS DATE)) AS avg_per_day
    FROM lyft
    GROUP BY PULocationID
""").df()

geo = gpd.read_file("data/taxi_zones/taxi_zones/taxi_zones.shp")
geo = geo.merge(zone_demand, on="LocationID", how="left")

fig, ax = plt.subplots(figsize=(9, 9))
geo.plot(column="avg_per_day", cmap="OrRd", legend=True,
         norm=LogNorm(), edgecolor="grey", linewidth=0.2,
         missing_kwds={"color": "lightgrey"}, ax=ax)
ax.set_axis_off()
ax.set_title("Average daily Lyft requests by pickup zone")
plt.tight_layout()
plt.savefig("figures/zone_map.png")
plt.show()


airport = con.sql("""
    WITH hourly AS (
        SELECT hour(request_datetime) AS hour,
               COUNT(*) FILTER (WHERE PULocationID IN (132, 138)) AS airports,
               COUNT(*) AS city
        FROM lyft
        GROUP BY hour
    )
    SELECT hour,
           ROUND(100.0 * airports / SUM(airports) OVER (), 2) AS airports_pct,
           ROUND(100.0 * city / SUM(city) OVER (), 2) AS city_pct
    FROM hourly
    ORDER BY hour
""").df()

print(airport.to_string())

plt.figure(figsize=(10, 4))
plt.plot(airport["hour"], airport["airports_pct"], marker="o", label="JFK + LaGuardia")
plt.plot(airport["hour"], airport["city_pct"], marker="o", label="whole city")
plt.xticks(range(24))
plt.xlabel("hour")
plt.ylabel("% of daily requests")
plt.legend()
plt.title("Hourly demand pattern: airports vs whole city")
plt.tight_layout()
plt.savefig("figures/airports_vs_city.png")
plt.show()