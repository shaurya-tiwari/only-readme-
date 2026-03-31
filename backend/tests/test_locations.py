import pytest


@pytest.mark.asyncio
async def test_location_config_available(client):
    cities_response = await client.get("/api/locations/cities")
    assert cities_response.status_code == 200
    cities = cities_response.json()
    assert {city["slug"] for city in cities} >= {"delhi", "mumbai", "bengaluru", "chennai"}

    zones_response = await client.get("/api/locations/zones", params={"city_slug": "delhi"})
    assert zones_response.status_code == 200
    zones = zones_response.json()
    assert any(zone["slug"] == "south_delhi" for zone in zones)


@pytest.mark.asyncio
async def test_worker_registration_uses_db_backed_zone_validation(client, valid_worker_data):
    invalid = {**valid_worker_data, "city": "delhi", "zone": "koramangala"}
    response = await client.post("/api/workers/register", json=invalid)
    assert response.status_code == 400
    assert "Valid zones" in response.json()["detail"]
