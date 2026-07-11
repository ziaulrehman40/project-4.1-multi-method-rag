# Test Plan

## Stage 0 objective and scope

Confirm the authentication gate, owner isolation, complete conversation lifecycle,
persisted chronological history, and the single mockable Gemini call. Retrieval and real
Gemini network behavior are deliberately excluded from automated tests.

## Test environment

- Python 3.14.5, Django 6.0.7, pytest 9.1.1, pytest-django 4.12.0.
- Local Postgres.app database; pytest creates and drops its isolated test database.
- `chat.gemini.generate_reply` is replaced with a `Mock` for message submission.

## Automated test cases

| ID | Description | Expected result | Status |
|---|---|---|---|
| M-01 | Create conversation with defaults | Owner, default title, and timestamps are set | Pass |
| M-02 | Create two messages | Related messages read in creation order | Pass |
| M-03 | Delete conversation | Related messages cascade-delete | Pass |
| V-01 | Anonymous list request | Redirects to `/login/?next=/` | Pass |
| V-02 | Create conversation | Owned record is created and detail redirect returned | Pass |
| V-03 | Load detail history | Persisted user and assistant text is rendered | Pass |
| V-04 | Submit a message | Both roles persist; mock called once with full history | Pass |
| V-05 | Rename conversation | Title changes | Pass |
| V-06 | Delete conversation | Record disappears and no longer renders in list | Pass |
| V-07 | Access another owner's conversation | Detail/message/rename/delete each return 404 | Pass (4 cases) |

Run: `.venv/bin/python -m pytest -q` with the Stage 0 environment configured.
Result on 2026-07-11: **13 passed**.

## Manual acceptance and known gaps

Required click path: anonymous gate → login → create → chat → reload/history → rename →
delete, plus a second-user ownership URL. The local database and server are prepared, but
the automated environment exposed no controllable browser, so visual click-through remains
to be repeated on the deployed host. The live HTTPS smoke test and screenshot also require
the selected host account.
