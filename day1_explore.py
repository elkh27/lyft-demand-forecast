import duckdb

con = duckdb.connect()

# یک view روی هر سه فایل پارکت؛ داده در حافظه بارگذاری نمی‌شه
con.sql("""
    CREATE VIEW trips AS
    SELECT * FROM read_parquet('data/fhvhv_tripdata_*.parquet')
""")
con.sql("""
    CREATE VIEW zones AS
    SELECT * FROM read_csv_auto('data/taxi_zone_lookup.csv')
""")

# ۱. ستون‌ها و نوع داده‌شون
print(con.sql("DESCRIBE trips"))

# ۲. تعداد کل سفرها
print(con.sql("SELECT COUNT(*) AS n_trips FROM trips"))

# ۳. سهم هر شرکت
print(con.sql("""
    SELECT
        CASE hvfhs_license_num
            WHEN 'HV0003' THEN 'Uber'
            WHEN 'HV0005' THEN 'Lyft'
            ELSE hvfhs_license_num
        END AS company,
        COUNT(*) AS n_trips,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
    FROM trips
    GROUP BY company
    ORDER BY n_trips DESC
"""))

# ۴. ده منطقه‌ی پرتقاضای لیفت
print(con.sql("""
    SELECT z.Borough, z.Zone, COUNT(*) AS n_requests
    FROM trips t
    JOIN zones z ON t.PULocationID = z.LocationID
    WHERE t.hvfhs_license_num = 'HV0005'
    GROUP BY z.Borough, z.Zone
    ORDER BY n_requests DESC
    LIMIT 10
"""))