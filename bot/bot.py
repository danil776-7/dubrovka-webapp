import json
import os
import sys
from aiogram import Bot, Dispatcher, types, executor
import requests

# Токен из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "7545540622"))

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not set!")
    sys.exit(1)

# URL вашего бэкенда на Railway
API_URL = "https://dubrovka-webapp-production.up.railway.app"

print(f"🤖 Бот запускается...")
print(f"📡 API URL: {API_URL}")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Клавиатура с кнопкой бронирования
keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(
    types.KeyboardButton(
        text="🍽 Бронирование",
        web_app=types.WebAppInfo(
            url="https://danil776-7.github.io/dubrovka_webapp/frontend/"
        )
    )
)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в Dubrovka Lounge & Bar!\n\n"
        "Нажмите кнопку ниже для бронирования стола:",
        reply_markup=keyboard
    )

@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def web_app(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        data["chat_id"] = message.chat.id
        
        print(f"📝 Получены данные: {data}")
        
        res = requests.post(
            f"{API_URL}/booking",
            json=data,
            timeout=10
        )
        
        result = res.json()
        
        if result.get("error") or result.get("detail") == "Time slot already booked":
            await message.answer("❌ Этот стол уже занят")
            return
        
        booking_id = result.get("id")
        
        text = f"""
✅ <b>Бронь создана!</b>

📅 {data['date']} {data['time']}
🪑 Стол {data['table']}
👥 {data['guests']} чел.
🆔 ID: {booking_id}
        """
        
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "❌ Отменить бронь",
                callback_data=f"cancel|{booking_id}"
            )
        )
        
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        
        await bot.send_message(
            ADMIN_ID,
            f"🔥 <b>НОВАЯ БРОНЬ!</b>\n\n"
            f"🆔 ID: {booking_id}\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"👥 {data['guests']} чел.\n"
            f"🪑 Стол {data['table']}\n"
            f"📅 {data['date']} {data['time']}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await message.answer("❌ Ошибка при бронировании")

@dp.callback_query_handler(lambda c: c.data.startswith("cancel"))
async def cancel_booking(call: types.CallbackQuery):
    try:
        _, booking_id = call.data.split("|")
        
        res = requests.post(
            f"{API_URL}/cancel/{booking_id}",
            timeout=10
        )
        
        if res.status_code == 200:
            await call.message.edit_text("❌ Бронь отменена")
            await call.answer("Бронь отменена")
        else:
            await call.answer("Ошибка отмены", show_alert=True)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await call.answer("Ошибка", show_alert=True)

if __name__ == "__main__":
    print("🤖 Бот запущен и готов к работе!")
    executor.start_polling(dp, skip_updates=True)
