from pathlib import Path
import geopandas as gpd

# Same shapefile path used in the exploratory analysis
geo = gpd.read_file("data/taxi_zones/taxi_zones.shp")

geo = geo.to_crs(epsg=4326)
geo["geometry"] = geo.geometry.simplify(0.0002, preserve_topology=True)
geo = geo[["LocationID", "geometry"]].rename(columns={"LocationID": "zone_id"})

out = Path("serving/taxi_zones.geojson")
geo.to_file(out, driver="GeoJSON")
print(f"{len(geo)} shapes, {out.stat().st_size / 1e6:.1f} MB")