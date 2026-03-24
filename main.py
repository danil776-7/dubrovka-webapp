from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import requests
import os
import threading
import time

# =====================
# DATABASE - НОВАЯ ССЫЛКА
# =====================

# 🔥 НОВАЯ ССЫЛКА НА POSTGRESQL
DATABASE_URL = "postgresql://postgres:YOhOreaGeQiTXNqnHsUACbozGqnVlQcb@postgres.railway.internal:5432/railway"

print(f"✅ Connecting to database...")

# Создаем engine
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# CONFIG - ВАШИ ДАННЫЕ ТЕЛЕГРАМ
# =====================

# 🔥 ВАШ ТОКЕН ТЕЛЕГРАМ БОТА
TELEGRAM_BOT_TOKEN = "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves"

# 🔥 ВАШ ID АДМИНА
ADMIN_CHAT_ID = "7545540622"

print(f"✅ Telegram configured for admin: {ADMIN_CHAT_ID}")

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
# ХРАНИЛИЩЕ ДЛЯ ТАЙМЕРОВ
# =====================

booking_timers = {}

def auto_complete_booking(booking_id):
    """Автоматическое завершение брони через 4 часа"""
    try:
        time.sleep(4 * 3600)  # 4 часа
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
                f"🆔 <b>ID брони:</b> {booking_id}\n"
                f"👤 <b>Имя:</b> {booking.name}\n"
                f"🪑 <b>Стол:</b> {booking.table}\n"
                f"📅 <b>Дата:</b> {booking.date}\n"
                f"⏰ <b>Время:</b> {booking.time}\n\n"
                f"🔓 Стол {booking.table} на {booking.time} теперь доступен для бронирования!"
            )
        db.close()
    except Exception as e:
        print(f"Error in auto_complete: {e}")
    finally:
        if booking_id in booking_timers:
            del booking_timers[booking_id]

def start_auto_complete_timer(booking_id):
    """Запуск таймера в отдельном потоке"""
    timer_thread = threading.Thread(target=auto_complete_booking, args=(booking_id,))
    timer_thread.daemon = True
    timer_thread.start()
    booking_timers[booking_id] = timer_thread

# =====================
# TELEGRAM
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
            print("✅ Telegram notification sent")
        else:
            print(f"❌ Telegram error: {response.status_code}")
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

        # Проверка стола
        if table not in TABLE_LIMITS:
            raise HTTPException(status_code=400, detail=f"Table {table} does not exist")

        # Лимит гостей
        if guests > TABLE_LIMITS[table]:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many guests. Max for table {table} is {TABLE_LIMITS[table]}"
            )

        # Проверка занятости
        exists = db.query(Booking).filter(
            Booking.date == date,
            Booking.time == time,
            Booking.table == table,
            Booking.status == "active"
        ).first()

        if exists:
            raise HTTPException(status_code=409, detail="Time slot already booked")

        # Создание брони
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

        # Запускаем таймер автоматического завершения через 4 часа
        start_auto_complete_timer(booking.id)

        print(f"✅ New booking created: ID={booking.id}, Table={table}, Time={time}, Guest={data['name']}")

        # Telegram уведомление
        send_telegram(
            f"🔥 <b>НОВАЯ БРОНЬ!</b>\n\n"
            f"👤 <b>Имя:</b> {data['name']}\n"
            f"📞 <b>Телефон:</b> {data['phone']}\n"
            f"👥 <b>Гостей:</b> {guests}\n"
            f"🪑 <b>Стол:</b> {table}\n"
            f"📅 <b>Дата:</b> {date}\n"
            f"⏰ <b>Время:</b> {time}\n"
            f"🆔 <b>ID брони:</b> {booking.id}\n\n"
            f"⏰ Бронь автоматически завершится через 4 часа"
        )

        return {"ok": True, "id": booking.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating booking: {e}")
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

        # Останавливаем таймер если он есть
        if id in booking_timers:
            # Таймер уже запущен в отдельном потоке, мы его не можем остановить
            # Просто удаляем из словаря, чтобы не дублировать
            del booking_timers[id]

        print(f"✅ Booking {id} marked as completed")

        send_telegram(
            f"✅ <b>ГОСТЬ УШЕЛ</b>\n\n"
            f"🆔 <b>ID брони:</b> {id}\n"
            f"👤 <b>Имя:</b> {booking.name}\n"
            f"🪑 <b>Стол:</b> {booking.table}\n"
            f"📅 <b>Дата:</b> {booking.date}\n"
            f"⏰ <b>Время:</b> {booking.time}\n"
            f"👥 <b>Было гостей:</b> {booking.guests}\n\n"
            f"🔓 Стол {booking.table} на {booking.time} теперь доступен для бронирования!"
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

        # Останавливаем таймер если он есть
        if id in booking_timers:
            del booking_timers[id]

        print(f"❌ Booking {id} cancelled")

        send_telegram(
            f"❌ <b>БРОНЬ ОТМЕНЕНА</b>\n\n"
            f"🆔 <b>ID брони:</b> {id}\n"
            f"👤 <b>Имя:</b> {booking.name}\n"
            f"📞 <b>Телефон:</b> {booking.phone}\n"
            f"🪑 <b>Стол:</b> {booking.table}\n"
            f"📅 <b>Дата:</b> {booking.date}\n"
            f"⏰ <b>Время:</b> {booking.time}\n\n"
            f"🔓 Стол {booking.table} на {booking.time} теперь доступен для бронирования!"
        )

        return {"ok": True, "message": "Booking cancelled"}

    except HTTPException:
        raise
    finally:
        db.close()

# =====================
# ВСЕ БРОНИ (ДЛЯ ОТЛАДКИ)
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
