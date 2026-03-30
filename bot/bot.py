import json
import os
import sys
from aiogram import Bot, Dispatcher, types, executor
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "7545540622"))

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not set!")
    sys.exit(1)

API_URL = "https://dubrovka-webapp-production.up.railway.app"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Клавиатура с кнопкой бронирования
keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(
    types.KeyboardButton(
        text="🍽 Бронирование",
        web_app=types.WebAppInfo(
            url="https://danil776-7.github.io/dubrovka-webapp/"
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
        # 🔥 ОТПРАВЛЯЕМ СООБЩЕНИЕ "Обработка..." СРАЗУ
        processing_msg = await message.answer("⏳ Проверка доступности стола...")
        
        data = json.loads(message.web_app_data.data)
        data["chat_id"] = message.chat.id
        
        print(f"📝 Получены данные: {data}")
        
        # Отправляем запрос на сервер
        res = requests.post(
            f"{API_URL}/booking",
            json=data,
            timeout=10
        )
        
        result = res.json()
        print(f"📡 Ответ сервера: {result}")
        
        # Проверяем ответ сервера
        if result.get("error") or result.get("detail") == "Time slot already booked":
            # 🔥 СТОЛ ЗАНЯТ - ПОКАЗЫВАЕМ ОШИБКУ
            await processing_msg.delete()
            await message.answer(
                "❌ <b>Извините, этот стол уже занят!</b>\n\n"
                f"📅 {data['date']} {data['time']}\n"
                f"🪑 Стол {data['table']}\n\n"
                "Пожалуйста, выберите другое время или стол.",
                parse_mode="HTML"
            )
            return
        
        # Успешная бронь
        booking_id = result.get("id")
        
        # Формируем сообщение об успехе
        success_text = (
            f"✅ <b>БРОНЬ ПОДТВЕРЖДЕНА!</b>\n\n"
            f"🆔 <b>ID брони:</b> {booking_id}\n"
            f"👤 <b>Имя:</b> {data['name']}\n"
            f"🪑 <b>Стол:</b> {data['table']}\n"
            f"👥 <b>Гостей:</b> {data['guests']}\n"
            f"📅 <b>Дата:</b> {data['date']}\n"
            f"⏰ <b>Время:</b> {data['time']}\n\n"
            f"📍 <b>Адрес:</b> Ермакова 11, Новокузнецк\n"
            f"📞 <b>Телефон:</b> +7‒913‒432‒01‒01\n\n"
            f"❤️ Ждем вас в Dubrovka!"
        )
        
        # Кнопка отмены
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "❌ Отменить бронь",
                callback_data=f"cancel|{booking_id}"
            )
        )
        
        # Удаляем сообщение "Обработка..." и отправляем результат
        await processing_msg.delete()
        await message.answer(success_text, reply_markup=kb, parse_mode="HTML")
        
        # Отправляем уведомление админу
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
        await message.answer(
            "❌ Произошла ошибка при бронировании.\n"
            "Пожалуйста, попробуйте позже или свяжитесь с администратором."
        )

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("cancel"))
async def cancel_booking(call: types.CallbackQuery):
    try:
        _, booking_id = call.data.split("|")
        
        await call.answer("⏳ Отмена брони...")
        
        res = requests.post(
            f"{API_URL}/cancel/{booking_id}",
            timeout=10
        )
        
        if res.status_code == 200:
            await call.message.edit_text(
                "❌ <b>Бронь отменена</b>\n\n"
                f"Бронь #{booking_id} успешно отменена.\n\n"
                "Если у вас есть вопросы, свяжитесь с администратором.",
                parse_mode="HTML"
            )
            await call.answer("Бронь отменена")
        else:
            await call.answer("Ошибка отмены", show_alert=True)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await call.answer("Ошибка", show_alert=True)

if __name__ == "__main__":
    print("🤖 Бот запущен и готов к работе!")
    executor.start_polling(dp, skip_updates=True)
