# CricManage India

Digital Management System for Indian Cricket Clubs & Academies.

## Tech stack used

- **Frontend**: HTML (Jinja templates) + Tailwind CSS (CDN) + Chart.js (CDN)
- **Backend**: Python Flask (sessions + role-based login)
- **Database**: SQLite (Flask-SQLAlchemy)
- **Prod server (deployment)**: Waitress (WSGI)

## Features

- **Admin Portal (Coach/Manager)**
  - Squad management (roles: Openers, Middle Order, Spinners, Pacers, Wicket-keeper)
  - Fixture scheduler (Opponent, Venue, Match Type, Date/Time)
  - Playing XI builder (select exactly 11)
  - Post-match score entry (batting + bowling)
  - Create Player Portal logins linked to player profiles
- **Player Portal (Athlete)**
  - Player dashboard with career totals and current-form charts
  - Runs per match and wickets per match charts (Chart.js)
  - Starting XI reminder for the upcoming fixture
  - Squad view (teammates + specialties)

## Project documentation

See `docs/PROJECT_DOCUMENTATION.md` for:
- Full feature breakdown (role-wise)
- Database schema
- Route map
- Suggested future improvements

## Run locally (first time, VS Code on Windows)

### 1) Requirements

- **Python 3.10+** installed (recommended 3.11+)
- VS Code with **Python** extension

### 2) Open in VS Code

- Open folder: `e:\crikcmana`

### 3) Create and activate a virtual environment (recommended)

In **PowerShell** (VS Code terminal):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 4) Run the app

```powershell
$env:PORT=5001
py app.py
```

Open **`http://127.0.0.1:5001`**.

## Demo credentials

- Admin: `admin` / `admin123`

## Core flows

- Admin
  - Squad: `/admin/players`
  - Fixtures: `/admin/fixtures`
  - Playing XI builder: open a fixture → Playing XI
  - Scorecard: open a fixture → Scorecard (marks match Completed)
  - Player logins: edit a player → create Player Portal login

- Player
  - Dashboard (career totals + charts + lineup reminder): `/player`
  - Squad view: `/player/squad`

## Notes

- SQLite DB file is created automatically on first run at `instance/cricmanage.sqlite3`.
- Default port is **5001** (or set `PORT`).

## Deploy to Render.com

Yes, this project is **easy to deploy** to Render.

### Option A (recommended): Render Blueprint

- This repo includes `render.yaml`
- In Render, choose **New → Blueprint**, connect your GitHub repo, and deploy.

Start command used:
- `waitress-serve --listen=0.0.0.0:$PORT app:app`

### SQLite persistence on Render (important)

Render’s filesystem can be **ephemeral** unless you attach a **Disk**.

- If you want the data to persist, create a Render Disk (example mount: `/var/data`)
- Set env var:
  - `SQLITE_PATH=sqlite:////var/data/cricmanage.sqlite3`

Without a disk, your SQLite data may reset on redeploy.

