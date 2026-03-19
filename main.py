from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import SessionLocal
from models import Booking

from aiogram import Bot

BOT_TOKEN = "8769949339:AAFwvdkPFgj7l4BQwGfmcljauMWXRx7qves"
ADMIN_ID = 7738397444

bot = Bot(token=BOT_TOKEN)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= СОЗДАНИЕ БРОНИ =================
@app.post("/booking")
async def create_booking(data: dict):
    db = SessionLocal()

    booking = Booking(**data)
    db.add(booking)
    db.commit()

    # 🔔 клиенту
    try:
        if data.get("user_id"):
            await bot.send_message(
                data["user_id"],
                f"🍽 Dubrovka\n\n"
                f"Ваша заявка отправлена администратору ⏳\n\n"
                f"📅 {data['date']} {data['time']}"
            )
    except Exception as e:
        print("Ошибка клиенту:", e)

    # 🔔 админу
    await bot.send_message(
        ADMIN_ID,
        f"🔥 Новая бронь!\n\n"
        f"👤 {data['name']}\n"
        f"📞 {data['phone']}\n"
        f"📅 {data['date']} {data['time']}\n"
        f"🪑 Стол: {data['table']}"
    )

    return {"status": "ok"}


# ================= СПИСОК =================
@app.get("/bookings")
def get_bookings():
    db = SessionLocal()
    return db.query(Booking).all()


# ================= ПОДТВЕРЖДЕНИЕ =================
@app.post("/confirm/{booking_id}")
async def confirm(booking_id: int):
    db = SessionLocal()
    booking = db.query(Booking).get(booking_id)

    booking.status = "confirmed"
    db.commit()

    # 🔔 клиенту
    try:
        if booking.user_id:
            await bot.send_message(
                booking.user_id,
                f"✅ Dubrovka\n\n"
                f"Ваша бронь подтверждена!\n\n"
                f"📅 {booking.date} {booking.time}\n"
                f"🪑 Стол: {booking.table}"
            )
    except Exception as e:
        print(e)

    return {"status": "confirmed"}


# ================= ОТКЛОНЕНИЕ =================
@app.post("/reject/{booking_id}")
async def reject(booking_id: int):
    db = SessionLocal()
    booking = db.query(Booking).get(booking_id)

    booking.status = "rejected"
    db.commit()

    try:
        if booking.user_id:
            await bot.send_message(
                booking.user_id,
                "❌ Ваша бронь отклонена"
            )
    except:
        pass

    return {"status": "rejected"}