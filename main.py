from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
import requests
import os
import threading
import time

# =====================
# DATABASE
# =====================

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# =====================
# MODEL
# =====================

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    guests = Column(Integer)
    table = Column(String)
    date = Column(String)
    time = Column(String)
    status = Column(String, default="active")
    chat_id = Column(String, nullable=True)

# создаем таблицы
Base.metadata.create_all(bind=engine)

# =====================
# APP
# =====================

app = FastAPI()

# ✅ ПРАВИЛЬНЫЙ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://danil776-7.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# CONFIG (БЕЗОПАСНО)
# =====================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TELEGRAM_BOT_TOKEN:
    raise Exception("❌ TELEGRAM_BOT_TOKEN не задан")

if not ADMIN_CHAT_ID:
    raise Exception("❌ ADMIN_CHAT_ID не задан")

# =====================
# LIMITS
# =====================

TABLE_LIMITS = {
    "1": 7,
    "2": 5,
    "3": 5,
    "4": 5,
    "5": 5,
    "6": 3,
    "VIP": 20
}

# =====================
# TELEGRAM
# =====================

def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=5
        )
    except Exception as e:
        print("Telegram error:", e)

# =====================
# HELPERS
# =====================

def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        raise HTTPException(status_code=400, detail="Invalid date")

# =====================
# ENDPOINTS
# =====================

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/bookings_by_date")
def bookings_by_date(date: str):
    db = SessionLocal()
    try:
        date = normalize_date(date)

        data = db.query(Booking).filter(
            Booking.date == date,
            Booking.status == "active"
        ).all()

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
    finally:
        db.close()

@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()
    try:
        required = ["name", "phone", "guests", "table", "date", "time"]

        for field in required:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing {field}")

        date = normalize_date(data["date"])
        table = str(data["table"])
        time_ = data["time"]
        guests = int(data["guests"])

        if guests > TABLE_LIMITS.get(table, 0):
            raise HTTPException(status_code=400, detail="Too many guests")

        exists = db.query(Booking).filter(
            Booking.date == date,
            Booking.time == time_,
            Booking.table == table,
            Booking.status == "active"
        ).first()

        if exists:
            raise HTTPException(status_code=409, detail="Busy")

        booking = Booking(
            name=data["name"],
            phone=data["phone"],
            guests=guests,
            table=table,
            date=date,
            time=time_
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        send_telegram(
            f"🔥 Новая бронь\n"
            f"{booking.name} | {booking.phone}\n"
            f"{booking.date} {booking.time}\n"
            f"Стол {booking.table}"
        )

        return {"ok": True, "id": booking.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/cancel/{id}")
def cancel(id: int):
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(
            Booking.id == id,
            Booking.status == "active"
        ).first()

        if not booking:
            raise HTTPException(status_code=404, detail="Not found")

        booking.status = "cancelled"
        db.commit()

        return {"ok": True}
    finally:
        db.close()
