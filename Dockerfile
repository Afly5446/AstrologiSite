# Один контейнер: Flask + gunicorn, статика из корня репозитория, API в backend/app.py
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Слой с зависимостями
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Код (корень = BASE_DIR для отдачи index.html, script.js, …)
COPY backend /app/backend
COPY index.html methodology.html script.js styles.css favicon.svg /app/

EXPOSE 8000
ENV PORT=8000
WORKDIR /app/backend

# Railway/Render задают переменную PORT
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120 app:app
