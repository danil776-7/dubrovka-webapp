from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
import os
import requests

# =====================
# DATABASE (Railway + fallback)
# =====================

DATABASE_URL = os.getenv("DATABASE_URL")

# если нет Postgres → fallback на SQLite
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./db.sqlite"

# фикс для postgres
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
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
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

# =====================
# APP
# =====================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# CONFIG
# =====================

TELEGRAM_BOT_TOKEN = "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves"
ADMIN_CHAT_ID = "7545540622"

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
# TIMEZONE (Новокузнецк)
# =====================

def now_novokuznetsk():
    return datetime.utcnow() + timedelta(hours=7)

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
            }
        )
    except Exception as e:
        print("TG ERROR:", e)

# =====================
# ROOT
# =====================

@app.get("/")
def root():
    return {"status": "ok"}

# =====================
# ВСЕ БРОНИ (админка)
# =====================

@app.get("/bookings")
def get_bookings():
    db = SessionLocal()
    data = db.query(Booking).all()
    db.close()

    return [b.__dict__ for b in data]

# =====================
# ПО ДАТЕ
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
# ЗАНЯТОЕ ВРЕМЯ
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
# СОЗДАНИЕ БРОНИ
# =====================

@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()

    name = data.get("name")
    phone = data.get("phone")
    guests = int(data.get("guests", 0))
    table = str(data.get("table"))
    date = data.get("date")
    time = data.get("time")

    # ❌ валидация
    if not name or not phone or guests <= 0:
        return {"error": "invalid"}

    # ❌ лимит гостей
    max_guests = TABLE_LIMITS.get(table, 5)
    if guests > max_guests:
        return {"error": "guests_limit"}

    # ❌ проверка времени (Новокузнецк)
    now = now_novokuznetsk()
    booking_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

    if booking_dt < now:
        return {"error": "past_time"}

    # ❌ проверка занятости
    exists = db.query(Booking).filter(
        Booking.date == date,
        Booking.time == time,
        Booking.table == table,
        Booking.status != "done"
    ).first()

    if exists:
        return {"error": "busy"}

    # ✅ создаём
    booking = Booking(
        name=name,
        phone=phone,
        guests=guests,
        table=table,
        date=date,
        time=time,
        status="pending"
    )

    db.add(booking)
    db.commit()
    db.close()

    # 🔔 TELEGRAM
    send_telegram(
        f"<b>🔥 Новая бронь</b>\n\n"
        f"👤 {name}\n"
        f"📞 {phone}\n"
        f"👥 {guests}\n"
        f"🪑 {table}\n"
        f"📅 {date}\n"
        f"⏰ {time}"
    )

    return {"ok": True}

# =====================
# ГОСТЬ УШЕЛ
# =====================

@app.post("/done/{id}")
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

    return {"ok": True}
