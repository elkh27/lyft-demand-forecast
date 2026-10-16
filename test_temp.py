import duckdb
con = duckdb.connect()
print(con.sql("""
    SELECT * FROM 'data/zone_hour_panel.parquet'
    WHERE zone_id = 132
    ORDER BY hour
    LIMIT 10
"""))