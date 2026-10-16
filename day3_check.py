import duckdb
import matplotlib.pyplot as plt

con = duckdb.connect()
con.sql("CREATE VIEW panel AS SELECT * FROM 'data/zone_hour_panel.parquet'")

print(con.sql("""
    SELECT COUNT(*) AS n_rows,
           COUNT(DISTINCT zone_id) AS n_zones,
           COUNT(DISTINCT hour) AS n_hours,
           SUM(n_requests) AS total_requests,
           ROUND(100.0 * AVG(CASE WHEN n_requests = 0 THEN 1 ELSE 0 END), 1) AS pct_zero
    FROM panel
"""))

monthly = con.sql("""
    SELECT date_trunc('month', hour) AS month,
           SUM(n_requests) / COUNT(DISTINCT CAST(hour AS DATE)) AS avg_per_day
    FROM panel
    GROUP BY month
    ORDER BY month
""").df()

plt.figure(figsize=(12, 4))
plt.plot(monthly["month"], monthly["avg_per_day"], marker="o")
plt.title("Average daily Lyft requests by month, 2024-2025")
plt.tight_layout()
plt.savefig("figures/monthly_trend.png")
plt.show()