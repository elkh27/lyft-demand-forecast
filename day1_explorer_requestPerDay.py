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
        EXTRACT(hour FROM request_datetime) AS hour,
        COUNT(*) AS n_requests
    From trips
    WHERE hvfhs_license_num = 'HV0005'
    GROUP BY hour
    ORDER BY hour
""").df().to_string())




print(con.sql("""
    SELECT
        dayname(request_datetime) AS day,
        COUNT(*) AS n_requests
    FROM trips
    WHERE hvfhs_license_num = 'HV0005'
    GROUP BY day
    ORDER BY day
""").df().to_string())


# ۶. میانگین درخواست‌های لیفت در هر روز هفته
print(con.sql("""
    SELECT
        isodow(request_datetime) AS dow,
        dayname(request_datetime) AS day,
        COUNT(*) AS n_requests,
        COUNT(DISTINCT CAST(request_datetime AS DATE)) AS n_days,
        ROUND(COUNT(*) / COUNT(DISTINCT CAST(request_datetime AS DATE))) AS avg_per_day
    FROM trips
    WHERE hvfhs_license_num = 'HV0005'
    GROUP BY dow, day
    ORDER BY dow
""").df().to_string())