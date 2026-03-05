# Local Development Guide

This guide covers the complete flow from a fresh clone to a running local stack.

**Primary workflow: PowerShell on Windows.** WSL2 notes are in [Appendix A](#appendix-a-wsl2).

---

## 1. Prerequisites

Ensure the following are installed before starting:

- **Python 3.11+** — verify: `python --version`
- **Node.js 18+ and npm** — verify: `node --version`
- **PostgreSQL (running locally)** — verify: `psql -U postgres -c "\l"`
- **Git**

Create the local database before running migrations:

```powershell
psql -U postgres -c "CREATE DATABASE intrepid_poc;"
```

---

## 2. Initial Setup

```powershell
git clone <repo-url>
cd intrepid-poc
.\dev.ps1 setup
```

`.\dev.ps1 setup` does three things:

1. Creates `backend\venv` (Python virtual environment at `backend\venv\Scripts\`)
2. Installs Python dependencies from `backend\requirements.txt` into the venv
3. Runs `npm install` in `frontend\`

> The `--trusted-host` flags are included automatically for corporate networks that intercept HTTPS.

---

## 3. Environment Configuration

Copy the example env file and edit it:

```powershell
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` to match your local setup:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/intrepid_poc` | Update password if your Postgres install uses a different one |
| `SECRET_KEY` | `change-me-local` | Change to any random string for local dev |
| `STORAGE_TYPE` | `local` | Leave as `local` for sample data |
| `DEV_INPUT` | `./data/sample/files_required` | Leave as-is to use sample data |

`backend\.env` is gitignored — never commit it. Only `backend\.env.example` is tracked.

---

## 4. Run Database Migrations

```powershell
.\dev.ps1 migrate
```

Expected output: `Running upgrade -> 60a8a67090c8` (or `already at head` if already applied).

**If you have an existing `intrepid_poc` database from before Alembic was introduced**, drop and recreate it first:

```powershell
psql -U postgres -c "DROP DATABASE IF EXISTS intrepid_poc; CREATE DATABASE intrepid_poc;"
.\dev.ps1 migrate
```

---

## 5. Start the Backend

```powershell
.\dev.ps1 run-backend
```

The backend starts at `http://localhost:8000`. Verify it is running in a second terminal:

```powershell
curl http://localhost:8000/api/health
```

Expected: HTTP 200 response with no startup errors.

> Always start the backend before the frontend. The Vite dev server proxies `/api` requests to `:8000`.

---

## 6. Start the Frontend

In a separate terminal:

```powershell
.\dev.ps1 run-frontend
```

The frontend starts at `http://localhost:5173` with hot reload enabled.

Open `http://localhost:5173` in your browser. API calls are proxied to `http://localhost:8000`.

---

## 7. Running the Pipeline Locally

The repository includes a sample dataset at `backend\data\sample\files_required\`. The pipeline uses date-stamped filenames to locate input files.

**Important:** The sample files are dated `02-18-2026`, which means the pipeline processing date must be `2026-02-19` (the day after the file date).

**Via the UI:**

1. Open `http://localhost:5173`
2. Use the pipeline run form and enter processing date `2026-02-19`

**Via CLI directly** (with backend running, in a separate terminal):

```powershell
cd backend
.\venv\Scripts\python main.py --pdate 2026-02-19
```

Expected: pipeline completes without `FileNotFoundError`. Output files appear in `backend\data\outputs\`.

**To use your own live input files** instead of sample data, set `DEV_INPUT` in `backend\.env`:

```
DEV_INPUT=C:\path\to\your\files_required
```

---

## 8. Development Notes

- **All backend commands run from `backend\`.** pydantic-settings resolves `.env` relative to the working directory. `dev.ps1` handles the directory switch automatically.
- **Alembic enum changes** (`UserRole`, `RunStatus`) are not auto-detected — write manual migration steps if you modify these enums.
- **`backend\.env` is gitignored** — never commit it. Only `backend\.env.example` is tracked.
- **Frontend proxy:** Vite proxies all `/api` requests to `http://localhost:8000`. No manual proxy setup needed.

---

## 9. Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'api'` | uvicorn run from wrong directory | Use `.\dev.ps1 run-backend` (handles `cd backend` automatically) |
| `connection refused` on `DATABASE_URL` | Postgres not running or wrong password | Start Postgres service; check password in `backend\.env` |
| `FileNotFoundError: Tape20Loans file not found` | Wrong `--pdate` with sample data | Use `--pdate 2026-02-19` when running with sample data |
| `STORAGE_TYPE=s3` errors without S3 credentials | `.env` has `STORAGE_TYPE=s3` | Set `STORAGE_TYPE=local` in `backend\.env` |
| `venv\Scripts\alembic` not found | venv created in WSL2, not PowerShell | Delete `backend\venv` and run `.\dev.ps1 setup` from PowerShell |

---

## Appendix A: WSL2

WSL2 is not the primary workflow for this project. If you need to use WSL2:

- Run `make setup` from WSL2 — this creates `backend/venv/bin/` (Linux-style)
- The `Makefile` auto-detects WSL2 and uses `venv/bin/` accordingly
- **WSL2 cannot reach Windows Postgres via `localhost`.** You must either:
  - Configure Postgres to listen on all interfaces (`listen_addresses = '*'` in `postgresql.conf`) and update `DATABASE_URL` with the Windows host IP (`cat /etc/resolv.conf | grep nameserver | awk '{print $2}'`)
  - Or run all database commands from PowerShell instead

The `dev.ps1` script and PowerShell workflow have no WSL2 dependencies.
