# Используем официальный образ Python
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY . .

# Создаем директорию для данных
RUN mkdir -p /app/data

# Устанавливаем PYTHONPATH
ENV PYTHONPATH=/app

# Устанавливаем флаг Docker окружения
ENV DOCKER_ENV=true

# Запускаем ТОЛЬКО main.py
# main.py сам запустит миграции при старте
CMD ["python", "-u", "main.py"]
