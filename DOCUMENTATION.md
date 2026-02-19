# Team Effort Tracker — Project Documentation

**Purpose (plain language)**
This small application helps a team track the work people do (tasks), who is responsible for those tasks, and simple reports that summarize time spent and blockers. It is split into two parts:
- A backend (server) that stores data and performs actions.
- A frontend (web page) that team members and team leads use in their browser.

This document explains what each piece of the project does in a friendly, non-technical way so non-developers can understand what is going on and what each file's role is.

---

## Quick summary of functionality
- Users can log in and out.
- Team Leads can create and manage team members.
- Members and leads can create tasks, update them, record hours and blockers.
- Members can upload profile pictures (avatars). The avatar is saved on the server so it shows across devices.
- Team Leads can run team reports (weekly/monthly/semester or custom date ranges) and export them as CSV or Excel (.xlsx) files.
- There is a small security model: passwords are stored in a safe way, and users receive a temporary token after logging in (like a temporary key) to identify themselves to the server.

---

## High-level architecture (easy description)
- Backend: the server program (Python with FastAPI) stores data in a database, enforces rules (like who can do what), and provides endpoints (addresses) the frontend calls to get or change data.
- Frontend: a single HTML file with JavaScript (`frontend/index.html`) provides the user interface. It talks to the backend endpoints to display data and make changes.
- Database: stores tables for teams, members, tasks, and small helper tables (like session tokens and tags).

---

## Files and what each one does (plain-language file-by-file)
I will list the important files and explain each in non-technical terms.

### Root files
- `README.md`
  - Short project summary and quick starting details.
- `requirements.txt`
  - A list of the third-party software (Python packages) this project needs. Programs like Pillow (image handling) and openpyxl (Excel export) are listed here.

### Backend folder (`backend/`)
This is the server-side code. Think of it as the "brain" that stores information and decides what is allowed.

- `main.py` — the main server program and the central place that defines the actions the web app can perform. Key responsibilities:
  - Serves the homepage file (`/`) so when you open the site in a browser it returns the frontend HTML.
  - Authentication (login) endpoint: checks username/password and returns a short-lived token (a secret) to keep the user logged in.
  - Change password endpoint: lets a logged-in user change their password.
  - Avatar endpoints: allow uploading an avatar picture, checking whether an avatar exists, and deleting it. Images are validated and resized before saving.
  - User management endpoints: creating, listing, editing, and removing members (only team leads can do these actions).
  - Task endpoints: list, create, update tasks, and add tags (useful to indicate related team members on tasks).
  - Reports endpoint: generates a report over a date range. It can return JSON, CSV, or Excel (.xlsx).
  - Startup seed: when the server starts and the database is empty, it creates a sample team, a lead user (`alex.lead`) and some sample tasks so you can try the app immediately.

  For non-technical readers: each endpoint is like a small service the web page calls — for example, "/api/auth/login" checks your username and password and gives you a key to remain logged in.

- `models.py` — defines how data is organized in the database (the tables and fields). Main data items:
  - `Team`: store the team name and members.
  - `Member`: store username, hashed password, real name, role (is_lead), and an `is_locked` flag to block login when needed.
  - `Task`: store title, details, hours, due date, blockers, comments, and its status (e.g., in_progress, completed).
  - `TaskTag`: a small table connecting tasks to members (used for tags).
  - `SessionToken`: store temporary login tokens and expiry times.

  In non-technical terms: this file defines what information is kept about people, teams, tasks and sessions.

- `schemas.py` — defines how data is shaped when it enters or leaves the server (request and response formats). Examples:
  - `MemberCreate` describes what information is required to create a member (username, password, name, etc.).
  - `TaskCreate` describes what the server expects when adding a task.

  For non-technical users: this is the "agreement" between the frontend and the backend about what fields are expected for each action.

- `db.py` — database connection helper. It reads environment variables (settings) to know how to connect to the database and provides a small helper function for other parts of the code to use.

  Simple explanation: it tells the server how to reach and talk to the database where the information is saved.

- `security.py` — security helpers: password hashing and token creation.
  - `hash_password`: turns a clear-text password into a secure, one-way representation (so the server never stores plain passwords).
  - `verify_password`: checks a submitted password against the secure stored version.
  - `issue_token`: generates a random token for a logged-in session.
  - `token_expiry`: returns when a token should expire.

  In plain language: this file makes sure passwords are stored safely and gives out short-lived keys for login sessions.

- `migrations/001_add_is_locked.sql` — a small SQL script that updates the database schema to add an `is_locked` column to the members table. This was added because the app needs a way to lock an account.

  Why it matters: if you add a new field in code but the database does not have the column, the server will fail when it tries to read it. Running the SQL in this file should be done on your database to keep the database and the code in sync.

- `create_tables.sql` — SQL for creating the original database schema (if you'd like to create the database from scratch manually).

### Teams (OPS / DevOPS / Infra)
The application seeds three teams by default on first startup: **OPS**, **DevOPS**, and **Infra**. Team Leads can assign members to these teams when creating or editing a member.

How it appears in the UI:
- Team Leads see a team filter to view members by team, and member entries include the team name next to career level and a subtle color to visually group team members.
- Non-leads (regular team members) see the global members list showing only name and career level — team assignments are hidden from regular members.


### Frontend folder (`frontend/`)
This is the web interface people use in the browser. The entire UI is a single HTML file with JavaScript and CSS.

- `index.html` — the full frontend. What it contains:
  - **Header / User menu:** where you see your name and avatar, open profile, change password, or logout.
  - **Team Members list:** a list on the left side with all team members; click a member to see their tasks.
  - **Team Lead panel:** additional controls shown only to users marked as `is_lead`. Leads can create members, run reports, and open the "Edit Members" modal.
  - **Tasks table:** the main area shows tasks for the selected member; you can add or edit tasks, record hours, blockers, tags, and change task status.
  - **Profile modal:** view and upload an avatar, see your name, role, and how long you've been a member.
  - **Edit Members modal:** leads can edit member details such as name, career level, lead-flag and account lock flag. They can set a new password for any member.
  - **Avatar upload:** when a user selects a picture, the frontend attempts to upload it to `/api/members/{id}/avatar`. If that fails, the browser stores the image locally (so it remains visible on the same device).
  - **Reports UI:** set date ranges or presets and generate reports; you can export them to CSV or Excel.

  Under the hood (short dev note): the frontend uses JavaScript `fetch()` calls to talk to the endpoints defined by the backend (for example, it calls `/api/tasks` to list or create tasks).

- `avatars/` — a directory where uploaded profile pictures are stored by the backend. The server serves these files so avatars are accessible from the browser.

---

## Getting the code onto a different machine

If you want to use the application on another computer (for example, a Windows
laptop) you can’t simply copy the folder over; instead push the repository to
a remote and pull it down from there. The following outline assumes the code is
stored in a Git repository accessible from your laptop (GitHub, GitLab, a
private server, etc.).

1. **Create a remote repository and push**
   - On GitHub (or your preferred host) create a new repository and mark it **public**. You can use the web UI:
     1. Log in to https://github.com.
     2. Click **+ → New repository**.
     3. Give it a name (e.g. `pyeffortapp`), choose **Public**, and click **Create repository**.
   - Back on your Linux machine run:
     ```bash
     cd /home/sam/effortapp/pyeffortapp
     git init                    # if not yet a repo
     git add .
     git commit -m "initial commit"
     git remote add origin git@github.com:yourusername/pyeffortapp.git
     git push -u origin main     # or master if that's your main branch
     ```
   - If you prefer HTTPS you can use `https://github.com/yourusername/pyeffortapp.git` instead of the SSH URL.

2. **On the Windows laptop:**
   - If you have Git installed, use the instructions below. Otherwise you can
     simply download a zip file of the repository from the public host (e.g.
     GitHub’s **Code → Download ZIP** button) and extract it into a folder
     named `pyeffortapp`.
   - If you do use Git, install Git for Windows from https://git-scm.com/download/win
     and run:
     ```bash
     git clone <your-remote-url> pyeffortapp
     cd pyeffortapp
     ```
   - After obtaining the files (by cloning or by unzipping), continue with the
     setup steps below. Using WSL or Git Bash is recommended but not required.

3. **Set up Python and dependencies on Windows:**
   - Ensure you have Python 3.10+ installed (from https://www.python.org).
   - Create a virtual environment:
     ```bash
     python -m venv .venv
     .\.venv\Scripts\activate     # PowerShell: .\.venv\Scripts\Activate.ps1
     ```
   - Install requirements:
     ```bash
     pip install -r requirements.txt
     ```

4. **Run the app:**
   ```bash
   set DATABASE_URL=sqlite:///./effort.db  # PowerShell: $env:DATABASE_URL = 'sqlite:///./effort.db'
   uvicorn backend.main:app --reload
   ```
   (the default is already SQLite, so setting `DATABASE_URL` is optional.)

5. Open a browser to `http://127.0.0.1:8000/` and the app will start with the
   same seeded data as on your original machine.

### Notes for Windows users
- Using **Windows Subsystem for Linux (WSL)** often gives a more familiar
  Unix-like environment and avoids path‑style headaches; the commands above
  can be run verbatim in WSL.
- If you clone into a folder with spaces or unusual characters, adjust the
  paths accordingly when activating the virtual environment and starting
  Uvicorn.
- You don’t need Oracle or any database server; the app uses SQLite by default.


## How to run the project (developer steps made plain)
These steps are what a developer or a slightly technical person would follow to run this on their machine. I will keep the commands and settings simple and safe.

1. Prepare a Python environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure the database. By default the code uses SQLite and will create a
   file called `effort.db` in the current directory. You can override this by
   setting a `DATABASE_URL` environment variable to any SQLAlchemy‑compatible
   URL (e.g. `postgresql://user:pass@host/dbname`). Example for a custom
   SQLite location:

```bash
export DATABASE_URL="sqlite:////path/to/your/effort.sqlite"
```

3. (Optional) apply migrations. For SQLite the startup code will automatically
   create any missing tables when you run the server, but you can also apply
   the SQL scripts in `backend/migrations/` manually if you prefer. The
   `create_tables.sql` file now contains SQLite‑compatible DDL.

4. Start the server (development):

```bash
uvicorn backend.main:app --reload
```

5. Open your browser to `http://127.0.0.1:8000/` and you should see the web UI.
   The server seeds a sample team and users if the database is empty.

---

## How to use the app (non-technical guide)
- Login: use one of the seeded users (username `alex.lead` or `bailey.dev`, password `changeme` if running from a fresh seed).
- As a Team Lead (alex.lead): you can create members, edit or delete them, lock accounts, and run team reports.
- As a Member: you can create and update your tasks, upload a profile picture, and generate a report for your own work.
- Upload avatar: open your profile, click the camera icon and select a picture. The app will attempt to upload it to the server; if it fails it saves it locally so you still see it on your device.

---

## Troubleshooting and common issues
- "ORA-00904: invalid identifier" errors mentioning `IS_LOCKED`: this happens when the code expects the `is_locked` column but the database does not have it. Fix: run the migration SQL in `backend/migrations/001_add_is_locked.sql`.
- Login failure: make sure your database has seeded users (server seeds users automatically on first run) or create a new user using the Team Lead account.
- Avatar upload fails: ensure Pillow is installed (in `requirements.txt`) and that the server has permission to write files in `frontend/avatars/`.
- Excel export fail: make sure `openpyxl` is installed (it's listed in `requirements.txt`).

---

## Security notes (important non-technical points)
- Passwords are not stored in plain text on the server; they are hashed (a one-way process) so the server cannot read your plain password. If you forget a password, the team lead can reset it for you.
- Login tokens are temporary keys: they expire after a short time (default 7 days). If you log out they are removed from your browser.
- Be careful with the database credentials in environment variables — do not share them publicly or commit them to version control.

---

## Glossary (simple definitions)
- Task: a unit of work (title + description + reported hours + status + due date).
- Member: a person using the system (has username, name, career level, and role such as Team Lead).
- Team Lead: a member with special privileges to manage team members and view team-wide reports.
- Avatar: profile picture for a member.
- Session token: a temporary secret the server gives you when you log in — it tells the server which user you are.

---

## Where to look in the code for specific behaviors
- Want to change the avatars’ max size or types accepted? See `backend/main.py` in the `upload_member_avatar` function (it uses Pillow to validate and resize the image).
- Want to change how long a login lasts? See `security.token_expiry()` in `backend/security.py`.
- Want to add a new field to members? Update `backend/models.py` and create a new migration in the `backend/migrations/` directory, then apply it to your database.
- Want to customize reports (add more columns to Excel)? Look at the `reports()` function in `backend/main.py` where it builds CSV or XLSX output.

---

## Examples (quick commands)
- Login using curl (replace username/password with real values):

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d '{"username":"alex.lead","password":"changeme"}'
```

- Request a report for the last week in CSV using your token (replace TOKEN):

```bash
curl -H "Authorization: Bearer TOKEN" "http://127.0.0.1:8000/api/reports?period=weekly&format=csv" -o weekly_report.csv
```

- Apply the `is_locked` migration (login to your database and run):

```sql
ALTER TABLE members ADD (is_locked NUMBER(1) DEFAULT 0);
UPDATE members SET is_locked = 0 WHERE is_locked IS NULL;
ALTER TABLE members MODIFY (is_locked DEFAULT 0 NOT NULL);
```

---

## Final notes and next steps
If you would like, I can:
- Produce a short user-guide with screenshots for non-technical users showing where to click to upload an avatar, create tasks, and run a report.
- Add automated migration tooling (e.g., Alembic) to make applying schema changes easier and safer.
- Add tests or simple scripts to perform health checks on the server.

If you want this document tuned for a particular audience (support staff, managers, or another role), tell me which audience and I’ll tailor it further.

---

Thank you — I can now add this file to the repository. Would you like me to commit it as `DOCUMENTATION.md`? If yes, I will save it and mark the documentation tasks as complete.