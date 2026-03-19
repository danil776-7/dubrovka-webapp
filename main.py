from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./db.sqlite"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String)
    guests = Column(Integer)
    table = Column(String)
    date = Column(String)
    time = Column(String)
    user_id = Column(Integer)
    status = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok"}

# занятые слоты
@app.get("/busy_times")
def busy_times(date: str, table: str):
    db = SessionLocal()
    bookings = db.query(Booking).filter(
        Booking.date == date,
        Booking.table == table
    ).all()
    return [b.time for b in bookings]

# создание брони
@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()

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

    return {"ok": True, "id": booking.id}

# удаление брони
@app.delete("/booking/{booking_id}")
def delete_booking(booking_id: int):
    db = SessionLocal()

    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        return {"error": "not_found"}

    db.delete(booking)
    db.commit()

    return {"ok": True}