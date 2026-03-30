FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости (нужны для psycopg2)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости напрямую
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.0 \
    sqlalchemy==2.0.35 \
    psycopg2-binary==2.9.9 \
    requests==2.31.0 \
    python-multipart==0.0.9

# Копируем код приложения
COPY . .

# Проверяем, что uvicorn установлен
RUN pip list | grep uvicorn

# Запускаем
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
