FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# A build-only URL lets Django initialize while collectstatic performs no DB I/O.
RUN DJANGO_SECRET_KEY=build-only-secret \
    DATABASE_URL=postgresql://build:build@localhost/build \
    DJANGO_DEBUG=false \
    python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
