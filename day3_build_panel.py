import urllib.request
from pathlib import Path
import duckdb

DATA_DIR = Path("data")
AGG_DIR = DATA_DIR / "monthly_counts"
AGG_DIR.mkdir(parents=True, exist_ok=True)
BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"

months = [f"{y}-{m:02d}" for y in (2024, 2025) for m in range(1, 13)]
con = duckdb.connect()

for month in months:
    out = AGG_DIR / f"counts_{month}.parquet"
    if out.exists():
        print(f"{month}: already done")
        continue

    raw = DATA_DIR / f"fhvhv_tripdata_{month}.parquet"
    keep_raw = raw.exists()   # keep the files downloaded earlier
    if not raw.exists():
        print(f"{month}: downloading ...")
        urllib.request.urlretrieve(f"{BASE}/fhvhv_tripdata_{month}.parquet", raw)

    con.sql(f"""
        COPY (
            SELECT date_trunc('hour', request_datetime) AS hour,
                   PULocationID AS zone_id,
                   COUNT(*) AS n_requests
            FROM read_parquet('{raw}')
            WHERE hvfhs_license_num = 'HV0005'
            GROUP BY ALL
        ) TO '{out}' (FORMAT parquet)
    """)

    if not keep_raw:
        raw.unlink()
    print(f"{month}: done")