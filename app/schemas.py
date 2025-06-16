from pydantic import BaseModel
from datetime import date

class LocationBase(BaseModel):
    name:str
    geom: str

class LocationCreate(LocationBase):
    pass

class LocationOut(BaseModel):
    id: int
    name: str
    geom_wkt: str

    class Config:
        orm_mode = True

class WeatherBase(BaseModel):
    date: date
    temp_max: float
    temp_min: float
    precipitation: float
    location_id: int

class WeatherCreate(WeatherBase):
    pass

class WeatherOut(WeatherBase):
    id: int
    location: LocationOut

    class Config:
        orm_mode = True

