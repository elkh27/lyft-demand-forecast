import duckdb

def get_con():
    con = duckdb.connect()
    con.sql("""
        CREATE VIEW trips AS
        SELECT * FROM read_parquet('data/fhvhv_tripdata_*.parquet')
    """)
    con.sql("""
        CREATE VIEW zones AS
        SELECT * FROM read_csv_auto('data/taxi_zone_lookup.csv')
    """)
    # Lyft only, and only requests inside the three-month window
    con.sql("""
        CREATE VIEW lyft AS
        SELECT * FROM trips
        WHERE hvfhs_license_num = 'HV0005'
          AND request_datetime >= '2025-01-01'
          AND request_datetime <  '2025-04-01'
    """)
    return con