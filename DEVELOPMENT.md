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

> Note: On Windows, `venv/bin/` in the Makefile corresponds to `venv\Scripts\` on Windows paths. The Makefile targets use the Unix path — if you run `make` on Windows via Git Bash or WSL, they work as-is.

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

## 9. Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'api'` | uvicorn run from wrong directory | Use `make run-backend` or run `cd backend && uvicorn api.main:app` |
| `connection refused` on DATABASE_URL | Postgres not running or database missing | Start Postgres; verify `intrepid_poc` database exists |
| `FileNotFoundError: Tape20Loans file not found` | Missing `--pdate` or wrong date with sample data | Use `--pdate 2026-02-19` when running with sample data |
| `STORAGE_TYPE=s3` errors without S3 credentials | `backend/.env` still has `STORAGE_TYPE=s3` | Set `STORAGE_TYPE=local` in `backend/.env` |
| `missing separator` in Makefile | Editor replaced tabs with spaces | Ensure Makefile recipe lines use tab (not space) indentation |
