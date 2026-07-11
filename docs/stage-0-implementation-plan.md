# Stage 0 Implementation Plan — App Skeleton and Chat

> **For the implementing model:** Build exactly what is described here. Do not add
> retrieval/RAG, extra features, or a frontend framework. Follow the lifecycle order:
> **Plan (this doc) → Tests-first → Build → Green → Deploy.** Keep it simple and functional.

## 1. Goal (from README "Stage 0")

A working, deployed chatbot over the compliance theme with **complete chat CRUD and
history**, one plain **Gemini Flash** call, **no retrieval yet**, guarded by login,
with **tests written first**. This is the skeleton every later RAG method plugs into.

## 2. Scope

**In:**
- Conversation CRUD: create, list, open (read + history), rename (update), delete.
- Persisted `Message` history per conversation.
- One plain Gemini Flash reply per user message (no retrieval, no embeddings).
- Django built-in auth: a single login gate protecting all chat views.
- Automated tests, written test-first, mocking the LLM.
- Deployable to a live HTTPS URL.

**Out (do NOT build):**
- Any retrieval, embeddings, vector store, chunking (that is Stage 1+).
- Separate SPA / React / DRF API.
- Multi-tenant sharing, streaming responses, WebSockets.
- Polished styling — functional HTML is enough.

## 3. Stack (locked)

| Layer | Choice |
|---|---|
| Web | Django 6.0 (templates + **HTMX** via CDN), **no DRF** |
| Auth | `django.contrib.auth`, `@login_required` on all chat views |
| DB | **Existing Postgres**, via `DATABASE_URL`; enable `pgvector` (for Stage 1, not used in Stage 0) |
| LLM | Gemini Flash through `google-genai` (already working in `scratch_rag.py`) |
| Server (prod) | `gunicorn` + `whitenoise` for static files |
| Deploy | Container (Dockerfile provided) to any Python host |

> **Python note:** environment is Python 3.14.5. Django 6.0.7 is confirmed working on it.
> Do not downgrade Django below 6.0 (older versions do not officially support 3.14).

## 4. Prerequisites / environment variables

Create/extend `.env` at repo root (already git-ignored). The implementer must set:

```
GEMINI_API_KEY=...          # already present and working
DATABASE_URL=postgres://USER:PASS@HOST:PORT/DBNAME
DJANGO_SECRET_KEY=...        # generate a random 50-char string
DJANGO_DEBUG=true            # false in production
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1   # add the deploy host later
```

One-time DB setup (Stage 1 readiness; harmless for Stage 0):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
The `DATABASE_URL` user needs `CREATEDB` privilege so Django can create the test database.

## 5. Dependencies

Add to `requirements.txt` (pin to versions resolved in the venv):
```
django>=6.0,<6.1
psycopg[binary]
dj-database-url
python-dotenv
google-genai
gunicorn
whitenoise
pytest
pytest-django
```

## 6. Target file tree

```
manage.py                      # at repo root; inserts src/ onto sys.path
pytest.ini
requirements.txt
Dockerfile
src/
  config/
    __init__.py
    settings.py
    urls.py
    wsgi.py
  chat/
    __init__.py
    apps.py
    models.py
    admin.py
    views.py
    urls.py
    gemini.py                  # the single LLM seam (mockable)
    migrations/__init__.py
    templates/chat/
      base.html
      login.html
      conversation_list.html
      conversation_detail.html
      _message.html            # HTMX partial: one message turn
tests/
  __init__.py
  conftest.py
  test_models.py
  test_views.py
```

## 7. Settings (`src/config/settings.py`)

- Load `.env` with `python-dotenv` at top.
- `SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]`.
- `DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"`.
- `ALLOWED_HOSTS` from `DJANGO_ALLOWED_HOSTS` (comma-split).
- `DATABASES = {"default": dj_database_url.config(conn_max_age=600, ssl_require=not DEBUG)}`.
- `INSTALLED_APPS`: default Django apps + `"chat"`.
- Add `whitenoise.middleware.WhiteNoiseMiddleware` right after `SecurityMiddleware`.
- `STATIC_URL="/static/"`, `STATIC_ROOT=BASE_DIR/"staticfiles"`, whitenoise storage.
- `LOGIN_URL="/login/"`, `LOGIN_REDIRECT_URL="/"`, `LOGOUT_REDIRECT_URL="/login/"`.
- `CSRF_TRUSTED_ORIGINS` from env for the deploy host.

`manage.py` and `wsgi.py` must `sys.path.insert(0, str(BASE_DIR / "src"))` and set
`DJANGO_SETTINGS_MODULE=config.settings`.

## 8. Models (`src/chat/models.py`)

```python
class Conversation(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=200, default="New conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-updated_at"]

class Message(models.Model):
    ROLE_CHOICES = [("user", "user"), ("assistant", "assistant")]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["created_at"]
```
Run `makemigrations chat` and commit the migration file.

## 9. LLM seam (`src/chat/gemini.py`)

One function, so tests can mock it and Stages 1–4 can extend it:
```python
def generate_reply(history: list[dict]) -> str:
    """history: [{"role": "user"|"assistant", "content": str}, ...] → assistant text.
    Stage 0: plain Gemini Flash, no retrieval. Later stages augment `history`/prompt here."""
```
- Build a `genai.Client(api_key=os.environ["GEMINI_API_KEY"])`.
- Model: `gemini-2.5-flash` (confirmed working). Send the conversation history as context.
- Return `response.text`. Keep all Gemini specifics inside this module.

## 10. URLs + Views (`src/chat/urls.py`, `views.py`)

All views `@login_required`. Use plain function views + Django forms/POST; no DRF.

| Method+Path | View | Behavior |
|---|---|---|
| `GET /login/`, `POST /login/` | Django `LoginView` (template `login.html`) | Auth |
| `POST /logout/` | Django `LogoutView` | Auth |
| `GET /` | `conversation_list` | List current user's conversations + "New" button |
| `POST /conversations/` | `conversation_create` | Create empty conversation, redirect to detail |
| `GET /conversations/<id>/` | `conversation_detail` | Show messages (history) + message form |
| `POST /conversations/<id>/messages/` | `message_create` | Save user msg → call `generate_reply(history)` → save assistant msg → **return `_message.html` partial** (HTMX swap) or redirect if non-HTMX |
| `POST /conversations/<id>/rename/` | `conversation_rename` | Update `title` |
| `POST /conversations/<id>/delete/` | `conversation_delete` | Delete, redirect to list |

**Ownership guard:** every conversation view must filter by `owner=request.user`
(use `get_object_or_404(Conversation, id=..., owner=request.user)`), so users cannot
touch others' conversations.

## 11. Templates (HTMX via CDN in `base.html`)

- `base.html`: minimal HTML, `<script src="https://unpkg.com/htmx.org">`, block for content, logout button.
- `login.html`: Django auth form.
- `conversation_list.html`: list with rename/delete forms + "New conversation".
- `conversation_detail.html`: message history (loop `_message.html`) + a form that
  `hx-post`s to the messages endpoint and appends the returned partial.
- `_message.html`: renders one message (role + content). Reused by the HTMX response.
- Include `{% csrf_token %}` in every POST form; configure HTMX to send the CSRF header.

## 12. Tests — WRITE THESE FIRST (`tests/`)

Use `pytest` + `pytest-django`. `pytest.ini`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
pythonpath = src
python_files = test_*.py
testpaths = tests
```
`conftest.py`: fixtures for a logged-in `client` and a test user.

**`test_models.py`:**
- `test_conversation_defaults` — new conversation has default title, is owned, timestamps set.
- `test_messages_ordered_by_created` — messages return in creation order.
- `test_delete_conversation_cascades_messages` — deleting a conversation deletes its messages.

**`test_views.py` (mock the LLM — never call the real API in tests):**
Mock `chat.gemini.generate_reply` with `monkeypatch`/`unittest.mock` to return a fixed string.
- `test_login_required_redirects` — anonymous GET `/` redirects to `/login/`.
- `test_create_conversation` — POST creates a conversation owned by the user.
- `test_load_history` — detail view shows previously saved messages.
- `test_post_message_saves_user_and_assistant` — posting a message stores a `user`
  message and an `assistant` message; `generate_reply` was called once with history.
- `test_rename_conversation` — POST rename updates the title.
- `test_delete_conversation` — POST delete removes it; it no longer appears in the list.
- `test_cannot_access_others_conversation` — user B gets 404 on user A's conversation.

**Test-first loop:** write each test, run `pytest`, watch it fail (red), implement until
green. Do not skip the red step.

## 13. Verify locally

```bash
source .venv/bin/activate
python manage.py makemigrations && python manage.py migrate
python manage.py createsuperuser        # to log in
pytest                                    # all green
python manage.py runserver                # click through: create, chat, rename, delete
```

## 14. Deploy

- **Dockerfile:** python:3.14-slim base → install `requirements.txt` → `collectstatic`
  → `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
- Set env vars on the host: `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`,
  `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `GEMINI_API_KEY`.
- Run `migrate` on release. Confirm a live HTTPS URL that stays up for later stages.
- Save the URL + a screenshot into `proof/`.

## 15. Acceptance criteria (README Stage 0 exit)

- [ ] App works as a normal chatbot behind a login.
- [ ] Full conversation CRUD + persisted history, scoped to the owner.
- [ ] Exactly one Gemini Flash call per user message; **no retrieval anywhere**.
- [ ] All tests written test-first and passing; LLM is mocked in tests.
- [ ] Live deployed HTTPS URL.
- [ ] There is a clear seam (`chat/gemini.py`) where retrieval will plug in later.

## 16. Docs to update on completion

- `docs/requirements.md` — Stage 0 section (problem, scope, definition of done).
- `docs/test-plan.md` — the test cases above.
- `docs/reflection.md` — a few lines.
- `docs/system-diagram.drawio` — reflect the Stage 0 architecture.
- `LEARNING_LOG.md` — only if a `teach me` concept was run (Stage 0 is mostly known scaffolding).
