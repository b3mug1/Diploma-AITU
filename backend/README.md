# Backend API — Initial Contribution

This FastAPI slice provides the first backend portion of the Locker Management System: student and locker registries, status updates, and locker assignments. It is intended for local development with synthetic data.

## Run locally

Requires Python 3.11 or later. From the `backend` directory:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
py -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI documentation is at `/docs`. The default database is a local SQLite file. Set `DATABASE_URL` in `.env` to the PostgreSQL connection string when the shared database and Docker Compose setup are ready.

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

## Work remaining for backend completion

- Authentication and server-side role-based access control.
- Repair-ticket models, endpoints, permissions, and approved lifecycle.
- Database migrations and production-ready transaction/concurrency review.
- PostgreSQL/Docker Compose integration, environment and deployment configuration.
- API integration with the frontend and implementation of the agreed validation and verification plan.

The current version is an initial, unauthenticated prototype. Do not expose it to a public network or use real student information. Schema creation uses `create_all` for local prototyping; replace it with versioned migrations before shared or production use.
