from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
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
# MODEL (без chat_id)
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
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    raise

# =====================
# APP
# =====================

app = FastAPI()

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://danil776-7.github.io",
        "https://dani1776-7.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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

print(f"✅ Telegram configured")

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

reminder_timers = {}
completion_timers = {}

# =====================
# ФУНКЦИИ
# =====================

def send_telegram_to_admin(text):
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
            print("✅ Уведомление отправлено админу")
    except Exception as e:
        print("❌ Ошибка:", e)

def send_reminder_to_admin(booking):
    """Отправка напоминания админу (вместо гостя)"""
    message = (
        f"🔔 <b>НАПОМИНАНИЕ О БРОНИ!</b>\n\n"
        f"🪑 <b>Стол:</b> {booking.table}\n"
        f"📅 <b>Сегодня:</b> {booking.date}\n"
        f"⏰ <b>Через 30 минут:</b> {booking.time}\n\n"
        f"👤 <b>Гость:</b> {booking.name}\n"
        f"📞 <b>Телефон:</b> {booking.phone}\n"
        f"👥 <b>Гостей:</b> {booking.guests}\n\n"
        f"📍 <b>Адрес:</b> Ермакова 11\n"
        f"📞 <b>Телефон:</b> +7‒913‒432‒01‒01"
    )
    send_telegram_to_admin(message)
    print(f"⏰ Напоминание отправлено админу для брони {booking.id}")

def send_thank_you_to_admin(booking):
    """Отправка благодарности админу (вместо гостя)"""
    message = (
        f"✅ <b>ГОСТЬ ПОСЕТИЛ</b>\n\n"
        f"🆔 ID: {booking.id}\n"
        f"👤 {booking.name}\n"
        f"📞 {booking.phone}\n"
        f"🪑 Стол {booking.table}\n"
        f"👥 {booking.guests} чел.\n"
        f"📅 {booking.date} {booking.time}\n\n"
        f"🔗 <b>Ссылка на отзыв в 2ГИС:</b>\n"
        f"{TWO_GIS_REVIEW_URL}"
    )
    send_telegram_to_admin(message)

def schedule_reminder(booking):
    try:
        booking_datetime = datetime.strptime(f"{booking.date} {booking.time}", "%Y-%m-%d %H:%M")
        reminder_time = booking_datetime - timedelta(minutes=30)
        now = datetime.now()
        
        if reminder_time > now:
            delay = (reminder_time - now).total_seconds()
            timer = threading.Timer(delay, send_reminder_to_admin, args=[booking])
            timer.daemon = True
            timer.start()
            reminder_timers[booking.id] = timer
            print(f"⏰ Напоминание запланировано на {reminder_time}")
    except Exception as e:
        print(f"❌ Ошибка планирования: {e}")

def schedule_auto_complete(booking):
    try:
        timer = threading.Timer(4 * 3600, auto_complete_booking, args=[booking.id])
        timer.daemon = True
        timer.start()
        completion_timers[booking.id] = timer
        print(f"🤖 Авто-завершение через 4 часа для брони {booking.id}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def auto_complete_booking(booking_id):
    try:
        time.sleep(4 * 3600)
        db = SessionLocal()
        booking = db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.status == "active"
        ).first()
        
        if booking:
            booking.status = "completed"
            db.commit()
            print(f"🤖 Авто-завершение брони {booking_id}")
            
            send_telegram_to_admin(
                f"🤖 <b>АВТО-ЗАВЕРШЕНИЕ</b>\n\n"
                f"🆔 ID: {booking_id}\n"
                f"👤 {booking.name}\n"
                f"🪑 Стол {booking.table}\n"
                f"📅 {booking.date} {booking.time}"
            )
            
        db.close()
    except Exception as e:
        print(f"Ошибка авто-завершения: {e}")
    finally:
        if booking_id in completion_timers:
            del completion_timers[booking_id]

# =====================
# HELPERS
# =====================

def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        raise HTTPException(status_code=400, detail="Invalid date")

# =====================
# ЭНДПОИНТЫ
# =====================

@app.get("/")
def root():
    return {"status": "ok", "database": "connected"}

@app.get("/health")
def health():
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

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
        print(f"❌ Ошибка в bookings_by_date: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

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
            status="active"
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        # Планируем напоминание за 30 минут
        schedule_reminder(booking)
        
        # Планируем авто-завершение через 4 часа
        schedule_auto_complete(booking)

        print(f"✅ Новая бронь: ID={booking.id}")

        send_telegram_to_admin(
            f"🔥 <b>НОВАЯ БРОНЬ!</b>\n\n"
            f"🆔 ID: {booking.id}\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"👥 {guests}\n"
            f"🪑 Стол {table}\n"
            f"📅 {date}\n"
            f"⏰ {time}"
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

        # Останавливаем таймеры
        if id in reminder_timers:
            reminder_timers[id].cancel()
            del reminder_timers[id]
        if id in completion_timers:
            completion_timers[id].cancel()
            del completion_timers[id]

        print(f"✅ Бронь {id} завершена")

        send_telegram_to_admin(
            f"✅ <b>ГОСТЬ УШЕЛ</b>\n\n"
            f"🆔 ID: {id}\n"
            f"👤 {booking.name}\n"
            f"📞 {booking.phone}\n"
            f"🪑 Стол {booking.table}\n"
            f"👥 {booking.guests} чел.\n"
            f"📅 {booking.date} {booking.time}\n\n"
            f"🔗 <b>Ссылка на отзыв для гостя:</b>\n"
            f"{TWO_GIS_REVIEW_URL}"
        )

        return {"ok": True, "message": "Booking completed"}

    except HTTPException:
        raise
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
            raise HTTPException(status_code=404, detail="Active booking not found")

        booking.status = "cancelled"
        db.commit()

        if id in reminder_timers:
            reminder_timers[id].cancel()
            del reminder_timers[id]
        if id in completion_timers:
            completion_timers[id].cancel()
            del completion_timers[id]

        print(f"❌ Бронь {id} отменена")

        send_telegram_to_admin(
            f"❌ <b>БРОНЬ ОТМЕНЕНА</b>\n\n"
            f"🆔 ID: {id}\n"
            f"👤 {booking.name}\n"
            f"📞 {booking.phone}\n"
            f"🪑 Стол {booking.table}\n"
            f"📅 {booking.date} {booking.time}"
        )

        return {"ok": True, "message": "Booking cancelled"}

    except HTTPException:
        raise
    finally:
        db.close()

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
