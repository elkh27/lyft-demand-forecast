import duckdb

con = duckdb.connect()

# ۱. ترکیب فایل‌های ماهانه
con.sql("""
    CREATE TABLE counts AS
    SELECT hour, zone_id, SUM(n_requests) AS n_requests
    FROM read_parquet('data/monthly_counts/*.parquet')
    WHERE hour >= '2024-01-01' AND hour < '2026-01-01'
    GROUP BY ALL
""")

# ۲. همه‌ی ترکیب‌های ساعت و منطقه
con.sql("""
    CREATE TABLE grid AS
    SELECT h.hour, z.LocationID AS zone_id
    FROM generate_series(
        TIMESTAMP '2024-01-01 00:00:00',
        TIMESTAMP '2025-12-31 23:00:00',
        INTERVAL 1 HOUR
    ) AS h(hour)
    CROSS JOIN (
        SELECT LocationID
        FROM read_csv_auto('data/taxi_zone_lookup.csv')
        WHERE LocationID NOT IN (1, 264, 265)
    ) AS z
""")

# ۳. وصل کردن تعدادها و پر کردن خالی‌ها با صفر
con.sql("""
    COPY (
        SELECT g.hour, g.zone_id,
               COALESCE(c.n_requests, 0) AS n_requests
        FROM grid g
        LEFT JOIN counts c USING (hour, zone_id)
        ORDER BY g.zone_id, g.hour
    ) TO 'data/zone_hour_panel.parquet' (FORMAT parquet)
""")

print("Saved data/zone_hour_panel.parquet")