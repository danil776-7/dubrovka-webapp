from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DATABASE_URL = "sqlite:///./db.sqlite"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# =====================
# ЛИМИТЫ СТОЛОВ
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
# МОДЕЛЬ
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
    user_id = Column(Integer)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

# =====================
# APP
# =====================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# АДМИН ЛОГИН
# =====================

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "1234"

@app.post("/login")
def login(data: dict):
    if data.get("login") == ADMIN_LOGIN and data.get("password") == ADMIN_PASSWORD:
        return {"ok": True}
    return {"error": "invalid"}

# =====================
# ROOT
# =====================

@app.get("/")
def root():
    return {"status": "ok"}

# =====================
# DATE FIX
# =====================

def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return date_str

# =====================
# ВСЕ БРОНИ
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
        } for b in data
    ]

# =====================
# ЗАНЯТЫЕ ВРЕМЕНА
# =====================

@app.get("/busy_times")
def busy_times(date: str, table: str):
    db = SessionLocal()
    date = normalize_date(date)

    bookings = db.query(Booking).filter(
        Booking.date == date,
        Booking.table == table,
        Booking.status != "done"
    ).all()

    db.close()
    return [b.time for b in bookings]

# =====================
# СОЗДАНИЕ БРОНИ
# =====================

@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()

    date = normalize_date(data["date"])
    table = str(data["table"])
    time = data["time"]
    guests = int(data["guests"])

    max_guests = TABLE_LIMITS.get(table, 5)

    if guests > max_guests:
        db.close()
        return {"error": "guests_limit", "message": f"Максимум: {max_guests}"}

    existing = db.query(Booking).filter(
        Booking.date == date,
        Booking.time == time,
        Booking.table == table,
        Booking.status != "done"
    ).first()

    if existing:
        db.close()
        return {"error": "busy"}

    booking = Booking(
        name=data["name"],
        phone=data["phone"],
        guests=guests,
        table=table,
        date=date,
        time=time,
        user_id=int(data.get("user_id", 0)),
        status="pending"
    )

    db.add(booking)
    db.commit()
    db.close()

    return {"ok": True}

# =====================
# ОСВОБОДИТЬ СТОЛ
# =====================

@app.post("/done/{booking_id}")
def done(booking_id: int):
    db = SessionLocal()

    b = db.query(Booking).filter(Booking.id == booking_id).first()

    if not b:
        db.close()
        return {"error": "not_found"}

    b.status = "done"
    db.commit()
    db.close()

    return {"ok": True}