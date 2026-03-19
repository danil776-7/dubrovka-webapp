from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# БД (SQLite — проще и работает сразу)
DATABASE_URL = "sqlite:///./db.sqlite"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Модель
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

app = FastAPI()

# CORS (ВАЖНО ДЛЯ САЙТА)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Проверка
@app.get("/")
def root():
    return {"status": "ok"}

# 📥 БРОНИРОВАНИЕ
@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()

    # ❌ защита от двойной брони
    existing = db.query(Booking).filter(
        Booking.date == data["date"],
        Booking.time == data["time"],
        Booking.table == str(data["table"])
    ).first()

    if existing:
        return {"error": "busy"}

    booking = Booking(
        name=data["name"],
        phone=data["phone"],
        guests=int(data["guests"]),
        table=str(data["table"]),
        date=data["date"],
        time=data["time"],
        user_id=int(data.get("user_id", 0)),
        status="pending"
    )

    db.add(booking)
    db.commit()

    return {"ok": True}

# 📊 список (для проверки)
@app.get("/bookings")
def get_bookings():
    db = SessionLocal()
    return db.query(Booking).all()