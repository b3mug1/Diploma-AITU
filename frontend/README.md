# AITU Locker Management frontend

React 18 + Vite interface for the three project roles. The backend API remains
the authority for authentication and permissions.

## Role features

- **Administrator:** manage student and locker registries, create assignments,
  view and close repair requests, assign technicians, and create or deactivate
  user accounts.
- **Student:** view current and previous locker assignments, submit a repair
  request for an assigned locker, and track personal requests and outcomes.
- **Technician:** view assigned repair requests, mark a repair as in progress,
  and record the resolution when work is complete.

## Local development

Start the API and create the initial administrator as described in
[`../backend/README.md`](../backend/README.md). Then run:

```sh
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to
`http://127.0.0.1:8000`; the API uses the `/api/v1` prefix. Run `npm run build`
to create a production bundle.

## Docker

From the repository root, configure `.env` and run `docker compose up --build -d`.
Nginx serves the built frontend and proxies API calls to the backend container.
The root README documents bootstrap, health checks, and shutdown commands.

Session tokens remain in memory and are cleared on logout, session expiry, or
page reload. Use synthetic records during development; do not enter real student
information in this prototype.
