from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import requests

# =====================
# DATABASE
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

# 🔥 СЮДА ВСТАВЬ СВОЙ ТОКЕН БОТА
TELEGRAM_BOT_TOKEN = "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves"

# 🔥 СЮДА ВСТАВЬ СВОЙ ID АДМИНА (можно получить через @userinfobot)
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
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=5
        )
        response.raise_for_status()
    except Exception as e:
        print("TG ERROR:", e)

# =====================
# HELPERS
# =====================

def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        # 🔥 ИСПРАВЛЕНО: выбрасываем ошибку вместо возврата неправильной даты
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}")

# =====================
# ROOT
# =====================

@app.get("/")
def root():
    return {"status": "ok"}

# =====================
# БРОНИ ПО ДАТЕ (АДМИНКА)
# =====================

@app.get("/bookings_by_date")
def bookings_by_date(date: str):
    db = SessionLocal()
    
    try:
        date = normalize_date(date)
        
        data = db.query(Booking).filter(
            Booking.date == date
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
        # 🔥 ИСПРАВЛЕНО: закрываем сессию в любом случае
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
            Booking.status != "done"
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
        # 🔥 ИСПРАВЛЕНО: проверяем наличие всех полей
        required_fields = ["name", "phone", "guests", "table", "date", "time"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")
        
        date = normalize_date(data["date"])
        table = str(data["table"])
        time = data["time"]
        guests = int(data["guests"])
        
        # проверка что стол существует
        if table not in TABLE_LIMITS:
            raise HTTPException(status_code=400, detail=f"Invalid table: {table}")
        
        # лимит гостей
        if guests > TABLE_LIMITS[table]:
            raise HTTPException(status_code=400, detail="Too many guests for this table")
        
        # проверка занятости
        exists = db.query(Booking).filter(
            Booking.date == date,
            Booking.time == time,
            Booking.table == table,
            Booking.status != "done"
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
            status="pending"
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Telegram админу
        send_telegram(
            f"🔥 <b>Новая бронь</b>\n\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"👥 {guests}\n"
            f"🪑 Стол: {table}\n"
            f"📅 {date}\n"
            f"⏰ {time}"
        )
        
        return {"ok": True, "id": booking.id}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
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
            Booking.id == id
        ).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # 🔥 ИСПРАВЛЕНО: меняем статус вместо удаления
        booking.status = "done"
        db.commit()
        
        return {"ok": True, "message": "Booking marked as completed"}
    
    except HTTPException:
        raise
    finally:
        db.close()
