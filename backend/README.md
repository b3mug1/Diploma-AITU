# Locker Management API

FastAPI + SQLAlchemy, SQLite for local development, PostgreSQL for Compose.
Python 3.11+ is required. Use synthetic records during development.

## Local setup

From `backend/` (POSIX shell):

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.bootstrap
uvicorn app.main:app --reload
```

On PowerShell use `py -m venv .venv`, `.venv\Scripts\Activate.ps1`, and
`Copy-Item .env.example .env`. Bootstrap prompts for the first administrator's
username and password without echoing the password. It refuses to run when an
active administrator exists. There are no default credentials or public signup.
Administrators create subsequent users via `/users`.

Swagger UI: http://127.0.0.1:8000/docs. Login returns an opaque bearer token;
enter it using **Authorize** in Swagger. Tokens expire after `SESSION_HOURS`
(default 8, range 1–168), are stored as SHA-256 digests, and are revoked by logout
or account deactivation. Passwords use scrypt with a random per-user salt.
Usernames are case-insensitive ASCII letters, digits, `_`, `.`, and `-`.
New passwords require 12–128 characters. Passwords and hashes are never returned.

## Routes and permissions

All routes use `/api/v1` by default (`API_PREFIX` locally).

| Method | Route | Access / behavior |
|---|---|---|
| GET | `/health`, `/health/ready` | Public liveness / database readiness |
| POST | `/auth/login` | Username/password JSON; returns token and expiry |
| GET | `/auth/me` | Current authenticated account |
| POST | `/auth/logout` | Revoke current session; 204 response |
| POST, GET | `/users` | Administrator creates/lists accounts |
| POST | `/users/{id}/deactivate` | Administrator; revokes all sessions; cannot deactivate self |
| POST, GET | `/students` | Administrator registry |
| POST, GET | `/lockers` | Administrator registry; optional `?status=available` |
| GET | `/lockers/{id}` | Administrator; student for an assigned or personally reported locker; technician for a locker linked to an assigned request |
| PATCH | `/lockers/{id}/status` | Administrator; assignment and repair guards |
| POST | `/assignments` | Administrator; only available lockers with no active repair |
| GET | `/assignments` | Administrator: all; student: own; technician: denied |
| POST | `/assignments/{id}/end` | Administrator; releases locker or holds it for open repair |
| POST | `/repairs` | Student: currently assigned locker only; administrator: any locker |
| GET | `/repairs`, `/repairs/{id}` | Administrator: all; student: own reports; technician: assigned reports |
| POST | `/repairs/{id}/assign` | Administrator assigns/reassigns an open or assigned ticket to active technician |
| PATCH | `/repairs/{id}/status` | Assigned technician or administrator, subject to transitions below |

List endpoints accept `offset` (>=0), `limit` (1–100, default 50).
`/assignments` defaults to `active_only=true`; `/repairs` accepts a `status` filter.
Student users require a unique `student_id` referencing the student registry;
admin and technician accounts must not have a student link. No GPA, social status,
or automatic allocation rules are implemented.

Example user JSON (administrator bearer header required):

```json
{"username":"student-example","password":"choose-a-unique-password","role":"student","student_id":1}
```

## Provisional repair policy

These implementation rules require process-owner approval before real use.

1. Student or administrator posts `{"locker_id":1,"description":"Door hinge is broken"}`.
   Only one open/assigned/in-progress repair per locker is allowed (database index).
2. Administrator posts `{"technician_id":3}` to `/repairs/{id}/assign`:
   `open → assigned`. Reassignment is allowed while `assigned`.
3. Assigned technician or administrator patches `{"status":"in_progress"}`:
   `assigned → in_progress`.
4. They patch `{"status":"resolved","resolution":"Replaced hinge"}`:
   `in_progress → resolved`. An outcome is mandatory.
5. Administrator may cancel any nonterminal request using
   `{"status":"cancelled","resolution":"Reason for cancellation"}`.
   Resolved/cancelled tickets are terminal; a new fault requires a new request.

Creating a repair holds an available locker in `maintenance`; an occupied locker
keeps its assignment. Ending that assignment while repair is open sets
`maintenance`, so the locker cannot be reissued. Closing a ticket releases a
maintenance locker according to its active assignment; `out_of_service` remains
an explicit administrator decision. Opening a repair prevents new assignments
even while a locker is occupied. Students cannot update ticket status or inspect
other people's reports. Unauthorized ticket reads return 404.

PostgreSQL mutations lock the same locker row before checking/changing state;
partial unique indexes also prevent duplicate active assignments and repairs.
SQLite is for single-process development; PostgreSQL integration tests exercise
concurrent transactions.

## Migrations and existing prototype databases

Startup does not create or change tables. `alembic upgrade head` is mandatory.
`0001` represents the original registry schema; `0002` adds users, sessions, repairs.

For an existing database created by the original prototype, back it up, stop the
old API, and verify it contains exactly the original three tables and indexes
before adopting the baseline:

```sh
alembic stamp 0001
alembic upgrade head
python -m app.bootstrap
```

Do not stamp an empty or modified schema. For a new database use only
`alembic upgrade head`. PostgreSQL URLs must use `postgresql+psycopg://`.
`alembic downgrade 0001` removes accounts/sessions/repairs and their data;
rollback is for disposable environments or planned restoration from backup.

## Verification

```sh
pip install -r requirements-dev.txt
python -m pytest -q
ruff check app tests alembic
alembic check
```

For PostgreSQL integration, set `TEST_DATABASE_URL` to a dedicated local test
server and rerun pytest. Each integration fixture creates/removes a uniquely
named schema; the role needs schema creation permissions. Two opt-in tests verify
migrations and competing assignments/repair operations. The default suite checks
SQLite, role/ownership isolation, session expiry/logout/deactivation, lifecycle
validation, and preservation of legacy data during upgrades.

## Deployment and limits

Use the repository-root Compose instructions. The checked-in `requirements.lock`
records the dependencies used for the Linux container. Regenerate deliberately
with `uv pip compile backend/requirements.txt -o backend/requirements.lock`.

Compose binds the UI to loopback, keeps PostgreSQL/API on the internal network,
and rate-limits login attempts at Nginx. For a shared deployment configure TLS,
trusted proxy settings, backups and restore procedures, monitoring and a reviewed
permissions policy. The baseline has no password recovery, MFA, institutional SSO,
notifications, immutable audit trail, or automated allocation. Student and
technician workflows currently use the API; the web UI is the administrator
registry with login/logout. Business validation and approval remain external work.
