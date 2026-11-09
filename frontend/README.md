# AITU Locker Management frontend

React 18 + Vite interface for the three project roles. The backend API remains
the authority for authentication and permissions.

## Role features

- **Administrator:** manage student and locker registries, create assignments,
  view and close repair requests, assign technicians, and create or deactivate
  user accounts, reactivate them, and reset another user's password.
- **Student:** view current and previous locker assignments, submit a repair
  request for an assigned locker, and track personal requests and outcomes.
- **Technician:** view assigned repair requests, mark a repair as in progress,
  and record the resolution when work is complete.
- **All roles:** change their own password after entering the current password.
  Password changes end all sessions and require a new sign-in.
- **All roles:** view personal notifications, filter unread messages, and mark
  notifications as read. Read status changes only after a successful API response.
- **Administrator:** view audit history with exact action and actor ID filters,
  the registry summary report, and locker counts by location and status.

## Notifications, audit history, and reports

The shared navigation exposes Notifications to all signed-in roles. Audit History
and Reports are visible only to administrators and are mounted only when selected.
The existing bearer-token client is used for every request; backend permissions
remain authoritative. A 401 ends the current session, while other API errors are
shown with retry controls. New screens include loading, empty, and error states.

Notifications and audit history load all API pages in batches of 100 records.
Audit filters are submitted explicitly; action matching follows the backend's
exact-match semantics. Responses from obsolete filters are ignored. Summary and
location reports load and refresh independently, so a failure in one does not hide
the other. Reports display server-provided metrics without calculating new reports.

| Screen | API |
| --- | --- |
| Notifications | `GET /notifications?unread_only=...` |
| Mark as read | `POST /notifications/{id}/read` |
| Audit history (admin) | `GET /admin/audit-events?action=...&actor_id=...` |
| Summary (admin) | `GET /admin/reports/summary` |
| Locations (admin) | `GET /admin/reports/locations` |

All paths are relative to `/api/v1`.

## Frontend QA

Use Node.js 22.12+ (22.x) or 24.x for the test runner. CI uses Node.js 22.

```sh
npm ci
npm test
npm run build
```

Vitest and React Testing Library cover notifications, read success/failure,
unread filtering, empty/loading/error states, retries, audit filters and stale
responses, independent reports, role navigation, pagination, and session errors.
Tests use synthetic API responses in jsdom. GitHub Actions runs the frontend tests
and production build alongside the existing backend and deployment checks.

For manual integration QA, sign in with each role against a running backend:

1. Create and end an assignment as admin; verify notifications appear for the
   affected student and can be marked read. Switch the unread filter and refresh.
2. As admin, open Audit History, filter by `assignment.created` and the admin ID,
   then reset filters. Confirm the new events appear.
3. Open Reports and compare totals, occupancy, and locations to registry changes.
4. Sign in as student and technician; confirm Notifications is available and
   administrative screens are absent. The backend must reject direct admin API
   calls from these sessions with 403.
5. Verify empty states on a fresh database and retry after a simulated API failure.

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
