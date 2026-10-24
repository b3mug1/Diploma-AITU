# Locker Management System

**Diploma project topic:** “Development of an Information System for Managing Locker Allocation and Operations in an Educational Institution.”

The project concerns a web-based system for maintaining locker records, assignments, and fault reports. An initial working prototype now includes a role-aware React interface, a FastAPI API, PostgreSQL migrations, and a Docker Compose setup. The current process and user needs still require empirical validation.

## Problem and objective

According to the team's initial description, lockers are allocated manually and there is no unified service for recording and maintaining them. These claims have not yet been independently verified and are treated as hypotheses.

The project objective is to design, implement, and evaluate a system that supports locker records, assignments, and repair requests based on requirements validated by users and the organisation. Automated allocation is a conditional feature: its rules must be approved by the process owner before implementation.

## Target roles

- **Student** — views their own assignment and, if the process is confirmed, submits and tracks a repair request.
- **Administrator** — maintains registries and manages assignments and requests within approved authority.
- **Technician** — handles assigned requests and records repair outcomes.

The roles and permissions are provisional and require approval.

## Project scope

The provisional scope includes digital student and locker registries, assignment records, role-based access, and repair-request handling. Electronic locks, RFID and other physical-access technologies, payments, a mobile application, and integration with university systems are excluded from the baseline scope.

Social status, academic performance (GPA), and activity are not approved allocation criteria. Collecting or using them requires separate justification and approval.

## Provisional technologies

The proposed stack is React and Vite for the web client, FastAPI and SQLAlchemy for the server, PostgreSQL for data storage, and Docker Compose for local deployment. WebSocket is a possible future option for updating the interface; it is not currently implemented.

## Project materials

- [Pre-defence report](Locker_Management_System_Pre_Defence_Report.docx)
- [Backend API and setup guide](backend/README.md)
- [Frontend features and setup guide](frontend/README.md)
- [Local Docker Compose configuration](compose.yaml)
- [Student questionnaire](https://forms.gle/SWRtDB8ZSErLt4qG6) — verify the form settings and consent-filtered results before citing the responses.

## Team

| Member | Study group | GitHub | Responsibility |
|---|---|---|---|
| Murat Bekzat Gizatuly | SE-2401 | [b3mug1](https://github.com/b3mug1) | Backend Developer / Team Lead; initial FastAPI registry and assignment API |
| Amanbek Nazarbek Toleubekuly | SE-2401 | [nazarrbek](https://github.com/nazarrbek) | Backend Developer / DevOps; remaining backend workflows and Docker setup |
| Sandybaev Daniyal Gabitovich | SE-2401 | [hqvnd](https://github.com/hqvnd) | Frontend Developer / QA; frontend implementation and interface verification |

**Academic supervisor:** Latuta Konstantin Nikolayevich.

## Project management and running the project

### Frontend

The React 18 + Vite frontend is in [`frontend/`](frontend/README.md). Administrators can manage locker and student registries, assignments, user accounts, and repair tickets. Students can view their assignments, submit repair requests, and track their status. Technicians can view assigned tickets, start work, and record repair outcomes. Run `npm ci` and `npm run dev` from `frontend/` with a local backend. The production Dockerfile and Nginx configuration are also included.

Project tasks are tracked on the [YouTrack Agile board](https://nazarbek.youtrack.cloud/agiles/204-1/current). Dates, assignees, and statuses should be kept consistent with the pre-defence materials.

The FastAPI backend is in [`backend/`](backend/README.md). It covers student and locker registries and locker assignments, using SQLite locally and a configurable PostgreSQL URL. It now includes revocable bearer sessions, server-side roles, scoped repair workflows, Alembic migrations and Docker Compose. The backend README contains local run instructions. Do not commit passwords, API keys, or personal data; use synthetic records during development.

## Current status

An initial analysis-and-design package and a working prototype have been prepared. The prototype supports the three user roles and the main locker-assignment and repair workflows. The preliminary summary of eight survey submissions still requires verification of consent filtering and denominators. Remaining work includes validating the current process and requirements with stakeholders, evaluating the interface with users, confirming role permissions and repair rules, reviewing production deployment needs, and obtaining verified substantive supervisor feedback. Tasks are tracked on the [YouTrack Agile board](https://nazarbek.youtrack.cloud/agiles/204-1/current).


## Run the complete local stack

Requires Docker Desktop (or Docker Engine) and Docker Compose v2.
From the repository root:

```sh
cp .env.example .env
# Set POSTGRES_PASSWORD to a random URL-safe value in .env.
docker compose up --build -d
docker compose exec backend python -m app.bootstrap
```

Open http://localhost:8080 and sign in with the administrator you just created.
`WEB_PORT` in `.env` changes the port. No default passwords are shipped.
Compose starts PostgreSQL, waits for database health, runs Alembic in a one-shot
`migrate` service, then starts the API and Nginx frontend after readiness checks.
The API and database are not published to host ports. The UI listens on loopback.
The API prefix in this stack is fixed at `/api/v1` to match Nginx and the frontend.

```sh
docker compose ps -a
docker compose logs migrate backend
docker compose exec backend alembic current
docker compose down
```

Database records persist in the `postgres_data` named volume across shutdowns.
Do not remove this volume unless intentionally discarding the database.
On upgrades, rerun `docker compose up --build -d` and inspect migration logs.
Environment configuration and credentials belong in ignored `.env` files.
See [backend instructions](backend/README.md) for permissions, API examples,
legacy database migration and verification. Repair rules and role permissions
are provisional and still require organisational approval.
