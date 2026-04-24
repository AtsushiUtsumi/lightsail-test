FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/AtsushiUtsumi/lightsail-test"

WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Reactの静的ファイルをコピー
COPY frontend/build/static ./staticfiles/

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1"]
