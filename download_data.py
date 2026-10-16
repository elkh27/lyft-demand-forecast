import urllib.request
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://d37ci6vzurychx.cloudfront.net"
months = ["2025-01", "2025-02", "2025-03"]

for m in months:
    out = DATA_DIR / f"fhvhv_tripdata_{m}.parquet"
    if not out.exists():
        print(f"Downloading {m} ...")
        urllib.request.urlretrieve(f"{BASE}/trip-data/fhvhv_tripdata_{m}.parquet", out)

zones = DATA_DIR / "taxi_zone_lookup.csv"
if not zones.exists():
    urllib.request.urlretrieve(f"{BASE}/misc/taxi_zone_lookup.csv", zones)




shp = DATA_DIR / "taxi_zones.zip"
if not shp.exists():
    urllib.request.urlretrieve(f"{BASE}/misc/taxi_zones.zip", shp)


print("Done")