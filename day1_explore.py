import duckdb

con = duckdb.connect()

# A view over all Parquet files; data is not loaded into memory
con.sql("""
    CREATE VIEW trips AS
    SELECT * FROM read_parquet('data/fhvhv_tripdata_*.parquet')
""")
con.sql("""
    CREATE VIEW zones AS
    SELECT * FROM read_csv_auto('data/taxi_zone_lookup.csv')
""")

# 1. Columns and their types
print(con.sql("DESCRIBE trips"))

# 2. Total number of trips
print(con.sql("SELECT COUNT(*) AS n_trips FROM trips"))

# 3. Share of each company
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

# 4. Top 10 Lyft pickup zones
print(con.sql("""
    SELECT z.Borough, z.Zone, COUNT(*) AS n_requests
    FROM trips t
    JOIN zones z ON t.PULocationID = z.LocationID
    WHERE t.hvfhs_license_num = 'HV0005'
    GROUP BY z.Borough, z.Zone
    ORDER BY n_requests DESC
    LIMIT 10
"""))