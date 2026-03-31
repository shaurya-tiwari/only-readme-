from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CityResponse(BaseModel):
    id: UUID
    slug: str
    display_name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


class ZoneResponse(BaseModel):
    id: UUID
    city_id: UUID
    city_slug: str
    slug: str
    display_name: str
    active: bool
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None


class LocationConfigResponse(BaseModel):
    cities: List[CityResponse]
    zones: List[ZoneResponse]
