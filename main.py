from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import requests
import os

# =====================
# DATABASE (RAILWAY POSTGRES)
# =====================

DATABASE_URL = os.getenv("DATABASE_URL")

# 🔥 ПРОВЕРКА: если переменная не установлена
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Please add it in Railway Variables."
    )

# 🔥 фикс Railway postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

print(f"✅ Connecting to database: {DATABASE_URL.replace('postgresql://postgres:', 'postgresql://***:***@')}")  # Лог без пароля

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

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    guests = Column(Integer)
    table = Column(String)
    date = Column(String)
    time = Column(String)
    status = Column(String, default="active")

# Создаем таблицы
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    raise

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

TELEGRAM_BOT_TOKEN = os.getenv("8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves")
ADMIN_CHAT_ID = os.getenv("7545540622")

# Проверка Telegram переменных
if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
    print("⚠️ WARNING: TELEGRAM_BOT_TOKEN or ADMIN_CHAT_ID not set. Telegram notifications disabled.")

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
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("⚠️ Telegram not configured, skipping notification")
        return
    
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
        print("✅ Telegram notification sent")
    except Exception as e:
        print("❌ TG ERROR:", e)

# =====================
# HELPERS
# =====================

def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        raise HTTPException(status_code=400, detail="Invalid date")

# =====================
# ROOT
# =====================

@app.get("/")
def root():
    return {
        "status": "ok",
        "database": "connected" if DATABASE_URL else "not configured"
    }

# =====================
# БРОНИ ПО ДАТЕ (АДМИНКА)
# =====================

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

# =====================
# ЗАНЯТЫЕ ВРЕМЕНА
# =====================

@app.get("/busy_times")
def busy_times(date: str, table: str):
    db = SessionLocal()

    try:
        date = normalize_date(date)

        data = db.query(Booking).filter(
            Booking.date == date,
            Booking.table == table,
            Booking.status == "active"
        ).all()

        return [b.time for b in data]

    finally:
        db.close()

# =====================
# СОЗДАНИЕ БРОНИ
# =====================

@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()

    try:
        # Проверка обязательных полей
        required = ["name", "phone", "guests", "table", "date", "time"]
        for field in required:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")

        date = normalize_date(data["date"])
        table = str(data["table"])
        time = data["time"]
        guests = int(data["guests"])

        # Проверка существования стола
        if table not in TABLE_LIMITS:
            raise HTTPException(status_code=400, detail=f"Table {table} does not exist")

        # лимит гостей
        if guests > TABLE_LIMITS[table]:
            raise HTTPException(status_code=400, detail="Too many guests for this table")

        # проверка занятости (только активные)
        exists = db.query(Booking).filter(
            Booking.date == date,
            Booking.time == time,
            Booking.table == table,
            Booking.status == "active"
        ).first()

        if exists:
            raise HTTPException(status_code=409, detail="Time slot already booked")

        booking = Booking(
            name=data["name"],
            phone=data["phone"],
            guests=guests,
            table=table,
            date=date,
            time=time,
            status="active"
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        # Telegram только после успешного создания
        send_telegram(
            f"🔥 <b>Новая бронь</b>\n\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"👥 {guests} чел.\n"
            f"🪑 Стол {table}\n"
            f"📅 {date}\n"
            f"⏰ {time}\n"
            f"🆔 ID: {booking.id}"
        )

        return {"ok": True, "id": booking.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# =====================
# ГОСТЬ УШЕЛ (СМЕНА СТАТУСА)
# =====================

@app.post("/done/{id}")
def done(id: int):
    db = SessionLocal()

    try:
        booking = db.query(Booking).filter(
            Booking.id == id
        ).first()

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        booking.status = "completed"
        db.commit()

        send_telegram(
            f"✅ <b>Гость ушел</b>\n\n"
            f"🆔 ID: {id}\n"
            f"👤 {booking.name}\n"
            f"🪑 Стол {booking.table}\n"
            f"📅 {booking.date} {booking.time}"
        )

        return {"ok": True, "message": "Booking completed"}

    except HTTPException:
        raise
    finally:
        db.close()

# =====================
# ОТМЕНА БРОНИ
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
            raise HTTPException(status_code=404, detail="Active booking not found")

        booking.status = "cancelled"
        db.commit()

        send_telegram(
            f"❌ <b>Бронь отменена</b>\n\n"
            f"🆔 ID: {id}\n"
            f"👤 {booking.name}\n"
            f"🪑 Стол {booking.table}\n"
            f"📅 {booking.date} {booking.time}"
        )

        return {"ok": True, "message": "Booking cancelled"}

    except HTTPException:
        raise
    finally:
        db.close()
