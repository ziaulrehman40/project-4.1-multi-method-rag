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
# All build steps are idempotent and content-hash guarded (ingest_docs, build_graph, …), so
# redeploys with unchanged docs make no extra LLM calls. ensure_eval runs BACKGROUNDED (never
# blocks gunicorn from binding) and only when there's no EvalRun yet (or EVAL_VERSION changed).
CMD ["sh", "-c", "python manage.py migrate && python manage.py ensure_superuser && python manage.py apply_rebuild && python manage.py ingest_docs && python manage.py build_graph && python manage.py build_trees && python manage.py build_multimodal && (python manage.py ensure_eval &) && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
