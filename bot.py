from aiogram import Bot, Dispatcher, types, executor
import json
import requests
import os

# ===== ENV =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise Exception("❌ TELEGRAM_BOT_TOKEN не задан")

if not ADMIN_ID:
    raise Exception("❌ ADMIN_ID не задан")

ADMIN_ID = int(ADMIN_ID)

# ===== INIT =====
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ===== КНОПКА САЙТА =====
keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(
    types.KeyboardButton(
        text="🍽 Бронирование",
        web_app=types.WebAppInfo(
            url="https://danil776-7.github.io/dubrovka-webapp/"
        )
    )
)

# ===== /start =====
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Открыть бронирование:", reply_markup=keyboard)

# ===== ПОЛУЧЕНИЕ ДАННЫХ С САЙТА =====
@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def web_app(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
    except:
        await message.answer("❌ Ошибка данных")
        return

    try:
        res = requests.post(
            "https://dubrovka-webapp-9.onrender.com/booking",
            json=data,
            timeout=5
        )
        result = res.json()
    except:
        await message.answer("❌ Ошибка сервера, попробуйте позже")
        return

    if result.get("error"):
        await message.answer("❌ Этот стол уже занят")
        return

    booking_id = result.get("id")

    text = f"""
✅ Бронь создана

📅 {data.get('date')}
⏰ {data.get('time')}
🪑 Стол {data.get('table')}
👥 Гостей: {data.get('guests')}
"""

    # кнопка отмены
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "❌ Отменить бронь",
            callback_data=f"cancel|{booking_id}"
        )
    )

    # пользователю
    await message.answer(text, reply_markup=kb)

    # админу
    await bot.send_message(
        ADMIN_ID,
        f"🔥 Новая бронь\n{text}"
    )

# ===== ОТМЕНА БРОНИ =====
@dp.callback_query_handler(lambda c: c.data.startswith("cancel"))
async def cancel_booking(call: types.CallbackQuery):
    try:
        _, booking_id = call.data.split("|")

        res = requests.delete(
            f"https://dubrovka-webapp-9.onrender.com/booking/{booking_id}",
            timeout=5
        )
        result = res.json()
    except:
        await call.answer("Ошибка сервера", show_alert=True)
        return

    if result.get("ok"):
        await call.message.edit_text("❌ Бронь отменена")
    else:
        await call.answer("Ошибка отмены", show_alert=True)

# ===== СТАРТ =====
if __name__ == "__main__":
    print("🚀 Bot started...")
    executor.start_polling(dp, skip_updates=True)
