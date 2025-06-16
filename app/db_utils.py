from sqlalchemy.orm import Session, joinedload
from . import models
from .database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_all_weather(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Weather)
        .options(joinedload(models.Weather.location))
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_weather_by_date(db: Session, date):
    return (
        db.query(models.Weather)
        .options(joinedload(models.Weather.location))
        .filter(models.Weather.date == date)
        .first()
    )
