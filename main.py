from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
import requests
import os
import threading
import time

# =====================
# APP
# =====================

app = FastAPI()

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
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# DATABASE
# =====================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found!")
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/railway"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
    name = Column(String(100))
    phone = Column(String(20))
    guests = Column(Integer)
    table = Column(String(10))
    date = Column(String(10))
    time = Column(String(5))
    status = Column(String(20), default="active")
    chat_id = Column(String(50), nullable=True)

# 🔥 ПРИНУДИТЕЛЬНОЕ ДОБАВЛЕНИЕ КОЛОНКИ chat_id
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='bookings' AND column_name='chat_id'
        """))
        if result.fetchone() is None:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN chat_id VARCHAR(50)"))
            conn.commit()
            print("✅ Добавлена колонка chat_id")
        else:
            print("✅ Колонка chat_id уже существует")
except Exception as e:
    print(f"⚠️ Ошибка при проверке колонки: {e}")

# Создаем таблицы
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Error creating tables: {e}")

# =====================
# CONFIG
# =====================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves")

# 👇👇👇 СПИСОК ID АДМИНОВ 👇👇👇
# Добавьте сюда всех админов, которым нужно отправлять уведомления
ADMIN_CHAT_IDS = [
    "7545540622",  # Первый админ
    "81239213"    # Второй админ (добавлен)
]

TWO_GIS_REVIEW_URL = "https://2gis.ru/novokuznetsk/review/70000001067987554"

print(f"✅ Telegram configured")
print(f"👥 Админы для уведомлений: {ADMIN_CHAT_IDS}")

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
# ФУНКЦИИ ОТПРАВКИ СООБЩЕНИЙ
# =====================

def send_telegram_to_user(chat_id, text):
    if not chat_id or chat_id == "" or chat_id == "0" or chat_id == "None":
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка отправки пользователю: {e}")
        return False

def send_telegram_to_admins(text):
    """Отправляет сообщение ВСЕМ админам из списка ADMIN_CHAT_IDS"""
    success_count = 0
    for admin_id in ADMIN_CHAT_IDS:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": admin_id, "text": text, "parse_mode": "HTML"},
                timeout=5
            )
            if response.status_code == 200:
                success_count += 1
                print(f"✅ Уведомление отправлено админу {admin_id}")
            else:
                print(f"❌ Ошибка отправки админу {admin_id}: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка отправки админу {admin_id}: {e}")
    return success_count

def send_booking_confirmation(booking):
    message = (
        f"✅ <b>БРОНЬ ПОДТВЕРЖДЕНА!</b>\n\n"
        f"🆔 <b>ID:</b> {booking.id}\n"
        f"👤 <b>Имя:</b> {booking.name}\n"
        f"🪑 <b>Стол:</b> {booking.table}\n"
        f"👥 <b>Гостей:</b> {booking.guests}\n"
        f"📅 <b>Дата:</b> {booking.date}\n"
        f"⏰ <b>Время:</b> {booking.time}\n\n"
        f"📍 <b>Адрес:</b> Ермакова 11\n"
        f"📞 <b>Телефон:</b> +7‒913‒432‒01‒01\n\n"
        f"❤️ Ждем вас!"
    )
    if booking.chat_id:
        send_telegram_to_user(booking.chat_id, message)

def send_reminder_to_guest(booking):
    message = (
        f"🔔 <b>НАПОМИНАНИЕ О БРОНИ!</b>\n\n"
        f"🪑 Стол {booking.table}\n"
        f"📅 {booking.date}\n"
        f"⏰ Через 30 минут: {booking.time}\n\n"
        f"📍 Ермакова 11\n"
        f"📞 +7‒913‒432‒01‒01"
    )
    if booking.chat_id:
        send_telegram_to_user(booking.chat_id, message)

def schedule_reminder(booking):
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
            print(f"⏰ Напоминание запланировано на {reminder_time}")
    except Exception as e:
        print(f"❌ Ошибка планирования напоминания: {e}")

def schedule_auto_complete(booking):
    try:
        timer = threading.Timer(4 * 3600, auto_complete_booking, args=[booking.id])
        timer.daemon = True
        timer.start()
        completion_timers[booking.id] = timer
        print(f"🤖 Авто-завершение через 4 часа")
    except Exception as e:
        print(f"❌ Ошибка планирования авто-завершения: {e}")

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
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

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
        print(f"📝 Создание брони: {data}")
        
        required = ["name", "phone", "guests", "table", "date", "time"]
        for field in required:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")

        date = normalize_date(data["date"])
        table = str(data["table"])
        time = data["time"]
        guests = int(data["guests"])
        chat_id = str(data.get("chat_id", ""))

        if table not in TABLE_LIMITS:
            raise HTTPException(status_code=400, detail=f"Table {table} does not exist")

        if guests > TABLE_LIMITS[table]:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many guests. Max for table {table} is {TABLE_LIMITS[table]}"
            )

        # Проверяем, занято ли время
        exists = db.query(Booking).filter(
            Booking.date == date,
            Booking.time == time,
            Booking.table == table,
            Booking.status == "active"
        ).first()

        if exists:
            raise HTTPException(status_code=409, detail="Time slot already booked")

        # Создаём бронь
        booking = Booking(
            name=data["name"],
            phone=data["phone"],
            guests=guests,
            table=table,
            date=date,
            time=time,
            status="active",
            chat_id=chat_id if chat_id and chat_id != "0" and chat_id != "None" else None
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        print(f"✅ Бронь создана: ID={booking.id}, chat_id={booking.chat_id}")

        # Отправляем подтверждение гостю
        send_booking_confirmation(booking)
        
        # Планируем напоминание
        schedule_reminder(booking)
        
        # Планируем авто-завершение
        schedule_auto_complete(booking)

        # 👇👇👇 Уведомление ВСЕМ админам 👇👇👇
        admin_message = (
            f"🔥 <b>НОВАЯ БРОНЬ!</b>\n\n"
            f"🆔 ID: {booking.id}\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"👥 {guests}\n"
            f"🪑 Стол {table}\n"
            f"📅 {date}\n"
            f"⏰ {time}\n\n"
            f"📌 <a href='https://t.me/c/--/message'>Открыть в админке</a>"
        )
        send_telegram_to_admins(admin_message)

        return {"ok": True, "id": booking.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
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

        if id in reminder_timers:
            reminder_timers[id].cancel()
            del reminder_timers[id]
        if id in completion_timers:
            completion_timers[id].cancel()
            del completion_timers[id]

        print(f"✅ Бронь {id} завершена")

        # 👇👇👇 Уведомление ВСЕМ админам о завершении 👇👇👇
        admin_message = (
            f"✅ <b>ГОСТЬ УШЕЛ</b>\n\n"
            f"🆔 ID: {id}\n"
            f"👤 {booking.name}\n"
            f"🪑 Стол {booking.table}\n"
            f"📅 {booking.date} {booking.time}"
        )
        send_telegram_to_admins(admin_message)

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

        if booking.chat_id:
            cancel_message = (
                f"❌ <b>Бронь отменена</b>\n\n"
                f"{booking.name}, ваша бронь отменена.\n\n"
                f"📞 +7‒913‒432‒01‒01"
            )
            send_telegram_to_user(booking.chat_id, cancel_message)

        # 👇👇👇 Уведомление ВСЕМ админам об отмене 👇👇👇
        admin_message = (
            f"❌ <b>БРОНЬ ОТМЕНЕНА</b>\n\n"
            f"🆔 ID: {id}\n"
            f"👤 {booking.name}\n"
            f"🪑 Стол {booking.table}\n"
            f"📅 {booking.date} {booking.time}"
        )
        send_telegram_to_admins(admin_message)

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
# ДОПОЛНИТЕЛЬНЫЙ ЭНДПОИНТ ДЛЯ ПРОВЕРКИ АДМИНОВ
# =====================

@app.get("/admins")
def get_admins():
    """Возвращает список ID админов (для проверки)"""
    return {"admins": ADMIN_CHAT_IDS, "count": len(ADMIN_CHAT_IDS)}
