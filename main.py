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
    status = Column(String, default="pending")

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


@app.get("/bookings")
def get_bookings():
    db = SessionLocal()
    return db.query(Booking).all()


def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return date_str


@app.get("/busy_times")
def busy_times(date: str, table: str):
    db = SessionLocal()

    date = normalize_date(date)

    bookings = db.query(Booking).filter(
        Booking.date == date,
        Booking.table == table,
        Booking.status != "done"
    ).all()

    return [b.time for b in bookings]


@app.post("/booking")
def create_booking(data: dict):
    db = SessionLocal()

    date = normalize_date(data["date"])
    table = str(data["table"])
    time = data["time"]

    existing = db.query(Booking).filter(
        Booking.date == date,
        Booking.table == table,
        Booking.time == time,
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

    return {"ok": True}


@app.post("/update_status/{booking_id}")
def update_status(booking_id: int):
    db = SessionLocal()

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        return {"error": "not_found"}

    booking.status = "done"
    db.commit()

    return {"ok": True}


@app.get("/clear")
def clear():
    db = SessionLocal()
    db.query(Booking).delete()
    db.commit()
    return {"ok": True}
