from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os
import requests

app = FastAPI()

# =====================
# DATABASE (Railway)
# =====================

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# =====================
# MODEL
# =====================

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String)
    guests = Column(Integer)
    table = Column(String)
    date = Column(String)
    time = Column(String)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

# =====================
# CORS
# =====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# CONFIG
# =====================

TELEGRAM_BOT_TOKEN = "ТВОЙ_ТОКЕН"
ADMIN_CHAT_ID = "ТВОЙ_ID"

# =====================
# LIMITS
# =====================

TABLE_LIMITS = {
    "1": 11,
    "2": 6,
    "3": 6,
    "4": 6,
    "5": 6,
    "6": 3,
    "VIP": 20
}

# =====================
# HELPERS
# =====================

def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": text
            }
        )
    except:
        pass

def is_past(date, time):
    try:
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        return dt < datetime.now()
    except:
        return False

# =====================
# ROOT
# =====================

@app.get("/")
def root():
    return {"status": "ok"}

# =====================
# GET BOOKINGS
# =====================

@app.get("/bookings")
def get_bookings():
    db = SessionLocal()
    data = db.query(Booking).all()
    db.close()

    return [
        {
            "id": b.id,
            "name": b.name,
            "phone": b.phone,
            "guests": b.guests,
            "table": b.table,
            "date": b.date,
            "time": b.time,
            "status": b.status
        }
        for b in data
    ]

# =====================
# BOOKINGS BY DATE
# =====================

@app.get("/bookings_by_date")
def bookings_by_date(date: str):
    db = SessionLocal()

    data = db.query(Booking).filter(
        Booking.date == date,
        Booking.status != "done"
    ).all()

    db.close()

    return [
        {
            "id": b.id,
            "name": b.name,
            "phone": b.phone,
            "guests": b.guests,
            "table": b.table,
            "date": b.date,
            "time": b.time,
            "status": b.status
        }
        for b in data
    ]

# =====================
# BUSY TIMES
# =====================

@app.get("/busy_times")
def busy_times(date: str, table: str):
    db = SessionLocal()

    data = db.query(Booking).filter(
        Booking.date == date,
        Booking.table == table,
        Booking.status != "done"
    ).all()

    db.close()

    return [b.time for b in data]

# =====================
# CREATE BOOKING
# =====================

"/booking"
def create_booking(data: dict):
    db = SessionLocal()

    date = data["date"]
    table = str(data["table"])
    time = data["time"]
    guests = int(data["guests"])

    if is_past(date, time):
        return {"error": "past"}

    if guests > TABLE_LIMITS.get(table, 5):
        return {"error": "limit"}

    exists = db.query(Booking).filter(
        Booking.date == date,
        Booking.time == time,
        Booking.table == table,
        Booking.status != "done"
    ).first()

    if exists:
        return {"error": "busy"}

    booking = Booking(
        name=data["name"],
        phone=data["phone"


,
        guests=guests,
        table=table,
        date=date,
        time=time
    )

    db.add(booking)
    db.commit()
    db.close()

    send_telegram(f"Новая бронь: {data}")

    return {"ok": True}

# =====================
# DONE
# =====================

"/done/{id}"
def done(id: int):
    db = SessionLocal()

    booking = db.query(Booking).filter(
        Booking.id == id
    ).first()

    if not booking:
        return {"error": "not_found"}

    booking.status = "done"
    db.commit()
    db.close()

    return {"ok": True}]
