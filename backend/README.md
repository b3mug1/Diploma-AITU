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
| POST | `/auth/change-password` | Current user; requires current and new password, revokes all sessions |
| POST, GET | `/users` | Administrator creates/lists accounts |
| POST | `/users/{id}/deactivate` | Administrator; revokes all sessions; cannot deactivate self |
| POST | `/users/{id}/activate` | Administrator; restore a deactivated account |
| POST | `/users/{id}/reset-password` | Administrator; set another user's password and revoke their sessions |
| POST, GET | `/students` | Administrator registry |
| PATCH | `/students/{id}` | Administrator; edit code/name in place |
| POST | `/students/import` | Administrator; atomic, create-only CSV import |
| POST, GET | `/lockers` | Administrator registry; optional `?status=available` |
| PATCH | `/lockers/{id}` | Administrator; edit number/location in place |
| POST | `/lockers/import` | Administrator; atomic, create-only CSV import |
| GET | `/lockers/{id}` | Administrator; student for an assigned or personally reported locker; technician for a locker linked to an assigned request |
| PATCH | `/lockers/{id}/status` | Administrator; assignment and repair guards |
| POST | `/assignments` | Administrator; only available lockers with no active repair |
| GET | `/assignments` | Administrator: all; student: own; technician: denied |
| POST | `/assignments/{id}/end` | Administrator; releases locker or holds it for open repair |
| POST | `/repairs` | Student: currently assigned locker only; administrator: any locker |
| GET | `/repairs`, `/repairs/{id}` | Administrator: all; student: own reports; technician: assigned reports |
| POST | `/repairs/{id}/assign` | Administrator assigns/reassigns an open or assigned ticket to active technician |
| PATCH | `/repairs/{id}/status` | Assigned technician or administrator, subject to transitions below |
| GET | `/notifications` | Current user's notifications; supports `?unread_only=true` and pagination |
| POST | `/notifications/{id}/read` | Mark an owned notification as read |
| GET | `/admin/audit-events` | Administrator-only action history; optional `action` and `actor_id` filters |
| GET | `/admin/reports/summary` | Administrator-only locker, assignment, student and occupancy totals |
| GET | `/admin/reports/locations` | Administrator-only locker counts by location and status |

List endpoints accept `offset` (>=0), `limit` (1–100, default 50).
`/assignments` defaults to `active_only=true`; `/repairs` accepts a `status` filter.
Student users require a unique `student_id` referencing the student registry;
admin and technician accounts must not have a student link. No GPA, social status,
or automatic allocation rules are implemented.
Passwords must be 12–128 characters. After a password change or administrator reset,
the affected user must sign in again. Passwords are never returned by the API;
successful password and account-status changes are recorded in the audit history.

Notifications are stored in the database and retrieved through the API; email,
push delivery and frontend integration are not included. Students with an active
account are notified when their locker assignment starts or ends. Technicians and
repair reporters are notified as a request progresses; administrators are notified
about new repair requests and lockers moved to maintenance or out of service.
Users without an account cannot receive notifications. Audit events record
successful registry, assignment, repair and account changes in the same transaction
as the change. They include the actor, action, entity and time; login and notification
reads are outside this business-event history.

Reports are live aggregates with no student names. Occupancy rate is occupied
lockers divided by all lockers, multiplied by 100; an empty registry returns 0.
Lockers without a location are grouped as `Unspecified`.

Example user JSON (administrator bearer header required):

```json
{"username":"student-example","password":"choose-a-unique-password","role":"student","student_id":1}
```

## Registry editing and CSV imports

`PATCH /students/{id}` accepts `student_code` and/or `full_name`.
`PATCH /lockers/{id}` accepts `locker_number` and/or `location`; send
`{"location":null}` to clear a location. For example:

```sh
curl -X PATCH http://127.0.0.1:8000/api/v1/students/1 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"student_code":"SYN-002","full_name":"Synthetic Student"}'
```

At least one field is required. Unknown fields, null required fields, blank
identifiers/names, NUL characters and overlong values return 422. Identifiers
are limited to 64 characters; names and locations to 200. Leading/trailing
whitespace is trimmed. Identifiers remain case-sensitive, matching the existing
registry uniqueness policy. Duplicate identifiers return 409; missing records
return 404. No-op updates succeed without another audit event. Record IDs,
creation timestamps, linked accounts, active/ended assignments and repairs are
preserved. Locker status can only be changed through the existing guarded
`PATCH /lockers/{id}/status` endpoint.

Imports accept the CSV file as the **raw request body** with
`Content-Type: text/csv`, rather than multipart form data or JSON. Use UTF-8
(optional BOM), comma separators, and a header row. Column order may vary;
unknown, repeated or missing required headers are rejected.

Students (`student_code` and `full_name` are both required):

```csv
student_code,full_name
SYN-001,Synthetic Student
SYN-002,"Example, Student"
```

Lockers (`locker_number` required; `location` optional):

```csv
locker_number,location
SYN-A1,Floor 1
SYN-A2,
```

```sh
curl -X POST http://127.0.0.1:8000/api/v1/students/import \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: text/csv' \
  --data-binary @students.csv
# For lockers: use /api/v1/lockers/import and @lockers.csv
```

A successful import returns **201** with `{"created":2}`. Imports only create
records: existing identifiers are errors and never overwrite registry entries.
New lockers are always `available`; CSV cannot set status, IDs or assignments.
Empty/omitted CSV locations become null. Files are limited to 1 MiB and 1000 data
rows (413); other content types return 415. CSV quoting supports commas and
newlines in fields; completely blank lines are ignored. Headers and empty files
are checked before writes.

Every row is validated before insertion. Errors return **422**, for example:

```json
{
  "detail": {
    "message": "Import rejected; no rows saved.",
    "errors": [
      {"row": 3, "field": "student_code", "message": "Duplicate identifier in CSV."},
      {"row": 4, "field": "full_name", "message": "String should have at least 1 character"}
    ]
  }
}
```

Row numbers are physical CSV line numbers (header is line 1); a multiline record
uses its ending line. Encoding/header errors identify line 1. Validation gathers
row errors across the file; malformed CSV stops parsing at the broken record.
Any validation error rejects the whole file. Database unique constraints remain
the final protection against concurrent inserts/edits: a late conflict returns
**409** with row details and rolls back all inserted rows and their audit events.
Correct the file or refresh the registry before retrying.

`GET /admin/audit-events?offset=0&limit=50` returns the existing administrator-only
audit history, including registry events. The existing `action` and `actor_id`
filters remain available.
Each includes actor ID/username, `occurred_at`, `entity_type` (`student`/`locker`),
record ID, action (`student.created`, `student.updated`, `student.imported`,
`locker.created`, `locker.updated`, `locker.imported`, `locker.status_changed`),
and `before`/`after` values. Create/import events have `before:null`. Existing
events and non-registry events may have null snapshots. Successful edits, direct creates,
manual status changes and each imported row are logged in the same transaction
as the record change; failed operations leave no successful-change events.
Assignment, repair and account events continue to use the same audit log;
this change adds field snapshots for direct registry edits and imports.
There is no API for modifying/deleting audit entries. This is a database audit
log, not a tamper-proof external archive; access to personal data must follow
the deployment's approved permissions and retention policy.

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
`0001` represents the original registry schema; `0002` adds users, sessions, repairs;
`0003` adds notifications and audit events. `0004` adds nullable before/after
snapshots to existing audit events; it preserves registry records, assignment
history, and existing audit entries. Run `alembic upgrade head` before starting
this version. Downgrading to `0003` removes snapshots but retains audit events.

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
`alembic downgrade 0001` removes accounts, sessions, repairs, notifications and audit events;
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
named schema; the role needs schema creation permissions. Opt-in tests verify
migrations, competing assignments/repair operations, and competing student/locker
CSV imports after duplicate prechecks. The default suite checks
SQLite, role/ownership isolation, session expiry/logout/deactivation, lifecycle
validation, registry editing, CSV error reporting and full rollback, transactional
audit events, OpenAPI contracts, and preservation of legacy assignment history
and audit entries during upgrades.

## Deployment and limits

Use the repository-root Compose instructions. The checked-in `requirements.lock`
records the dependencies used for the Linux container. Regenerate deliberately
with `uv pip compile backend/requirements.txt -o backend/requirements.lock`.

Compose binds the UI to loopback, keeps PostgreSQL/API on the internal network,
and rate-limits login attempts at Nginx. For a shared deployment configure TLS,
trusted proxy settings, backups and restore procedures, monitoring and a reviewed
permissions policy. The baseline has no password recovery, MFA, institutional SSO,
tamper-resistant audit storage, or automated allocation. Student and
technician workflows currently use the API; the web UI is the administrator
registry with login/logout. Business validation and approval remain external work.
