# Team Effort Tracker (FastAPI + SQLite)

A lightweight web app to track individual tasks, assignment, tagging for assistance, and lead‑level reporting (weekly/monthly/semester). Data is stored in a local SQLite database file by default.

## Features
- Two‑pane UI: left for team members, right for details and tasks.
- Per‑member task list with add/reset/save form (hours, due date, blockers, comments, tags).
- Lead capabilities: assign tasks to others, CRUD team members, view all work, export reports as CSV/XLSX.
- Tag teammates/leads for help on a task.
- Dark theme with light gray/orange accents.

## Quickstart
Before you can clone or download the code you need a public repository. You
can create one on GitHub as follows:

1. Log in to https://github.com and click **+ → New repository**.
2. Name the repo (e.g. `pyeffortapp`) and select **Public**, then click
   **Create repository**.
3. After creation you will be given a URL (SSH or HTTPS) for pushing and
   cloning. Use that URL in the commands below.

Once the remote repository exists, get a copy on the machine where you want to
run the app:

1. Obtain the repository on your machine. If you can use Git, clone it:
    ```bash
    git clone <your-remote-url> pyeffortapp
    cd pyeffortapp
    ```
   If you cannot run Git, simply download the source archive from the public
   hosting site (e.g. GitHub's **Code → Download ZIP**) and unzip into a
   directory named `pyeffortapp`.
2. Create and activate a Python 3.10+ virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate          # Windows (PowerShell): .\.venv\Scripts\Activate.ps1
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. (Optional) override the database location by setting `DATABASE_URL`, e.g.:
    ```bash
    export DATABASE_URL="sqlite:////path/to/mydb.sqlite"   # Windows: set DATABASE_URL=sqlite:///C:/path/effort.db
    ```
    Otherwise the app will use `sqlite:///./effort.db` in the project root.
5. Start the server:
    ```bash
    uvicorn backend.main:app --reload
    ```
6. Open http://localhost:8000 in your browser. The server will automatically create
   the SQLite file and seed teams/users on first run.

### Running on Windows
If you are working on a Windows laptop, use Git to clone the repo:

```bash
# in Git Bash, PowerShell, or WSL
git clone <your-remote-url> pyeffortapp
cd pyeffortapp
```

Then follow the same quickstart steps above; Python and pip commands work
identically once the virtual environment is active. Using WSL or Git Bash makes
path handling simpler, but the native PowerShell/Command Prompt will also work
if you adapt the `activate` and `set DATABASE_URL` commands.

The `backend/create_tables.sql` script contains equivalent SQLite DDL should you
wish to create the database manually, but it is not required when using the Python
startup code.

## API Highlights
- `GET /api/teams` – list teams (items include `id` and `name`).
- `GET /api/members` – list members.
- `POST /api/members` – create member (lead only).
- `PUT /api/members/{id}` – update member (lead only).
- `GET /api/tasks?member_id=` – list tasks (non‑leads restricted to self).
- `POST /api/tasks` – create task.
- `GET /api/reports?...` – export reports (JSON/CSV/XLSX).

## Frontend Notes
- Authentication uses bearer tokens stored in `localStorage`.
- The UI is a single HTML file that calls the backend endpoints via `fetch()`.
- Team leads see additional controls for managing members and running reports.

## Extending
- Add more robust authentication (JWT/SSO) and RBAC.
- Introduce automated migrations (Alembic) instead of manual SQL files.
- Add unit tests for backend endpoints.
- Modularize the frontend code for maintainability.
