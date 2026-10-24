# AITU Locker frontend

React 18 + Vite administrator registry, with authenticated API requests.

## Development

Start the backend and create the first administrator using
[`../backend/README.md`](../backend/README.md), then run:

```sh
npm ci
npm run dev
```

Open http://localhost:5173 and sign in as an administrator. Vite proxies `/api`
to `http://127.0.0.1:8000`. API prefix is `/api/v1`.
`npm run build` verifies the production bundle.

The session token is kept in memory and is cleared by page reload, logout, or
an expired-session response. Logout also revokes it on the server. There are no
default credentials. Student/technician accounts use the protected API for their
workflows; those role-specific pages and the repair management UI remain future
frontend work.

## Docker

Run `docker compose up --build -d` from the repository root after configuring
`.env`. Nginx serves the bundle and proxies API requests to `backend:8000`.
The root README includes bootstrap and shutdown commands.

The UI supports locker/student registries, manual assignments and completion,
search/status filters, pagination, loading and error states. Authorization is
always enforced by the API.
