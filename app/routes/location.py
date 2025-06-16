# ------------------- app/routes/location.py -------------------
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database
from shapely import wkt
from geoalchemy2.shape import from_shape

router = APIRouter(
    prefix="/locations",
    tags=["Locations"]
)

from ..db_utils import get_db

@router.post("/", response_model=schemas.LocationOut)
def create_location(location: schemas.LocationCreate, db: Session = Depends(get_db)):
    print(location)
    # try:
    print(location.geom)
    point_geom = from_shape(wkt.loads(location.geom), srid=4326)
    # except Exception:
        # raise HTTPException(status_code=400, detail="Invalid WKT geometry")

    db_location = models.Location(name=location.name, geom=point_geom)
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

@router.get("/", response_model=list[schemas.LocationOut])
def read_locations(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(models.Location).offset(skip).limit(limit).all()

@router.get("/{location_id}", response_model=schemas.LocationOut)
def read_location(location_id: int, db: Session = Depends(get_db)):
    location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location
