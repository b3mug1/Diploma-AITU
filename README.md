# Locker Management System

**Diploma project topic:** “Development of an Information System for Managing Locker Allocation and Operations in an Educational Institution.”

The project concerns a web-based system for maintaining locker records, assignments, and fault reports. The project remains in analysis and design, with a FastAPI backend for registry, authentication and repair workflows now available. The current process and user needs still require empirical validation.

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

The proposed stack is React and Vite for the web client, FastAPI and SQLAlchemy for the server, PostgreSQL for data storage, and Docker Compose for local deployment. WebSocket is one option for updating the interface. All choices are provisional; alternatives and selection criteria are documented in the [technology comparison](docs/technology-comparison.md).

## Documentation

- [Project proposal](docs/project-proposal.md)
- [User research](docs/user-research.md)
- [Questionnaire text](docs/google-form-questionnaire.md)
- [Preliminary survey results](docs/survey-results.md)
- [Student Google Form](https://forms.gle/SWRtDB8ZSErLt4qG6) — verify the actual form settings and responses
- [Literature review](docs/literature-review.md)
- [Existing-system comparison](docs/system-comparison.md)
- [Technology comparison](docs/technology-comparison.md)
- [Requirements and acceptance criteria](docs/requirements.md)
- [Architecture and diagrams](docs/architecture.md)
- [Scenarios and prototype](docs/prototype.md)
- [Verification and evaluation plan](docs/evaluation-plan.md)
- [Project management and risks](docs/project-management.md)
- [Draft supervisor feedback for confirmation](docs/supervisor-feedback.md)
- [Pre-defence checklist](docs/pre-defense-checklist.md)
- [System context diagram for draw.io](diagrams/system-context.drawio)
- [Use-case diagram for draw.io](diagrams/use-case.drawio)
- [Component diagram for draw.io](diagrams/component.drawio)
- [Mermaid sources and SVG exports](diagrams/)

## Team

| Member | Study group | GitHub | Responsibility |
|---|---|---|---|
| Murat Bekzat Gizatuly | SE-2401 | [b3mug1](https://github.com/b3mug1) | Backend Developer / Team Lead; initial FastAPI registry and assignment API |
| Amanbek Nazarbek Toleubekuly | SE-2401 | [nazarrbek](https://github.com/nazarrbek) | Backend Developer / DevOps; remaining backend workflows and Docker setup |
| Sandybaev Daniyal Gabitovich | SE-2401 | [hqvnd](https://github.com/hqvnd) | Frontend Developer / QA; frontend implementation and interface verification |

**Academic supervisor:** Latuta Konstantin Nikolayevich.

## Project management and running the project

### Frontend

The initial React 18 + Vite frontend is in [`frontend/`](frontend/README.md). It includes locker and student registries, assignment creation and completion, search, status filters, and API error handling. Run `npm ci` and `npm run dev` from `frontend/` with the backend on port 8000. The frontend directory also includes a production Dockerfile and Nginx configuration; see its README for backend network requirements. Administrator login/logout is connected to the API. Student/technician and repair-specific UI pages remain frontend work.

Project tasks are tracked on the [YouTrack Agile board](https://nazarbek.youtrack.cloud/agiles/204-1/current). Dates, assignees, and statuses should be kept consistent with the pre-defence materials.

The FastAPI backend is in [`backend/`](backend/README.md). It covers student and locker registries and locker assignments, using SQLite locally and a configurable PostgreSQL URL. It now includes revocable bearer sessions, server-side roles, scoped repair workflows, Alembic migrations and Docker Compose. The backend README contains local run instructions. Do not commit passwords, API keys, or personal data; use synthetic records during development.

## Current status

An initial set of analysis and design documents and a partial FastAPI backend have been prepared. The backend supports student and locker registries, manual assignments, authentication, server-side roles and repair requests. Versioned migrations and a local Compose stack are included. The preliminary summary of eight survey submissions requires verification of consent filtering and denominators. The following remain incomplete: confirmation of the current process, a visual prototype, approval of requirements and permissions, production deployment review, remaining role-specific frontend pages, and verified substantive feedback from the academic supervisor. Tasks are tracked on [YouTrack](https://nazarbek.youtrack.cloud/agiles/204-1/current). Individual task status is summarised in the [pre-defence checklist](docs/pre-defense-checklist.md).


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
