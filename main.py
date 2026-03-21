from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import requests

# ========= НАСТРОЙКИ =========
DATABASE_URL = "sqlite:////data/db.sqlite"

TELEGRAM_BOT_TOKEN = "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves"
ADMIN_CHAT_ID = "7545540622"

# ========= БАЗА =========
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ========= МОДЕЛЬ =========
class Booking(Base):
    tablename = "bookings"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String)
    guests = Column(Integer)
    table = Column(String)
    date = Column(String)
    time = Column(String)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

# ========= APP =========
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= TELEGRAM =========
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
        print("telegram error")

# ========= ROOT =========
@app.get("/")
def root():
    return {"ok": True}

# ========= BUSY =========
@app.get("/busy_times")
def busy(date: str, table: str):
    db = SessionLocal()
    data = db.query(Booking).filter(
        Booking.date == date,
        Booking.table == table,
        Booking.status != "done"
    ).all()
    db.close()
    return [b.time for b in data]

# ========= BOOK =========
@app.post("/booking")
def book(data: dict):
    db = SessionLocal()

    exists = db.query(Booking).filter(
        Booking.date == data["date"],
        Booking.time == data["time"],
        Booking.table == data["table"],
        Booking.status != "done"
    ).first()

    if exists:
        return {"error": "busy"}

    booking = Booking(**data)
    db.add(booking)
    db.commit()
    db.close()

    send_telegram(
        f"Новая бронь\n"
        f"{data['name']} | {data['phone']}\n"
        f"Стол {data['table']} | {data['date']} {data['time']}"
    )

    return {"ok": True}

# ========= DONE =========
@app.post("/done/{id}")
def done(id: int):
    db = SessionLocal()
    b = db.query(Booking).filter(Booking.id == id).first()
    if b:
        b.status = "done"
        db.commit()
    db.close()
    return {"ok": True}