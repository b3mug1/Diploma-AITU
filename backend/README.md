# Backend API

This FastAPI backend provides student and locker registries, assignments, authenticated accounts, in-app notifications, an administrator audit history, and aggregate reports. It is intended for local development with synthetic data.

## Run locally

Requires Python 3.11 or later. From the `backend` directory:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
py -m alembic upgrade head
py -m app.bootstrap
py -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI documentation is at `/docs`. The default database is a local SQLite file. Set `DATABASE_URL` in `.env` to a PostgreSQL connection string when that database is ready. The bootstrap command prompts for the first administrator's username and password; no default password is shipped.

The previous unauthenticated registry API is now protected: administrator credentials are required for student and locker registries and all mutations. Students may read only their own assignments. Sign in with `POST /api/v1/auth/login`, then pass `Authorization: Bearer <access_token>` to protected endpoints. Administrators can create student accounts with `POST /api/v1/users` after creating the corresponding student record. Tokens expire after eight hours and can be revoked through logout. Existing clients must add this authentication flow.

### Existing prototype database

Back up the database before upgrading. If it was created by the old `create_all` startup and contains the original `students`, `lockers`, and `assignments` schema, stop the old API and run `py -m alembic stamp 0001` followed by `py -m alembic upgrade head`. Check the schema before stamping: never stamp an empty or modified database. A new database should run only `py -m alembic upgrade head`. Startup no longer creates tables automatically.

## Initial endpoints

All routes use the `/api/v1` prefix by default.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | API process health |
| `POST`, `GET` | `/students` | Create and list student registry records |
| `POST`, `GET` | `/lockers` | Create and list lockers; optionally filter with `?status=available` |
| `PATCH` | `/lockers/{id}/status` | Update a locker status subject to active-assignment constraints |
| `POST`, `GET` | `/assignments` | Create and list assignments |
| `POST` | `/assignments/{id}/end` | End an active assignment and release the locker |
| `POST` | `/auth/login`, `/auth/logout` | Create or revoke an eight-hour bearer session |
| `GET` | `/auth/me` | Inspect the current account |
| `POST` | `/users` | Administrator creates a student or administrator account |
| `POST` | `/users/{id}/deactivate` | Administrator deactivates an account and revokes its sessions |
| `GET` | `/notifications` | Current user's notifications; `?unread_only=true` and pagination supported |
| `POST` | `/notifications/{id}/read` | Mark one owned notification read |
| `GET` | `/admin/audit-events` | Administrator event history, optionally filtered by `action` or `actor_id` |
| `GET` | `/admin/reports/summary` | Aggregate locker status, assignment, student, and occupancy counts |
| `GET` | `/admin/reports/locations` | Locker counts by location and status |

Assignment creation and ending create notifications for the linked student account. Changes to a locker into `maintenance` or `out_of_service` notify other active administrators. Notifications are stored in the database and retrieved by polling; no email, push service, or frontend integration is included. Users without an account do not receive notifications. The audit history records successful registry, assignment, locker-status, and account-management actions with actor, entity, action, and time; failed transactions leave no event. Login and notification reads are not included in this business-event history.

Reports are live aggregates of current database records. Occupancy rate is `occupied lockers / all lockers * 100`; an empty registry returns 0. The location report groups lockers without a location as `Unspecified`. No personal student information is included in these reports.

## Work remaining for backend completion

- Repair-ticket models, endpoints, permissions, and approved lifecycle.
- Production-ready transaction/concurrency review and database migration validation on PostgreSQL.
- PostgreSQL/Docker Compose integration, environment and deployment configuration.
- API integration with the frontend and implementation of the agreed validation and verification plan.

Do not expose this prototype to a public network or use real student information. Before shared deployment, add TLS, login rate limiting, backups, account recovery, and a reviewed data-retention policy for notifications and audit events.

## Checks

Install `requirements-dev.txt`, then run `py -m pytest -q`, `py -m ruff check app tests alembic`, and `py -m alembic check` against a migrated test database. Tests are written for notification ownership, administrator-only access, reports, and rollback of failed mutations.
