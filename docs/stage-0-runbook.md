# Stage 0 Runbook

## Prerequisites

- Python 3.14
- PostgreSQL 16
- Postgres role with `CREATEDB` for tests
- Gemini API key
- Docker Desktop for container checks/deployment

## First-time setup

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set every required value in `.env`:

```dotenv
GEMINI_API_KEY=...
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/multi_method_rag
DJANGO_SECRET_KEY=use-a-long-random-production-secret
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=
DJANGO_LOG_LEVEL=DEBUG
```

Generate a secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Create the local database

```bash
createdb multi_method_rag
psql -d multi_method_rag -c 'CREATE EXTENSION IF NOT EXISTS vector;'
python manage.py migrate
```

`vector` is enabled for Stage 1 readiness; Stage 0 does not use it.

## Create a login

```bash
python manage.py createsuperuser
```

Log in at `http://127.0.0.1:8000/login/`.

## Run locally

```bash
python manage.py runserver
```

Useful URLs:

- App: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`
- Health: `http://127.0.0.1:8000/health/`

## Test and validate

```bash
pytest
python manage.py check
python manage.py makemigrations --check
python -m pip check
```

Tests create a temporary Postgres database. The configured role needs `CREATEDB`.

## Development logs

`DJANGO_DEBUG=true` defaults app logs to `DEBUG`. Override with:

```dotenv
DJANGO_LOG_LEVEL=DEBUG
```

Logs include request timing, user/conversation/message IDs, CRUD events, Gemini model,
history/character counts, call timing, and failures. Message text, replies, keys, cookies,
and credentials are not logged.

Example:

```text
INFO chat.gemini gemini.call.complete model=gemini-flash-latest history_messages=3 prompt_chars=240 response_chars=510 elapsed_ms=842.3
INFO app.request request.complete method=POST path=/conversations/7/messages/ status=200 user_id=2 elapsed_ms=856.7
```

## Reset the local database

Destructive: this removes all local users, conversations, and messages.

```bash
dropdb --if-exists multi_method_rag
createdb multi_method_rag
psql -d multi_method_rag -c 'CREATE EXTENSION IF NOT EXISTS vector;'
python manage.py migrate
python manage.py createsuperuser
```

Do not run these commands against production.

## Docker

Build:

```bash
docker build -t multi-method-rag:stage0 .
```

Run against Postgres on the Mac host:

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql://USER:PASSWORD@host.docker.internal:5432/multi_method_rag \
  -e DJANGO_SECRET_KEY='replace-me' \
  -e DJANGO_DEBUG=true \
  -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
  -e GEMINI_API_KEY='replace-me' \
  multi-method-rag:stage0
```

## Deploy

Deploy the Dockerfile with a managed Postgres database and HTTPS enabled.

Required environment variables:

```dotenv
DATABASE_URL=postgresql://...
GEMINI_API_KEY=...
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=your-host.example
CSRF_TRUSTED_ORIGINS=https://your-host.example
DJANGO_SECURE_HSTS_SECONDS=3600
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=false
```

The container runs migrations before starting Gunicorn.

Create the first production login using the host's one-off shell:

```bash
python manage.py createsuperuser
```

Verify after deployment:

```bash
curl --fail https://your-host.example/health/
```

Expected:

```json
{"status": "ok", "database": "ok"}
```

Then verify: login → create → chat → reload → rename → delete. Save the URL and screenshot in `proof/`.

## Common maintenance

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py changepassword USERNAME
python manage.py shell
```
