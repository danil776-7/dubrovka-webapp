from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

# =====================
# БАЗА (SQLite для Render)
# =====================

DATABASE_URL = "sqlite:///./db.sqlite"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# =====================
# МОДЕЛЬ
# =====================

class Booking(Base):
    tablename = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    guests = Column(Integer)
    table = Column(String)
    date = Column(String)
    time = Column(String)
    user_id = Column(Integer)
    status = Column(String, default="pending")  # pending / done

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
# ПРОВЕРКА
# =====================

@app.get("/")
def root():
    return {"status": "ok"}

# =====================
# НОРМАЛИЗАЦИЯ ДАТЫ
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
    bookings = db.query(Booking).all()

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
        for b in bookings
    ]

# =====================
# ЗАНЯТЫЕ СЛОТЫ (КЛЮЧЕВОЕ)
# =====================

@app.get("/busy_times")
def busy_times(date: str, table: str):
    db = SessionLocal()

    date = normalize_date(date)

    bookings = db.query(Booking).filter(
        Booking.date == date,
        Booking.table == table,
        Booking.status != "done"  # только активные брони
    ).all()

    return [b.time for b in bookings]

# =====================
# СОЗДАНИЕ БРОНИ
# =====================

@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()

    date = normalize_date(data["date"])
    time = data["time"]
    table = str(data["table"])

    print("ПРОВЕРКА:", date, time, table)

    # ❗ защита от двойной брони
    existing = db.query(Booking).filter(
        Booking.date == date,
        Booking.time == time,
        Booking.table == table,
        Booking.status != "done"
    ).first()

    if existing:
        return {"error": "busy"}

    booking = Booking(
        name=data["name"],
        phone=data["phone"],
        guests=int(data["guests"]),
        table=table,
        date=date,
        time=time,
        user_id=int(data.get("user_id", 0)),
        status="pending"
    )

    db.add(booking)
    db.commit()

    print("✅ СОЗДАНО:", booking.id)

    return {"ok": True, "id": booking.id}

# =====================
# ГОСТЬ УШЕЛ (ОСВОБОЖДАЕМ СТОЛ)
# =====================

@app.post("/done/{booking_id}")
def done_booking(booking_id: int):
    db = SessionLocal()

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        return {"error": "not_found"}

    booking.status = "done"
    db.commit()

    return {"ok": True}

# =====================
# УДАЛЕНИЕ БРОНИ
# =====================

@app.delete("/booking/{booking_id}")
def delete_booking(booking_id: int):
    db = SessionLocal()

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        return {"error": "not_found"}

    db.delete(booking)
    db.commit()

    return {"ok": True}
    # =====================
# ОЧИСТКА БАЗЫ (ТЕСТ)
# =====================

@app.get("/clear")
def clear():
    db = SessionLocal()
    db.query(Booking).delete()
    db.commit()
    return {"ok": True}
