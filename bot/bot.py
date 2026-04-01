import json
import os
import sys
from aiogram import Bot, Dispatcher, types, executor
import requests
import asyncio
import threading
import time
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "7545540622"))

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not set!")
    sys.exit(1)

API_URL = "https://dubrovka-webapp-production.up.railway.app"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Хранилище для сообщений: {booking_id: {"chat_id": xxx, "message_id": xxx}}
booking_messages = {}
reminders = {}

keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(
    types.KeyboardButton(
        text="🍽 Бронирование",
        web_app=types.WebAppInfo(
            url="https://danil776-7.github.io/dubrovka-webapp/"
        )
    )
)

def schedule_reminder(chat_id, booking_id, booking_time, booking_date, booking_table, booking_name):
    try:
        booking_datetime = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
        reminder_time = booking_datetime - timedelta(minutes=30)
        now = datetime.now()
        
        if reminder_time > now:
            delay = (reminder_time - now).total_seconds()
            
            def send_reminder():
                time.sleep(delay)
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id,
                        f"🔔 <b>НАПОМИНАНИЕ О БРОНИ!</b>\n\n"
                        f"🪑 Стол {booking_table}\n"
                        f"📅 {booking_date}\n"
                        f"⏰ Через 30 минут: {booking_time}\n\n"
                        f"📍 Ермакова 11\n"
                        f"📞 +7‒913‒432‒01‒01"
                    ),
                    asyncio.get_event_loop()
                )
            
            timer = threading.Timer(delay, send_reminder)
            timer.daemon = True
            timer.start()
            reminders[booking_id] = timer
            print(f"⏰ Напоминание для брони {booking_id}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в Dubrovka Lounge & Bar!\n\n"
        "Нажмите кнопку ниже для бронирования стола:",
        reply_markup=keyboard
    )

@dp.message_handler(commands=["test"])
async def test(message: types.Message):
    await message.answer("✅ Бот работает!")

@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def web_app(message: types.Message):
    try:
        processing_msg = await message.answer("⏳ Проверка доступности стола...")
        
        data = json.loads(message.web_app_data.data)
        data["chat_id"] = message.chat.id
        
        print(f"📝 Получены данные: {data}")
        
        res = requests.post(
            f"{API_URL}/booking",
            json=data,
            timeout=10
        )
        
        print(f"📡 Статус ответа: {res.status_code}")
        print(f"📡 Текст ответа: {res.text}")
        
        await processing_msg.delete()
        
        try:
            result = res.json()
        except:
            result = {}
        
        booking_id = result.get("id")
        
        if booking_id:
            success_text = (
                f"✅ <b>БРОНЬ ПОДТВЕРЖДЕНА!</b>\n\n"
                f"🆔 <b>ID:</b> {booking_id}\n"
                f"👤 <b>Имя:</b> {data['name']}\n"
                f"🪑 <b>Стол:</b> {data['table']}\n"
                f"👥 <b>Гостей:</b> {data['guests']}\n"
                f"📅 <b>Дата:</b> {data['date']}\n"
                f"⏰ <b>Время:</b> {data['time']}\n\n"
                f"📍 <b>Адрес:</b> Ермакова 11\n"
                f"📞 <b>Телефон:</b> +7‒913‒432‒01‒01\n\n"
                f"❤️ Ждем вас!"
            )
            
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton(
                    "❌ Отменить бронь",
                    callback_data=f"cancel|{booking_id}"
                )
            )
            
            # Отправляем сообщение и сохраняем его ID
            sent_msg = await message.answer(success_text, reply_markup=kb, parse_mode="HTML")
            
            # Сохраняем информацию о сообщении
            booking_messages[booking_id] = {
                "chat_id": message.chat.id,
                "message_id": sent_msg.message_id,
                "booking": data
            }
            print(f"✅ Сохранено сообщение для брони {booking_id}, msg_id={sent_msg.message_id}")
            
            # Планируем напоминание
            schedule_reminder(
                message.chat.id,
                booking_id,
                data['time'],
                data['date'],
                data['table'],
                data['name']
            )
            
            # Уведомление админу
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
        else:
            await message.answer(
                f"❌ <b>Извините, этот стол уже занят!</b>\n\n"
                f"📅 {data['date']} {data['time']}\n"
                f"🪑 Стол {data['table']}\n\n"
                f"Пожалуйста, выберите другое время.",
                parse_mode="HTML"
            )
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await message.answer(
            "❌ Произошла ошибка при бронировании.\n"
            "Пожалуйста, попробуйте позже."
        )

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("cancel"))
async def cancel_booking(call: types.CallbackQuery):
    try:
        _, booking_id = call.data.split("|")
        booking_id = int(booking_id)
        
        await call.answer("⏳ Отмена брони...")
        
        res = requests.post(
            f"{API_URL}/cancel/{booking_id}",
            timeout=10
        )
        
        if booking_id in reminders:
            reminders[booking_id].cancel()
            del reminders[booking_id]
        
        if res.status_code == 200:
            # Редактируем сообщение с броней
            if booking_id in booking_messages:
                msg_info = booking_messages[booking_id]
                old_text = call.message.text
                new_text = old_text.replace("✅ <b>БРОНЬ ПОДТВЕРЖДЕНА!</b>", "❌ <b>БРОНЬ ОТМЕНЕНА</b>")
                new_text = new_text.replace("❤️ Ждем вас!", "❌ Бронь отменена.")
                
                try:
                    await bot.edit_message_text(
                        chat_id=msg_info["chat_id"],
                        message_id=msg_info["message_id"],
                        text=new_text,
                        parse_mode="HTML"
                    )
                    print(f"✅ Сообщение брони {booking_id} обновлено")
                except Exception as e:
                    print(f"⚠️ Не удалось обновить сообщение: {e}")
                
                del booking_messages[booking_id]
            
            await call.message.edit_text(
                f"❌ <b>Бронь отменена</b>\n\n"
                f"Бронь #{booking_id} успешно отменена.\n\n"
                f"📞 +7‒913‒432‒01‒01",
                parse_mode="HTML"
            )
            await call.answer("Бронь отменена")
        else:
            await call.answer("Ошибка отмены", show_alert=True)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await call.answer("Ошибка", show_alert=True)

if __name__ == "__main__":
    print("🤖 Бот запущен!")
    print(f"📡 API URL: {API_URL}")
    executor.start_polling(dp, skip_updates=True)
