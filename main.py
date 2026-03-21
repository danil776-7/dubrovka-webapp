from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import requests

# =====================
# НАСТРОЙКИ
# =====================

DATABASE_URL = "sqlite:////data/db.sqlite"

TELEGRAM_BOT_TOKEN = "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves"
ADMIN_CHAT_ID = "7545540622"

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "1234"

# =====================
# БАЗА
# =====================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Booking(Base):
    tablename = "bookings"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String)
    guests = Column(Integer)
    table = Column(String)
    date = Column(String)
    time = Column(String)
    user_id = Column(Integer)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TABLE_LIMITS = {
    "1": 7, "2": 5, "3": 5, "4": 5,
    "5": 5, "6": 3, "VIP": 20
}

# =====================
# TELEGRAM
# =====================

def notify(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": text}
        )
    except:
        pass

# =====================
# ROOT
# =====================

@app.get("/")
def root():
    return {"ok": True}

# =====================
# LOGIN
# =====================

@app.post("/login")
def login(data: dict):
    if data.get("login") == ADMIN_LOGIN and data.get("password") == ADMIN_PASSWORD:
        return {"ok": True}
    return {"error": "invalid"}

# =====================
# BOOKINGS
# =====================

@app.get("/bookings")
def get_all():
    db = SessionLocal()
    data = db.query(Booking).all()
    db.close()
    return [b.__dict__ for b in data]

@app.get("/bookings_by_date")
def by_date(date: str):
    db = SessionLocal()
    data = db.query(Booking).filter(Booking.date == date).all()
    db.close()
    return [b.__dict__ for b in data]

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

# =====================
# CREATE
# =====================

@app.post("/booking")
def create(data: dict):
    db = SessionLocal()

    guests = int(data["guests"])
    table = data["table"]

    if guests > TABLE_LIMITS.get(table, 5):
        return {"error": "guests_limit"}

    exists = db.query(Booking).filter(
        Booking.date == data["date"],
        Booking.time == data["time"],
        Booking.table == table,
        Booking.status != "done"
    ).first()

    if exists:
        return {"error": "busy"}

    b = Booking(**data)
    db.add(b)
    db.commit()
    db.close()

    notify(f"Новая бронь\n{data}")

    return {"ok": True}

# =====================
# DONE
# =====================

@app.post("/done/{id}")
def done(id: int):
    db = SessionLocal()
    b = db.query(Booking).get(id)
    if b:
        b.status = "done"
        db.commit()
    db.close()
    return {"ok": True}