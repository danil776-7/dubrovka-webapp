from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
import requests
import os
import threading
import time
import re
import secrets
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# =====================
# ЛОГИРОВАНИЕ
# =====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================
# RATE LIMITING
# =====================

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# =====================
# SECURITY
# =====================

# Генерация API ключа для админки (установите через переменную окружения)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", secrets.token_urlsafe(32))
security = HTTPBearer(auto_error=False)

# Список заблокированных IP (можно расширить)
BLOCKED_IPS = set(os.getenv("BLOCKED_IPS", "").split(","))

# Регулярные выражения для валидации
PHONE_PATTERN = re.compile(r'^\+7\d{10}$')
NAME_PATTERN = re.compile(r'^[а-яА-Яa-zA-Z\s-]{2,50}$')
TIME_PATTERN = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# =====================
# MIDDLEWARE ЗАЩИТЫ
# =====================

# HTTPS принудительно
app.add_middleware(HTTPSRedirectMiddleware)

# CORS с ограничениями
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://danil776-7.github.io",
        "https://dani1776-7.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    expose_headers=["*"],
    max_age=3600,
)

# =====================
# ФУНКЦИЯ ПРОВЕРКИ IP
# =====================

async def check_ip(request: Request):
    client_ip = request.client.host
    if client_ip in BLOCKED_IPS:
        logger.warning(f"Blocked IP attempt: {client_ip}")
        raise HTTPException(status_code=403, detail="Access denied")
    return client_ip

# =====================
# АУТЕНТИФИКАЦИЯ АДМИНКИ
# =====================

async def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")
    if credentials.credentials != ADMIN_API_KEY:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

# =====================
# DATABASE
# =====================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:YOhOreaGeQiTXNqnHsUACbozGqnVlQcb@postgres.railway.internal:5432/railway")

print(f"✅ Connecting to database...")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    connect_args={"connect_timeout": 10}
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
    chat_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(String, nullable=True)

# Создаем таблицы
try:
    with engine.connect() as conn:
        # Добавляем новые колонки если их нет
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN ip_address VARCHAR"))
            conn.commit()
            print("✅ Добавлена колонка ip_address")
        except Exception as e:
            if "already exists" not in str(e):
                print(f"⚠️ {e}")
        
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN created_at VARCHAR"))
            conn.commit()
            print("✅ Добавлена колонка created_at")
        except Exception as e:
            if "already exists" not in str(e):
                print(f"⚠️ {e}")
        
        try:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='bookings' AND column_name='chat_id'
            """))
            if result.fetchone() is None:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN chat_id VARCHAR"))
                conn.commit()
                print("✅ Добавлена колонка chat_id")
        except Exception as e:
            print(f"⚠️ {e}")
    
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    raise

# =====================
# CONFIG
# =====================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "7545540622")
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
# ФУНКЦИИ ВАЛИДАЦИИ
# =====================

def validate_phone(phone: str) -> bool:
    """Проверка номера телефона"""
    return bool(PHONE_PATTERN.match(phone))

def validate_name(name: str) -> bool:
    """Проверка имени"""
    return bool(NAME_PATTERN.match(name))

def validate_time(time_str: str) -> bool:
    """Проверка времени"""
    return bool(TIME_PATTERN.match(time_str))

def validate_date(date_str: str) -> bool:
    """Проверка даты"""
    return bool(DATE_PATTERN.match(date_str))

def validate_guests(guests: int, table: str) -> tuple:
    """Проверка количества гостей"""
    max_guests = TABLE_LIMITS.get(table, 5)
    if guests < 1:
        return False, "Минимум 1 гость"
    if guests > max_guests:
        return False, f"Максимум {max_guests} гостей для стола {table}"
    return True, ""

# =====================
# ФУНКЦИИ ОТПРАВКИ СООБЩЕНИЙ
# =====================

def send_telegram_to_user(chat_id, text):
    """Отправка сообщения пользователю (гостю)"""
    if not chat_id or chat_id == "" or chat_id == "0" or chat_id == "None":
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        if response.status_code == 200:
            logger.info(f"✅ Сообщение отправлено гостю {chat_id}")
            return True
        else:
            logger.error(f"❌ Ошибка отправки: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return False

def send_telegram_to_admin(text):
    """Отправка уведомления админу"""
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
            logger.info("✅ Уведомление отправлено админу")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

def send_booking_confirmation(booking):
    """Подтверждение брони гостю"""
    message = (
        f"✅ <b>БРОНЬ ПОДТВЕРЖДЕНА!</b>\n\n"
        f"🆔 <b>ID брони:</b> {booking.id}\n"
        f"👤 <b>Имя:</b> {booking.name}\n"
        f"🪑 <b>Стол:</b> {booking.table}\n"
        f"👥 <b>Гостей:</b> {booking.guests}\n"
        f"📅 <b>Дата:</b> {booking.date}\n"
        f"⏰ <b>Время:</b> {booking.time}\n\n"
        f"🔔 <b>Напоминание:</b> Мы пришлем уведомление за 30 минут до брони.\n\n"
        f"📍 <b>Адрес:</b> Ермакова 11, Новокузнецк\n"
        f"📞 <b>Телефон:</b> +7‒913‒432‒01‒01\n\n"
        f"❤️ Ждем вас в Dubrovka!"
    )
    if booking.chat_id:
        send_telegram_to_user(booking.chat_id, message)

def send_reminder_to_guest(booking):
    """Напоминание гостю за 30 минут"""
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
    if booking.chat_id:
        send_telegram_to_user(booking.chat_id, message)
        logger.info(f"⏰ Напоминание отправлено гостю для брони {booking.id}")
    else:
        send_telegram_to_admin(
            f"🔔 <b>НАПОМИНАНИЕ (позвонить гостю)</b>\n\n"
            f"🪑 Стол {booking.table}\n"
            f"👤 {booking.name}\n"
            f"📞 {booking.phone}\n"
            f"📅 {booking.date} {booking.time}"
        )

def send_thank_you_to_guest(booking):
    """Благодарность гостю после посещения"""
    message = (
        f"🌟 <b>Спасибо, что посетили Dubrovka Lounge & Bar!</b> 🌟\n\n"
        f"👤 <b>{booking.name}</b>, мы благодарим вас за визит!\n\n"
        f"🍷 Надеемся, вам понравилась атмосфера, обслуживание и кухня.\n\n"
        f"📝 <b>Пожалуйста, оставьте отзыв о нашем заведении в 2ГИС</b>\n"
        f"Ваше мнение очень важно для нас!\n\n"
        f"🔗 <a href='{TWO_GIS_REVIEW_URL}'>Написать отзыв в 2ГИС</a>\n\n"
        f"❤️ Ждем вас снова в Dubrovka!"
    )
    if booking.chat_id:
        send_telegram_to_user(booking.chat_id, message)
        logger.info(f"📱 Благодарность отправлена гостю {booking.name}")
    else:
        send_telegram_to_admin(
            f"✅ <b>ГОСТЬ ПОСЕТИЛ (нет чата)</b>\n\n"
            f"👤 {booking.name}\n"
            f"📞 {booking.phone}\n"
            f"🪑 Стол {booking.table}\n"
            f"📅 {booking.date} {booking.time}\n\n"
            f"🔗 <b>Ссылка на отзыв для гостя:</b>\n"
            f"{TWO_GIS_REVIEW_URL}"
        )

# =====================
# ТАЙМЕРЫ
# =====================

def schedule_reminder(booking):
    """Запланировать напоминание за 30 минут"""
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
            logger.info(f"⏰ Напоминание запланировано на {reminder_time}")
    except Exception as e:
        logger.error(f"❌ Ошибка планирования: {e}")

def schedule_auto_complete(booking):
    """Запланировать автоматическое завершение через 4 часа"""
    try:
        timer = threading.Timer(4 * 3600, auto_complete_booking, args=[booking.id])
        timer.daemon = True
        timer.start()
        completion_timers[booking.id] = timer
        logger.info(f"🤖 Авто-завершение через 4 часа для брони {booking.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

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
            logger.info(f"🤖 Авто-завершение брони {booking_id}")
            
            send_telegram_to_admin(
                f"🤖 <b>АВТО-ЗАВЕРШЕНИЕ</b>\n\n"
                f"🆔 ID: {booking_id}\n"
                f"👤 {booking.name}\n"
                f"📞 {booking.phone}\n"
                f"🪑 Стол {booking.table}\n"
                f"📅 {booking.date} {booking.time}"
            )
            
            send_thank_you_to_guest(booking)
            
        db.close()
    except Exception as e:
        logger.error(f"Ошибка авто-завершения: {e}")
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
# ПУБЛИЧНЫЕ ЭНДПОИНТЫ (без аутентификации)
# =====================

@app.get("/")
@limiter.limit("100/minute")
def root(request: Request):
    return {"status": "ok", "database": "connected"}

@app.get("/health")
@limiter.limit("100/minute")
def health(request: Request):
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/busy_times")
@limiter.limit("60/minute")
async def busy_times(request: Request, date: str, table: str, ip: str = Depends(check_ip)):
    db = SessionLocal()
    try:
        if not validate_date(date):
            raise HTTPException(status_code=400, detail="Invalid date format")
        if not validate_time(table) and table not in TABLE_LIMITS:
            raise HTTPException(status_code=400, detail="Invalid table")
            
        date = normalize_date(date)
        data = db.query(Booking).filter(
            Booking.date == date,
            Booking.table == table,
            Booking.status == "active"
        ).all()
        
        logger.info(f"Busy times requested: date={date}, table={table}, count={len(data)}")
        return [b.time for b in data]
    except Exception as e:
        logger.error(f"Error in busy_times: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/booking")
@limiter.limit("10/minute")
async def create_booking(request: Request, data: dict, ip: str = Depends(check_ip)):
    db = SessionLocal()
    try:
        logger.info(f"📝 Создание брони от IP: {ip}")
        
        # Валидация обязательных полей
        required = ["name", "phone", "guests", "table", "date", "time"]
        for field in required:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")

        # Валидация форматов
        if not validate_name(data["name"]):
            raise HTTPException(status_code=400, detail="Invalid name (2-50 chars, letters, spaces, hyphens)")
        if not validate_phone(data["phone"]):
            raise HTTPException(status_code=400, detail="Invalid phone number. Format: +7XXXXXXXXXX")
        if not validate_date(data["date"]):
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        if not validate_time(data["time"]):
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")

        date = normalize_date(data["date"])
        table = str(data["table"])
        time = data["time"]
        guests = int(data["guests"])
        chat_id = str(data.get("chat_id", ""))

        # Проверка стола
        if table not in TABLE_LIMITS:
            raise HTTPException(status_code=400, detail=f"Table {table} does not exist")

        # Проверка количества гостей
        valid, msg = validate_guests(guests, table)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)

        # Проверка занятости
        exists = db.query(Booking).filter(
            Booking.date == date,
            Booking.time == time,
            Booking.table == table,
            Booking.status == "active"
        ).first()

        if exists:
            logger.warning(f"Double booking attempt: {date} {time} table {table}")
            raise HTTPException(status_code=409, detail="Time slot already booked")

        # Создание брони
        booking = Booking(
            name=data["name"],
            phone=data["phone"],
            guests=guests,
            table=table,
            date=date,
            time=time,
            status="active",
            chat_id=chat_id if chat_id and chat_id != "0" and chat_id != "None" else None,
            ip_address=ip,
            created_at=datetime.now().isoformat()
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        # Отправка уведомлений
        send_booking_confirmation(booking)
        schedule_reminder(booking)
        schedule_auto_complete(booking)

        logger.info(f"✅ Новая бронь: ID={booking.id}, Table={table}, Time={time}")

        # Уведомление админу
        send_telegram_to_admin(
            f"🔥 <b>НОВАЯ БРОНЬ!</b>\n\n"
            f"🆔 <b>ID:</b> {booking.id}\n"
            f"👤 <b>Имя:</b> {data['name']}\n"
            f"📞 <b>Телефон:</b> {data['phone']}\n"
            f"👥 <b>Гостей:</b> {guests}\n"
            f"🪑 <b>Стол:</b> {table}\n"
            f"📅 <b>Дата:</b> {date}\n"
            f"⏰ <b>Время:</b> {time}\n"
            f"📱 <b>Telegram ID:</b> {chat_id if chat_id and chat_id != '0' else 'нет'}\n"
            f"🌐 <b>IP:</b> {ip}"
        )

        return {"ok": True, "id": booking.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Ошибка создания брони: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# =====================
# ЗАЩИЩЕННЫЕ ЭНДПОИНТЫ (с аутентификацией)
# =====================

@app.get("/bookings_by_date")
@limiter.limit("30/minute")
async def bookings_by_date(
    request: Request, 
    date: str, 
    authenticated: bool = Depends(verify_admin),
    ip: str = Depends(check_ip)
):
    db = SessionLocal()
    try:
        logger.info(f"📅 Админ запрос броней на дату: {date} от IP: {ip}")
        
        if not validate_date(date):
            raise HTTPException(status_code=400, detail="Invalid date format")
            
        date = normalize_date(date)
        data = db.query(Booking).filter(
            Booking.date == date,
            Booking.status == "active"
        ).all()
        
        logger.info(f"✅ Найдено броней: {len(data)}")
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
        logger.error(f"❌ Ошибка в bookings_by_date: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/done/{id}")
@limiter.limit("30/minute")
async def done(
    id: int, 
    request: Request,
    authenticated: bool = Depends(verify_admin),
    ip: str = Depends(check_ip)
):
    db = SessionLocal()
    try:
        logger.info(f"✅ Админ завершает бронь {id} от IP: {ip}")
        
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

        logger.info(f"✅ Бронь {id} завершена")

        send_telegram_to_admin(
            f"✅ <b>ГОСТЬ УШЕЛ</b>\n\n"
            f"🆔 <b>ID:</b> {id}\n"
            f"👤 <b>Имя:</b> {booking.name}\n"
            f"📞 <b>Телефон:</b> {booking.phone}\n"
            f"🪑 <b>Стол:</b> {booking.table}\n"
            f"👥 <b>Гостей:</b> {booking.guests}\n"
            f"📅 <b>Дата:</b> {booking.date}\n"
            f"⏰ <b>Время:</b> {booking.time}"
        )
        
        send_thank_you_to_guest(booking)

        return {"ok": True, "message": "Booking completed"}

    except HTTPException:
        raise
    finally:
        db.close()

@app.post("/cancel/{id}")
@limiter.limit("30/minute")
async def cancel(
    id: int, 
    request: Request,
    authenticated: bool = Depends(verify_admin),
    ip: str = Depends(check_ip)
):
    db = SessionLocal()
    try:
        logger.info(f"❌ Админ отменяет бронь {id} от IP: {ip}")
        
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

        logger.info(f"❌ Бронь {id} отменена")

        send_telegram_to_admin(
            f"❌ <b>БРОНЬ ОТМЕНЕНА</b>\n\n"
            f"🆔 ID: {id}\n"
            f"👤 {booking.name}\n"
            f"📞 {booking.phone}\n"
            f"🪑 Стол {booking.table}\n"
            f"📅 {booking.date} {booking.time}"
        )
        
        # Уведомляем гостя об отмене
        if booking.chat_id:
            cancel_message = (
                f"❌ <b>Бронь отменена</b>\n\n"
                f"Уважаемый(ая) {booking.name},\n\n"
                f"Ваша бронь в Dubrovka на {booking.date} {booking.time} (стол {booking.table}) была отменена администратором.\n\n"
                f"Если у вас есть вопросы, звоните: 📞 +7‒913‒432‒01‒01"
            )
            send_telegram_to_user(booking.chat_id, cancel_message)

        return {"ok": True, "message": "Booking cancelled"}

    except HTTPException:
        raise
    finally:
        db.close()

@app.get("/all_bookings")
@limiter.limit("10/minute")
async def all_bookings(
    request: Request,
    authenticated: bool = Depends(verify_admin),
    ip: str = Depends(check_ip)
):
    db = SessionLocal()
    try:
        logger.info(f"📊 Админ запрос всех броней от IP: {ip}")
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
# ЭНДПОИНТ ДЛЯ ГЕНЕРАЦИИ API КЛЮЧА
# =====================

@app.get("/generate_api_key")
async def generate_api_key():
    """Генерация нового API ключа (только для администратора)"""
    new_key = secrets.token_urlsafe(32)
    return {"api_key": new_key}
