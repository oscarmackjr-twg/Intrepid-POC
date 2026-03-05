# Local Development Guide

This guide covers the complete flow from a fresh clone to a running local stack. Follow each section in order.

---

## 1. Prerequisites

Ensure the following are installed before starting:

- **Python 3.11+** — verify: `python --version`
- **Node.js 18+ and npm** — verify: `node --version`
- **PostgreSQL (running locally)** — verify: `psql -U postgres -c '\l'`
- **Git**
- **GNU Make** (Linux/macOS: built-in; Windows: install via Chocolatey `choco install make` or Git for Windows)

Create the local database before running migrations:

```bash
psql -U postgres -c "CREATE DATABASE intrepid_poc;"
```

---

## 2. Initial Setup

```bash
git clone <repo-url>
cd intrepid-poc
make setup
```

`make setup` does three things:

1. Creates `backend/venv` (Python virtual environment)
2. Installs Python dependencies from `backend/requirements.txt` into the venv
3. Runs `npm install` in `frontend/`

**Windows users without `make`:** Run these commands manually:

```
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
cd ..\frontend
npm install
```

> **WSL2 users:** `make` runs correctly in WSL2, but the Makefile auto-detects the environment (`venv/bin/` on WSL/Linux, `venv\Scripts\` on native Windows). If you run `make setup` from WSL2, run all other `make` targets from WSL2 as well. See [WSL2 and PostgreSQL](#wsl2-and-postgresql) below for the database connection caveat.

---

## 3. Environment Configuration

Copy the example env file and edit it:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` to match your local setup:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/intrepid_poc` | Update if your Postgres credentials differ |
| `SECRET_KEY` | `change-me-local` | Change to any random string for local dev |
| `STORAGE_TYPE` | `local` | Leave as `local` for sample data |
| `DEV_INPUT` | `./data/sample/files_required` | Leave as-is to use sample data |

`backend/.env` is gitignored — never commit it. Only `backend/.env.example` is tracked.

---

## 4. Run Database Migrations

```bash
make migrate
```

This runs `alembic upgrade head` from the `backend/` directory.

**If you have an existing `intrepid_poc` database from before Alembic was introduced**, drop and recreate it first to avoid schema conflicts:

```bash
psql -U postgres -c "DROP DATABASE IF EXISTS intrepid_poc; CREATE DATABASE intrepid_poc;"
make migrate
```

**WSL2 users:** If `make migrate` fails with `Connection refused` — see [WSL2 and PostgreSQL](#wsl2-and-postgresql).

---

## 5. Start the Backend

```bash
make run-backend
```

The backend starts at `http://localhost:8000`.

Verify it is running:

```bash
curl http://localhost:8000/api/health
```

> Always start the backend before the frontend. The Vite dev server proxies `/api` requests to `:8000`, so the frontend will show errors if the backend is not up.

---

## 6. Start the Frontend

In a separate terminal:

```bash
make run-frontend
```

The frontend starts at `http://localhost:5173` with hot reload enabled.

Open `http://localhost:5173` in your browser. API calls are proxied to `http://localhost:8000`.

---

## 7. Running the Pipeline Locally

The repository includes a sample dataset at `backend/data/sample/files_required/`. The pipeline uses date-stamped filenames to locate input files.

**Important:** The sample files are dated `02-18-2026`, which means the pipeline processing date must be `2026-02-19` (the day after the file date).

**Via the UI:**

1. Open `http://localhost:5173`
2. Use the pipeline run form and enter processing date `2026-02-19`

**Via CLI directly:**

```bash
cd backend
venv/bin/python main.py --pdate 2026-02-19
```

**To use your own live input files** instead of sample data, set `DEV_INPUT` in `backend/.env` to point at your `files_required/` directory:

```
DEV_INPUT=/path/to/your/files_required
```

---

## 8. Development Notes

- **All backend commands must be run from the `backend/` directory.** pydantic-settings resolves `.env` relative to the current working directory. The Makefile handles the `cd backend` step automatically.
- **Alembic enum changes** (such as `UserRole`, `RunStatus`) are not auto-detected — write manual migration steps if you modify these enums.
- **`backend/.env` is gitignored** — never commit it. Only `backend/.env.example` is tracked.
- **Frontend proxy:** The Vite dev server (`vite.config.ts`) proxies all `/api` requests to `http://localhost:8000`. This is configured automatically — no manual proxy setup needed.

---

## 9. WSL2 and PostgreSQL

If you run `make` from WSL2 and Postgres is installed on Windows (not inside WSL2), the connection will be refused — WSL2's `localhost` is isolated from Windows' `localhost`.

**Option A — Run database commands from Windows PowerShell (quickest):**

```powershell
cd backend
.\venv\Scripts\alembic upgrade head
```

This works because PowerShell's `localhost` reaches Windows Postgres directly.

**Option B — Configure Windows Postgres to accept WSL2 connections (permanent fix):**

1. Find your PostgreSQL data directory (usually `C:\Program Files\PostgreSQL\<version>\data\`)

2. Edit `postgresql.conf` — change:
   ```
   listen_addresses = 'localhost'
   ```
   to:
   ```
   listen_addresses = '*'
   ```

3. Edit `pg_hba.conf` — add this line:
   ```
   host    all    all    0.0.0.0/0    md5
   ```

4. Restart the Postgres Windows service (Services → `postgresql-x64-<version>` → Restart)

5. Get the Windows host IP from WSL2:
   ```bash
   cat /etc/resolv.conf | grep nameserver | awk '{print $2}'
   ```

6. Update `backend/.env` to use that IP instead of `localhost`:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@<windows-host-ip>:5432/intrepid_poc
   ```

After this, `make migrate`, `make run-backend`, and all other `make` targets work from WSL2.

---

## 10. Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'api'` | uvicorn run from wrong directory | Use `make run-backend` or run `cd backend && uvicorn api.main:app` |
| `connection refused` on DATABASE_URL | Postgres not running or database missing | Start Postgres; verify `intrepid_poc` database exists |
| `connection refused` from WSL2 | WSL2 cannot reach Windows `localhost` | See [WSL2 and PostgreSQL](#wsl2-and-postgresql) |
| `FileNotFoundError: Tape20Loans file not found` | Missing `--pdate` or wrong date with sample data | Use `--pdate 2026-02-19` when running with sample data |
| `STORAGE_TYPE=s3` errors without S3 credentials | `backend/.env` still has `STORAGE_TYPE=s3` | Set `STORAGE_TYPE=local` in `backend/.env` |
| `missing separator` in Makefile | Editor replaced tabs with spaces | Ensure Makefile recipe lines use tab (not space) indentation |
| `SSL certificate verify failed` on `pip install` | Corporate proxy intercepts HTTPS | Run `pip config set global.trusted-host "pypi.org files.pythonhosted.org"` then retry |
