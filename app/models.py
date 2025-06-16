from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy import Column, ForeignKey, Integer, Float, Date, String
from sqlalchemy.orm import relationship
from .database import Base


class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True)
    temp_max = Column(Float)
    temp_min = Column(Float)
    precipitation = Column(Float)
    location_id = Column(Integer, ForeignKey('location.id', name='fk_weather_location'), nullable=True)
    location = relationship("Location")


class Location(Base):
    __tablename__ = "location"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    geom = Column(Geometry(geometry_type='POINT', srid=4326))

    @property
    def geom_wkt(self):
        if self.geom:
            return to_shape(self.geom).wkt
        return None