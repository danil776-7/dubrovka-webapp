FROM python:3.11-slim

WORKDIR /app

# Копируем requirements.txt ПЕРВЫМ (для кэширования)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot.py .

# Запускаем бота с выводом логов в реальном времени
CMD ["python", "-u", "bot.py"]
