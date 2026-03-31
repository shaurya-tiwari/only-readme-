"""
Location APIs for DB-backed geography.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.location_service import location_service
from backend.database import get_db
from backend.schemas.location import CityResponse, LocationConfigResponse, ZoneResponse

router = APIRouter(prefix="/api/locations", tags=["Locations"])


@router.get("/cities", response_model=list[CityResponse])
async def list_cities(db: AsyncSession = Depends(get_db)):
    cities = await location_service.get_active_cities(db)
    return cities


@router.get("/zones", response_model=list[ZoneResponse])
async def list_zones(city_slug: str | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    zones = await location_service.get_active_zones(db, city_slug=city_slug)
    return [
        ZoneResponse(
            id=zone.id,
            city_id=zone.city_id,
            city_slug=zone.city_ref.slug,
            slug=zone.slug,
            display_name=zone.display_name,
            active=zone.active,
            centroid_lat=float(zone.centroid_lat) if zone.centroid_lat is not None else None,
            centroid_lon=float(zone.centroid_lon) if zone.centroid_lon is not None else None,
        )
        for zone in zones
    ]


@router.get("/config", response_model=LocationConfigResponse)
async def get_location_config(db: AsyncSession = Depends(get_db)):
    cities = await location_service.get_active_cities(db)
    zones = await location_service.get_active_zones(db)
    return LocationConfigResponse(
        cities=cities,
        zones=[
            ZoneResponse(
                id=zone.id,
                city_id=zone.city_id,
                city_slug=zone.city_ref.slug,
                slug=zone.slug,
                display_name=zone.display_name,
                active=zone.active,
                centroid_lat=float(zone.centroid_lat) if zone.centroid_lat is not None else None,
                centroid_lon=float(zone.centroid_lon) if zone.centroid_lon is not None else None,
            )
            for zone in zones
        ],
    )
