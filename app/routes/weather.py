# ------------------- app/routes/weather.py -------------------
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, models, db_utils
from ..database import SessionLocal

router = APIRouter(
    prefix="/weather",
    tags=["Weather"]
)

from ..db_utils import get_db

@router.get("/", response_model=list[schemas.WeatherOut])
def read_weather(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db_utils.get_all_weather(db, skip, limit)

@router.get("/{date}", response_model=schemas.WeatherOut)
def read_weather_by_date(date: str, db: Session = Depends(get_db)):
    weather = db_utils.get_weather_by_date(db, date)
    if not weather:
        raise HTTPException(status_code=404, detail="Date not found")
    return weather

@router.post("/", response_model=schemas.WeatherOut)
def create_weather(weather: schemas.WeatherCreate, db: Session = Depends(get_db)):
    db_weather = models.Weather(**weather.dict())
    db.add(db_weather)
    db.commit()
    db.refresh(db_weather)
    return db_weather
