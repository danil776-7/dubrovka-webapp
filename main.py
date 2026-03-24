from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import requests
import os
import threading
import time

# =====================
# DATABASE
# =====================

DATABASE_URL = "postgresql://postgres:YOhOreaGeQiTXNqnHsUACbozGqnVlQcb@postgres.railway.internal:5432/railway"

print(f"✅ Connecting to database...")

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
    user_id = Column(String, nullable=True)

# Создаем таблицы
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    raise

# =====================
# APP
# =====================

app = FastAPI()

# 🔥 ПРАВИЛЬНАЯ НАСТРОЙКА CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dani1776-7.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "*"  # временно для теста
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# =====================
# OPTIONS обработчик
# =====================

@app.options("/{path:path}")
async def options_handler(path: str):
    return JSONResponse(
        status_code=200,
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# =====================
# CONFIG
# =====================

TELEGRAM_BOT_TOKEN = "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves"
ADMIN_CHAT_ID = "7545540622"
TWO_GIS_REVIEW_URL = "https://2gis.ru/novokuznetsk/review/70000001067987554"

print(f"✅ Telegram configured for admin: {ADMIN_CHAT_ID}")

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
# ХРАНИЛИЩЕ ДЛЯ ТАЙМЕРОВ
# =====================

booking_timers = {}
reminder_timers = {}

# =====================
# ФУНКЦИИ УВЕДОМЛЕНИЙ
# =====================

def send_to_guest(user_id, text):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": user_id,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error sending to guest: {e}")
        return False

def send_telegram(text):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Telegram sent to admin")
    except Exception as e:
        print("❌ TG ERROR:", e)

# =====================
# HELPERS
# =====================

def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        raise HTTPException(status_code=400, detail="Invalid date. Use YYYY-MM-DD")

# =====================
# ROOT
# =====================

@app.get("/")
def root():
    return {
        "status": "ok", 
        "database": "connected",
        "telegram": "configured"
    }

# =====================
# HEALTH CHECK
# =====================

@app.get("/health")
def health():
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# =====================
# БРОНИ ПО ДАТЕ
# =====================

@app.get("/bookings_by_date")
def bookings_by_date(date: str):
    db = SessionLocal()
    try:
        print(f"📅 Запрос броней на дату: {date}")
        date = normalize_date(date)
        
        data = db.query(Booking).filter(
            Booking.date == date,
            Booking.status == "active"
        ).all()
        
        print(f"✅ Найдено броней: {len(data)}")
        
        result = [
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
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка в bookings_by_date: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# =====================
# ЗАНЯТЫЕ ВРЕМЕНА
# =====================

@app.get("/busy_times")
def busy_times(date: str, table: str):
    db = SessionLocal()
    try:
        print(f"🔍 Запрос занятых времен: date={date}, table={table}")
        date = normalize_date(date)
        
        data = db.query(Booking).filter(
            Booking.date == date,
            Booking.table == table,
            Booking.status == "active"
        ).all()
        
        result = [b.time for b in data]
        print(f"✅ Занятые времена: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка в busy_times: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# =====================
# СОЗДАНИЕ БРОНИ
# =====================

@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()
    try:
        print(f"📝 Создание брони: {data}")
        
        required = ["name", "phone", "guests", "table", "date", "time"]
        for field in required:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")

        date = normalize_date(data["date"])
        table = str(data["table"])
        time = data["time"]
        guests = int(data["guests"])
        user_id = str(data.get("user_id", ""))

        if table not in TABLE_LIMITS:
            raise HTTPException(status_code=400, detail=f"Table {table} does not exist")

        if guests > TABLE_LIMITS[table]:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many guests. Max for table {table} is {TABLE_LIMITS[table]}"
            )

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
            status="active",
            user_id=user_id if user_id else None
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        print(f"✅ Новая бронь: ID={booking.id}, Table={table}, Time={time}")

        send_telegram(
            f"🔥 <b>НОВАЯ БРОНЬ!</b>\n\n"
            f"🆔 <b>ID:</b> {booking.id}\n"
            f"👤 <b>Имя:</b> {data['name']}\n"
            f"📞 <b>Телефон:</b> {data['phone']}\n"
            f"👥 <b>Гостей:</b> {guests}\n"
            f"🪑 <b>Стол:</b> {table}\n"
            f"📅 <b>Дата:</b> {date}\n"
            f"⏰ <b>Время:</b> {time}"
        )

        return {"ok": True, "id": booking.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания брони: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# =====================
# ГОСТЬ УШЕЛ
# =====================

@app.post("/done/{id}")
def done(id: int):
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(
            Booking.id == id,
            Booking.status == "active"
        ).first()

        if not booking:
            raise HTTPException(status_code=404, detail="Active booking not found")

        booking.status = "completed"
        db.commit()

        print(f"✅ Бронь {id} завершена")

        send_telegram(
            f"✅ <b>ГОСТЬ УШЕЛ</b>\n\n"
            f"🆔 <b>ID:</b> {id}\n"
            f"👤 <b>Имя:</b> {booking.name}\n"
            f"🪑 <b>Стол:</b> {booking.table}\n"
            f"📅 <b>Дата:</b> {booking.date}\n"
            f"⏰ <b>Время:</b> {booking.time}"
        )
        
        # Отправляем благодарность гостю
        if booking.user_id:
            thank_message = (
                f"🌟 <b>Спасибо, что посетили Dubrovka!</b>\n\n"
                f"{booking.name}, мы благодарим вас за визит!\n\n"
                f"📝 Оставьте отзыв: {TWO_GIS_REVIEW_URL}"
            )
            send_to_guest(booking.user_id, thank_message)

        return {"ok": True, "message": "Booking completed"}

    except HTTPException:
        raise
    finally:
        db.close()

# =====================
# ВСЕ БРОНИ
# =====================

@app.get("/all_bookings")
def all_bookings():
    db = SessionLocal()
    try:
        data = db.query(Booking).all()
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
