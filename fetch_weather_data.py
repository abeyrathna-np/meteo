import requests
from datetime import datetime
from app.database import SessionLocal
from app.models import Weather

url = (
    "https://archive-api.open-meteo.com/v1/archive?"
    "latitude=6.9271&longitude=79.8612"
    "&start_date=2000-01-01&end_date=2025-06-01"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
    "&timezone=auto"
)

response = requests.get(url)
data = response.json()

records = []
for i in range(len(data["daily"]["time"])):
    records.append(Weather(
        date=datetime.strptime(data["daily"]["time"][i], "%Y-%m-%d").date(),
        temp_max=data["daily"]["temperature_2m_max"][i],
        temp_min=data["daily"]["temperature_2m_min"][i],
        precipitation=data["daily"]["precipitation_sum"][i],
        location_id=1
    ))

# Insert into DB
session = SessionLocal()
session.bulk_save_objects(records)
session.commit()
session.close()