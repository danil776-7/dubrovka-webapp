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

TELEGRAM_BOT_TOKEN = "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves"
ADMIN_CHAT_ID = "7545540622"

# Ссылка на 2ГИС для отзыва
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
            
            # Отправляем уведомление админу
            send_telegram(
                f"🤖 <b>АВТОМАТИЧЕСКОЕ ЗАВЕРШЕНИЕ</b>\n\n"
                f"🆔 <b>ID брони:</b> {booking_id}\n"
                f"👤 <b>Имя:</b> {booking.name}\n"
                f"📞 <b>Телефон:</b> {booking.phone}\n"
                f"🪑 <b>Стол:</b> {booking.table}\n"
                f"📅 <b>Дата:</b> {booking.date}\n"
                f"⏰ <b>Время:</b> {booking.time}\n\n"
                f"🔓 Стол {booking.table} на {booking.time} теперь доступен для бронирования!"
            )
            
            # Отправляем уведомление гостю
            send_telegram_to_guest(booking.phone, booking.name)
            
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
            print("✅ Telegram notification sent to admin")
        else:
            print(f"❌ Telegram error: {response.status_code}")
    except Exception as e:
        print("❌ TG ERROR:", e)

def send_telegram_to_guest(phone, name):
    """Отправка уведомления гостю через Telegram (если у гостя есть Telegram)"""
    try:
        # Пытаемся найти гостя по номеру телефона в Telegram
        # Для этого нужно, чтобы гость уже взаимодействовал с ботом
        # Используем метод getUpdates или храним user_id в базе
        
        # Формируем сообщение для гостя
        message = (
            f"🌟 <b>Спасибо, что посетили Dubrovka Lounge & Bar!</b> 🌟\n\n"
            f"👤 {name}, мы благодарим вас за визит!\n\n"
            f"🍷 Надеемся, вам понравилась атмосфера, обслуживание и кухня.\n\n"
            f"📝 <b>Пожалуйста, оставьте отзыв о нашем заведении в 2ГИС</b>\n"
            f"Ваше мнение очень важно для нас!\n\n"
            f"🔗 <a href='{TWO_GIS_REVIEW_URL}'>Написать отзыв в 2ГИС</a>\n\n"
            f"❤️ Ждем вас снова в Dubrovka!"
        )
        
        # Отправляем сообщение в Telegram бот (гость должен был начать диалог с ботом)
        # Для этого нужно сохранять user_id при бронировании через Telegram WebApp
        # Временно отправляем админу для проверки
        print(f"📱 Would send to guest {phone}: {message[:100]}...")
        
        # TODO: Здесь нужно отправить сообщение гостю, если известен его user_id
        # response = requests.post(
        #     f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        #     json={
        #         "chat_id": user_id,  # Нужно сохранять user_id из Telegram WebApp
        #         "text": message,
        #         "parse_mode": "HTML"
        #     },
        #     timeout=5
        # )
        
    except Exception as e:
        print(f"❌ Error sending to guest {phone}: {e}")

def send_review_request(phone, name):
    """Отправка запроса на отзыв (через SMS или Telegram)"""
    try:
        # Формируем ссылку на отзыв в 2ГИС
        review_url = TWO_GIS_REVIEW_URL
        
        message = (
            f"🌟 Dubrovka Lounge & Bar 🌟\n\n"
            f"{name}, спасибо за визит!\n\n"
            f"Пожалуйста, оцените наше обслуживание:\n"
            f"{review_url}\n\n"
            f"Ваш отзыв поможет нам стать лучше! ❤️"
        )
        
        # Здесь можно добавить отправку SMS через сервис
        # или отправить через Telegram, если есть user_id
        
        print(f"📱 Review request for {phone}: {message[:100]}...")
        
    except Exception as e:
        print(f"❌ Error sending review request: {e}")

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
        required = ["name", "phone", "guests", "table", "date", "time"]
        for field in required:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")

        date = normalize_date(data["date"])
        table = str(data["table"])
        time = data["time"]
        guests = int(data["guests"])
        user_id = data.get("user_id", None)

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

        # Сохраняем user_id если есть (для отправки уведомлений)
        if user_id:
            # TODO: Сохранить user_id в отдельной таблице или поле
            pass

        start_auto_complete_timer(booking.id)

        print(f"✅ New booking created: ID={booking.id}, Table={table}, Time={time}")

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
        print(f"❌ Error: {e}")
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

        if id in booking_timers:
            del booking_timers[id]

        print(f"✅ Booking {id} marked as completed")

        # Отправляем уведомление админу
        send_telegram(
            f"✅ <b>ГОСТЬ УШЕЛ</b>\n\n"
            f"🆔 <b>ID брони:</b> {id}\n"
            f"👤 <b>Имя:</b> {booking.name}\n"
            f"📞 <b>Телефон:</b> {booking.phone}\n"
            f"🪑 <b>Стол:</b> {booking.table}\n"
            f"📅 <b>Дата:</b> {booking.date}\n"
            f"⏰ <b>Время:</b> {booking.time}\n"
            f"👥 <b>Было гостей:</b> {booking.guests}\n\n"
            f"🔓 Стол {booking.table} на {booking.time} теперь доступен для бронирования!"
        )
        
        # 🔥 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ ГОСТЮ С БЛАГОДАРНОСТЬЮ И ССЫЛКОЙ НА ОТЗЫВ
        guest_message = (
            f"🌟 <b>Спасибо, что посетили Dubrovka Lounge & Bar!</b> 🌟\n\n"
            f"👤 <b>{booking.name}</b>, мы благодарим вас за визит!\n\n"
            f"🍷 Надеемся, вам понравилась атмосфера, обслуживание и кухня.\n\n"
            f"📝 <b>Пожалуйста, оставьте отзыв о нашем заведении в 2ГИС</b>\n"
            f"Ваше мнение очень важно для нас!\n\n"
            f"🔗 <a href='{TWO_GIS_REVIEW_URL}'>Написать отзыв в 2ГИС</a>\n\n"
            f"❤️ Ждем вас снова в Dubrovka!"
        )
        
        # Отправляем сообщение гостю через Telegram (если бот знает user_id)
        # Временно отправляем админу для проверки, что сообщение сформировано правильно
        send_telegram(
            f"📱 <b>СООБЩЕНИЕ ДЛЯ ГОСТЯ</b>\n\n"
            f"Кому: {booking.name} ({booking.phone})\n\n"
            f"{guest_message}"
        )
        
        # TODO: Здесь нужно реально отправить сообщение гостю
        # Для этого нужно сохранять user_id при бронировании через Telegram WebApp
        # И использовать его для отправки
        
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
        
        # Отправляем уведомление гостю об отмене
        cancel_message = (
            f"❌ <b>Бронь отменена</b>\n\n"
            f"Уважаемый(ая) {booking.name},\n\n"
            f"Ваша бронь в Dubrovka Lounge & Bar на {booking.date} {booking.time} (стол {booking.table}) была отменена администратором.\n\n"
            f"Если у вас есть вопросы, пожалуйста, свяжитесь с нами:\n"
            f"📞 +7‒913‒432‒01‒01\n\n"
            f"Приносим извинения за неудобства."
        )
        
        # Отправляем админу для проверки
        send_telegram(
            f"📱 <b>УВЕДОМЛЕНИЕ ОБ ОТМЕНЕ ДЛЯ ГОСТЯ</b>\n\n"
            f"Кому: {booking.name} ({booking.phone})\n\n"
            f"{cancel_message}"
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
