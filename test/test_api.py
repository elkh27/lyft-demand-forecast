import numpy as np
from fastapi.testclient import TestClient

from app.main import app, booster, data, FEATURES

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_zones_search_finds_airports():
    r = client.get("/zones", params={"search": "Airport"})
    names = [z["zone"] for z in r.json()]
    assert "JFK Airport" in names
    assert "LaGuardia Airport" in names


def test_predict_one_hour():
    r = client.get("/predict", params={"zone_id": 161, "ts": "2025-11-14T18:00"})
    assert r.status_code == 200
    body = r.json()
    assert body["zone"] == "Midtown Center"
    assert body["predicted"] >= 0
    assert body["actual"] == 176


def test_minutes_are_rounded_down():
    a = client.get("/predict", params={"zone_id": 161, "ts": "2025-11-14T18:45"}).json()
    b = client.get("/predict", params={"zone_id": 161, "ts": "2025-11-14T18:00"}).json()
    assert a == b


def test_unknown_zone_returns_404():
    # zone 1 (Newark) is a valid id format but has no data
    r = client.get("/predict", params={"zone_id": 1, "ts": "2025-11-14T18:00"})
    assert r.status_code == 404


def test_time_outside_range_returns_422():
    r = client.get("/predict", params={"zone_id": 161, "ts": "2024-06-01T12:00"})
    assert r.status_code == 422


def test_day_has_24_hours():
    r = client.get("/predict/day", params={"zone_id": 132, "day": "2025-11-14"})
    assert r.status_code == 200
    assert len(r.json()["hours"]) == 24


def test_city_covers_all_zones_and_totals_match():
    body = client.get("/predict/city", params={"ts": "2025-11-14T18:00"}).json()
    assert len(body["zones"]) == 262
    assert body["total_actual"] == sum(z["actual"] for z in body["zones"])
    assert body["total_actual"] == 14104


def test_model_accuracy_has_not_regressed():
    X = data[FEATURES].copy()
    X["zone_id"] = X["zone_id"].astype("category")
    pred = booster.predict(X)
    y = data["n_requests"].values
    wape = np.abs(y - pred).sum() / y.sum() * 100
    assert 18.5 < wape < 19.3