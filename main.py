from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

app = FastAPI()

DATABASE_URL = "sqlite:////tmp/db.sqlite"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

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
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/bookings")
def get_bookings():
    db = SessionLocal()
    data = db.query(Booking).all()
    db.close()
    return [b.__dict__ for b in data]

"/booking"
def create_booking(data: dict):
    db = SessionLocal()

    booking = Booking(**data)
    db.add(booking)
    db.commit()
    db.close()

    return {"ok": True}
