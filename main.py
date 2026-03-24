from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# 🔥 ПРАВИЛЬНЫЕ CORS НАСТРОЙКИ - ДОБАВЛЯЕМ ВАШ GitHub PAGES
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Разрешаем все для теста
        "https://danil776-7.github.io",
        "https://danil776-7.github.io/*",
        "http://localhost:3000",
        "http://localhost:5500",
        "https://dubrovka-webapp-production-a00c.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
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
    """Отправка сообщения гостю по user_id"""
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
        if response.status_code == 200:
            print(f"✅ Message sent to guest {user_id}")
            return True
        return False
    except Exception as e:
        print(f"❌ Error sending to guest: {e}")
        return False

def send_booking_confirmation(booking):
    """Отправка подтверждения брони гостю"""
    try:
        message = (
            f"✅ <b>БРОНЬ ПОДТВЕРЖДЕНА!</b>\n\n"
            f"🆔 <b>ID брони:</b> {booking.id}\n"
            f"👤 <b>Имя:</b> {booking.name}\n"
            f"🪑 <b>Стол:</b> {booking.table}\n"
            f"👥 <b>Гостей:</b> {booking.guests}\n"
            f"📅 <b>Дата:</b> {booking.date}\n"
            f"⏰ <b>Время:</b> {booking.time}\n\n"
            f"🔔 <b>Напоминание:</b> Мы пришлем вам уведомление за 30 минут до брони.\n\n"
            f"📍 <b>Адрес:</b> Ермакова 11, Новокузнецк\n"
            f"📞 <b>Телефон:</b> +7‒913‒432‒01‒01\n\n"
            f"❤️ Ждем вас в Dubrovka!"
        )
        if booking.user_id:
            send_to_guest(booking.user_id, message)
            print(f"📱 Booking confirmation sent to {booking.name}")
    except Exception as e:
        print(f"❌ Error sending confirmation: {e}")

def send_reminder_to_guest(booking):
    """Отправка напоминания за 30 минут до брони"""
    try:
        message = (
            f"🔔 <b>НАПОМИНАНИЕ О БРОНИ!</b>\n\n"
            f"🪑 <b>Стол:</b> {booking.table}\n"
            f"📅 <b>Сегодня:</b> {booking.date}\n"
            f"⏰ <b>Через 30 минут:</b> {booking.time}\n\n"
            f"👤 <b>На имя:</b> {booking.name}\n"
            f"👥 <b>Гостей:</b> {booking.guests}\n\n"
            f"📍 <b>Ждем вас по адресу:</b> Ермакова 11\n"
            f"📞 <b>По вопросам:</b> +7‒913‒432‒01‒01\n\n"
            f"🌟 Пожалуйста, не опаздывайте!"
        )
        if booking.user_id:
            send_to_guest(booking.user_id, message)
            print(f"⏰ Reminder sent to {booking.name}")
    except Exception as e:
        print(f"❌ Error sending reminder: {e}")

def send_thank_you_message(booking):
    """Отправка благодарности после посещения"""
    try:
        message = (
            f"🌟 <b>Спасибо, что посетили Dubrovka Lounge & Bar!</b> 🌟\n\n"
            f"👤 <b>{booking.name}</b>, мы благодарим вас за визит!\n\n"
            f"🍷 Надеемся, вам понравилась атмосфера, обслуживание и кухня.\n\n"
            f"📝 <b>Пожалуйста, оставьте отзыв о нашем заведении в 2ГИС</b>\n"
            f"Ваше мнение очень важно для нас!\n\n"
            f"🔗 <a href='{TWO_GIS_REVIEW_URL}'>Написать отзыв в 2ГИС</a>\n\n"
            f"❤️ Ждем вас снова в Dubrovka!"
        )
        if booking.user_id:
            send_to_guest(booking.user_id, message)
            print(f"📱 Thank you message sent to {booking.name}")
    except Exception as e:
        print(f"❌ Error sending thank you: {e}")

def schedule_reminder(booking):
    """Запланировать напоминание за 30 минут до брони"""
    try:
        booking_datetime = datetime.strptime(f"{booking.date} {booking.time}", "%Y-%m-%d %H:%M")
        reminder_time = booking_datetime - timedelta(minutes=30)
        now = datetime.now()
        
        if reminder_time > now:
            delay = (reminder_time - now).total_seconds()
            timer = threading.Timer(delay, send_reminder_to_guest, args=[booking])
            timer.daemon = True
            timer.start()
            reminder_timers[booking.id] = timer
            print(f"⏰ Reminder scheduled for {reminder_time}")
    except Exception as e:
        print(f"❌ Error scheduling reminder: {e}")

def auto_complete_booking(booking_id):
    """Автоматическое завершение брони через 4 часа"""
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
            print(f"🤖 Auto-completed booking {booking_id}")
            
            send_telegram(
                f"🤖 <b>АВТОМАТИЧЕСКОЕ ЗАВЕРШЕНИЕ</b>\n\n"
                f"🆔 ID: {booking_id}\n"
                f"👤 {booking.name}\n"
                f"🪑 Стол {booking.table}\n"
                f"📅 {booking.date} {booking.time}\n\n"
                f"🔓 Стол {booking.table} теперь доступен!"
            )
            send_thank_you_message(booking)
        db.close()
    except Exception as e:
        print(f"Error in auto_complete: {e}")
    finally:
        if booking_id in booking_timers:
            del booking_timers[booking_id]

def start_auto_complete_timer(booking_id):
    timer_thread = threading.Thread(target=auto_complete_booking, args=(booking_id,))
    timer_thread.daemon = True
    timer_thread.start()
    booking_timers[booking_id] = timer_thread

# =====================
# TELEGRAM ДЛЯ АДМИНА
# =====================

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
        raise HTTPException(status_code=400, detail="Invalid date")

# =====================
# ENDPOINTS
# =====================

@app.get("/")
def root():
    return {"status": "ok", "database": "connected", "telegram": "configured"}

@app.get("/health")
def health():
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

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
            raise HTTPException(status_code=400, detail=f"Too many guests. Max is {TABLE_LIMITS[table]}")

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

        start_auto_complete_timer(booking.id)
        schedule_reminder(booking)
        send_booking_confirmation(booking)

        send_telegram(
            f"🔥 <b>НОВАЯ БРОНЬ!</b>\n\n"
            f"🆔 ID: {booking.id}\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"👥 {guests} чел.\n"
            f"🪑 Стол {table}\n"
            f"📅 {date}\n"
            f"⏰ {time}"
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

@app.post("/done/{id}")
def done(id: int):
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(
            Booking.id == id,
            Booking.status == "active"
        ).first()

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        booking.status = "completed"
        db.commit()

        if id in booking_timers:
            del booking_timers[id]
        if id in reminder_timers:
            del reminder_timers[id]

        send_telegram(
            f"✅ <b>ГОСТЬ УШЕЛ</b>\n\n"
            f"🆔 ID: {id}\n"
            f"👤 {booking.name}\n"
            f"🪑 Стол {booking.table}\n"
            f"📅 {booking.date} {booking.time}\n\n"
            f"🔓 Стол {booking.table} теперь доступен!"
        )
        
        send_thank_you_message(booking)

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
            raise HTTPException(status_code=404, detail="Booking not found")

        booking.status = "cancelled"
        db.commit()

        if id in booking_timers:
            del booking_timers[id]
        if id in reminder_timers:
            del reminder_timers[id]

        send_telegram(
            f"❌ <b>БРОНЬ ОТМЕНЕНА</b>\n\n"
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

# =====================
# OPTIONS - для CORS preflight
# =====================

@app.options("/{path:path}")
async def options_handler(path: str):
    return {}
