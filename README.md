<<<<<<< HEAD
# Team Effort Tracker (FastAPI + Oracle)

A lightweight web app to track individual tasks, assignment, tagging for assistance, and lead-level reporting (weekly/monthly/semester). Oracle is the primary database, wired via SQLAlchemy + cx_Oracle.

## Features
- Two-pane UI: left for team members, right for details and tasks.
- Per-member task list with add/reset/save form (hours, due date, blockers, comments, tags).
- Lead capabilities: assign tasks to others, CRUD team members, view all work, export reports as CSV.
- Tag teammates/leads for help on a task.
- Black theme with light gray/orange accents.

## Quickstart
1) Install Python 3.10+ and Oracle Instant Client (for cx_Oracle).
2) Install dependencies:
```
pip install -r requirements.txt
```
3) Set environment (example `.env`):
```
ORACLE_USER=appuser
ORACLE_PASSWORD=app_password
ORACLE_DSN=localhost:1521/FREEPDB1
# or provide DATABASE_URL=oracle+cx_oracle://user:pass@host:1521/servicename
```
4) Create schema (Oracle):
```
sqlplus appuser/app_password@localhost:1521/FREEPDB1 @backend/create_tables.sql
```
5) Run the app:
```
uvicorn backend.main:app --reload
```
6) Open http://localhost:8000 (frontend served from `/static`).

## API Highlights
- `GET /api/members` – list members.
- `POST /api/members` – create (lead only, send `X-Actor-Id` header for auth context).
- `GET /api/tasks?member_id=` – tasks for member (non-leads limited to theirs).
- `POST /api/tasks` – create task; leads can assign others; include `tags: [member_ids]`.
- `GET /api/reports?period=weekly|monthly|semester&format=csv|json` – lead-only exports.

## Frontend Notes
- Actor switcher in header sets `X-Actor-Id` for API calls (simulated auth).
- Task form toggle via “Add Task”; tags multi-select to request assistance.
- Lead panel surfaces member creation and report download buttons.

## Extending
- Add real auth/SSO and RBAC enforcement.
- Replace actor header with JWT/session.
- Enhance reporting (status filters, pivoted summaries).
- Add validation and input masks for hours/dates.

=======
# pyeffortapp
>>>>>>> 7d1970507efcf7287cd896042b48f2eba08506b1
