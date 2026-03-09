"""Async job tracking for Final Funding SG and CIBC program runs."""
import os
import socket
import threading
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.security import get_current_user
from cashflow.db import db_conn
from orchestration.final_funding_runner import execute_final_funding_sg, execute_final_funding_cibc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/program-run", tags=["program-run-jobs"])

_INSTANCE_ID = os.getenv("ECS_CONTAINER_METADATA_URI_V4") or socket.gethostname() or f"pid-{os.getpid()}"


def _ensure_final_funding_job_table() -> None:
    with db_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS final_funding_job (
              job_id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              mode TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL,
              started_at TIMESTAMPTZ NULL,
              completed_at TIMESTAMPTZ NULL,
              output_prefix TEXT NULL,
              progress_message TEXT NULL,
              log_messages_json JSONB NOT NULL DEFAULT '[]'::jsonb,
              error_detail TEXT NULL,
              owner_instance TEXT NULL,
              worker_pid INTEGER NULL,
              last_heartbeat TIMESTAMPTZ NULL
            )
        """)


try:
    _ensure_final_funding_job_table()
except Exception as _e:
    logger.warning("Could not ensure final_funding_job table at import: %s", _e)


def _set_ff_job_state(job_id: str, **kwargs) -> None:
    set_clauses = ", ".join(f"{k} = %({k})s" for k in kwargs)
    with db_conn() as conn:
        conn.execute(
            f"UPDATE final_funding_job SET {set_clauses} WHERE job_id = %(job_id)s",
            {"job_id": job_id, **kwargs},
        )


def _check_concurrent_ff_job(mode: str, conn) -> None:
    """Raise HTTPException 409 if a QUEUED or RUNNING job already exists for this mode.

    Accepts an open DB connection so callers can reuse the same transaction.
    """
    existing = conn.execute(
        "SELECT job_id FROM final_funding_job WHERE mode = %(mode)s AND status IN ('QUEUED', 'RUNNING')",
        {"mode": mode},
    ).fetchone()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A {mode.upper()} Final Funding job is already QUEUED or RUNNING ({existing['job_id']}). Wait for it to finish.",
        )


def _create_ff_job(mode: str, folder: Optional[str] = None) -> dict:
    """Insert a new QUEUED job row. Raises 409 if a QUEUED/RUNNING job for this mode already exists."""
    with db_conn() as conn:
        _check_concurrent_ff_job(mode, conn)
        job_id = f"ff-{mode}-{uuid4()}"
        now = datetime.now(timezone.utc)
        conn.execute(
            """INSERT INTO final_funding_job
               (job_id, status, mode, created_at, log_messages_json)
               VALUES (%(job_id)s, 'QUEUED', %(mode)s, %(created_at)s, '[]'::jsonb)""",
            {"job_id": job_id, "mode": mode, "created_at": now},
        )
        row = conn.execute(
            "SELECT * FROM final_funding_job WHERE job_id = %(job_id)s",
            {"job_id": job_id},
        ).fetchone()
    return dict(row)


def _run_ff_job_background(job_id: str, mode: str, folder: Optional[str]) -> None:
    """Run final funding script in background, updating job table with lifecycle status."""
    try:
        _set_ff_job_state(
            job_id,
            status="RUNNING",
            started_at=datetime.now(timezone.utc),
            owner_instance=_INSTANCE_ID,
            worker_pid=os.getpid(),
        )
        if mode == "sg":
            output_prefix = execute_final_funding_sg(folder=folder)
        elif mode == "cibc":
            output_prefix = execute_final_funding_cibc(folder=folder)
        else:
            raise ValueError(f"Unknown mode: {mode}")
        _set_ff_job_state(
            job_id,
            status="COMPLETED",
            completed_at=datetime.now(timezone.utc),
            output_prefix=output_prefix,
            progress_message="Completed successfully.",
        )
    except HTTPException:
        # Don't swallow HTTP exceptions (e.g. 409 from concurrent guard)
        raise
    except Exception as e:
        logger.exception("Final funding job %s failed: %s", job_id, e)
        try:
            _set_ff_job_state(
                job_id,
                status="FAILED",
                completed_at=datetime.now(timezone.utc),
                error_detail=str(e),
            )
        except Exception as e2:
            logger.error("Failed to update job %s to FAILED: %s", job_id, e2)


class FinalFundingJobCreate(BaseModel):
    mode: str  # "sg" | "cibc"
    folder: Optional[str] = None


@router.post("/jobs", status_code=202)
async def create_final_funding_job(
    body: FinalFundingJobCreate,
    current_user=Depends(get_current_user),
):
    if body.mode not in ("sg", "cibc"):
        raise HTTPException(status_code=400, detail="mode must be 'sg' or 'cibc'")
    job = _create_ff_job(body.mode, folder=body.folder)
    thread = threading.Thread(
        target=_run_ff_job_background,
        args=(job["job_id"], body.mode, body.folder),
        daemon=True,
    )
    thread.start()
    return job


@router.get("/jobs")
async def list_final_funding_jobs(current_user=Depends(get_current_user)):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM final_funding_job ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/jobs/{job_id}")
async def get_final_funding_job(job_id: str, current_user=Depends(get_current_user)):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM final_funding_job WHERE job_id = %(job_id)s",
            {"job_id": job_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return dict(row)
