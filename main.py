from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import requests

# =====================
# DATABASE (Render fix)
# =====================

DATABASE_URL = "sqlite:////tmp/db.sqlite"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
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
# HELPERS
# =====================

def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return date_str

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
# БРОНИ ПО ДАТЕ
# =====================

@app.get("/bookings_by_date")
def bookings_by_date(date: str):
    db = SessionLocal()
    date = normalize_date(date)

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
# ЗАНЯТЫЕ ВРЕМЕНА
# =====================

@app.get("/busy_times")
def busy_times(date: str, table: str):
    db = SessionLocal()
    date = normalize_date(date)

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

"/booking"
def create_booking(data: dict):
    db = SessionLocal()

    date = normalize_date(data["date"])
    table = str(data["table"])
    time = data["time"]
    guests = int(data["guests"])

    # 🔒 лимит гостей
    max_guests = TABLE_LIMITS.get(table, 5)
    if guests > max_guests:
        return {"error": "guests_limit"}

    # 🔒 проверка занятости
    exists = db.query(Booking).filter(


ooking.date == date,
        Booking.time == time,
        Booking.table == table,
        Booking.status != "done"
    ).first()

    if exists:
        return {"error": "busy"}

    booking = Booking(
        name=data["name"],
        phone=data["phone"],
        guests=guests,
        table=table,
        date=date,
        time=time,
        status="pending"
    )

    db.add(booking)
    db.commit()
    db.close()

    # 🔥 TELEGRAM
    send_telegram(
        f"<b>🔥 Новая бронь</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"👥 Гости: {guests}\n"
        f"🪑 Стол: {table}\n"
        f"📅 Дата: {date}\n"
        f"⏰ Время: {time}"
    )

    return {"ok": True}

# =====================
# ГОСТЬ УШЕЛ
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

    return {"ok": True} 
