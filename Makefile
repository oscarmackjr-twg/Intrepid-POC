.PHONY: setup run-backend run-frontend migrate

# Detect venv binary path: Scripts on native Windows, bin on Unix/WSL/macOS
ifeq ($(OS),Windows_NT)
    VENV_BIN := venv/Scripts
else
    VENV_BIN := venv/bin
endif

# Install backend Python dependencies into venv and frontend npm packages.
# Run once after cloning, or when requirements.txt / package.json change.
setup:
	cd backend && python -m venv venv
	cd backend && $(VENV_BIN)/pip install -r requirements.txt
	cd frontend && npm install

# Start the FastAPI backend with auto-reload at http://localhost:8000
# Requires backend/.env to exist (copy from backend/.env.example and fill in DATABASE_URL).
run-backend:
	cd backend && $(VENV_BIN)/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start the Vite frontend dev server with hot reload at http://localhost:5173
# The Vite proxy forwards /api requests to localhost:8000 — run-backend must be running.
run-frontend:
	cd frontend && npm run dev

# Apply Alembic database migrations to local Postgres.
# Requires DATABASE_URL in backend/.env and the intrepid_poc database to exist.
# If you have a pre-Alembic database, drop and recreate it first:
#   psql -U postgres -c "DROP DATABASE IF EXISTS intrepid_poc; CREATE DATABASE intrepid_poc;"
migrate:
	cd backend && $(VENV_BIN)/alembic upgrade head
