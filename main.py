from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import requests
import os

# =====================
# DATABASE
# =====================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL не задан")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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

Base.metadata.create_all(bind=engine)

# =====================
# APP
# =====================

app = FastAPI()

# 🔥 ЖЁСТКИЙ CORS FIX (гарантирует работу)
@app.middleware("http")
async def cors_fix(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# дополнительный CORS (нормальный)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# CONFIG
# =====================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# =====================
# HELPERS
# =====================

def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        raise HTTPException(status_code=400, detail="Invalid date")

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("⚠️ Telegram не настроен")
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": text
            },
            timeout=5
        )
    except Exception as e:
        print("Telegram error:", e)

# =====================
# TEST
# =====================

@app.get("/test")
def test():
    return {"status": "ok"}

# =====================
# ROOT
# =====================

@app.get("/")
def root():
    return {"status": "running"}

# =====================
# BOOKINGS BY DATE
# =====================

@app.get("/bookings_by_date")
def bookings_by_date(date: str):
    db = SessionLocal()
    try:
        print("👉 DATE:", date)

        try:
            date = normalize_date(date)
        except Exception as e:
            print("❌ DATE ERROR:", e)
            return {"error": "invalid date"}

        data = db.query(Booking).filter(
            Booking.date == date,
            Booking.status == "active"
        ).all()

        print("✅ FOUND:", len(data))

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

    except Exception as e:
        print("❌ SERVER ERROR:", e)
        return {"error": str(e)}

    finally:
        db.close()

# =====================
# CREATE BOOKING
# =====================

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

        exists = db.query(Booking).filter(
            Booking.date == date,
            Booking.time == time_,
            Booking.table == table,
            Booking.status == "active"
        ).first()

        if exists:
            return {"error": True}

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
            f"🔥 Новая бронь\n{booking.name} | {booking.phone}\n{booking.date} {booking.time}"
        )

        return {"ok": True, "id": booking.id}

    except Exception as e:
        db.rollback()
        print("❌ ERROR:", e)
        return {"error": str(e)}

    finally:
        db.close()

# =====================
# CANCEL
# =====================

@app.post("/cancel/{id}")
def cancel(id: int):
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(
            Booking.id == id,
            Booking.status == "active"
        ).first()

        if not booking:
            return {"error": True}

        booking.status = "cancelled"
        db.commit()

        return {"ok": True}

    finally:
        db.close()
