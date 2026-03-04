"""Cashflow file manager and execution endpoints."""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from psycopg.types.json import Json

from auth.security import get_current_user
from cashflow.aws import AWS_REGION
from cashflow.db import db_conn
from cashflow.compute.run_cashflows import run_pipeline
from cashflow.compute.run_purchase_package import run_purchase_package
from cashflow.models import (
    CashflowDefaultsResponse,
    CashflowFileEntry,
    CashflowFolder,
    CashflowJobDefaults,
    CashflowJobRequest,
    CashflowJobResponse,
)

router = APIRouter(
    prefix="/api/cashflow",
    tags=["cashflow"],
    dependencies=[Depends(get_current_user)],
)

_CASHFLOW_BUCKET = os.getenv("CASHFLOW_S3_BUCKET", "intrepid-poc-qa")
_CASHFLOW_PREFIX = os.getenv("CASHFLOW_S3_PREFIX", "").strip("/")
_INSTANCE_ID = os.getenv("ECS_CONTAINER_METADATA_URI_V4") or socket.gethostname() or f"pid-{os.getpid()}"
_CASHFLOW_EXECUTION_MODE = os.getenv("CASHFLOW_EXECUTION_MODE", "local").strip().lower()
_CASHFLOW_ECS_CLUSTER = os.getenv("CASHFLOW_ECS_CLUSTER", "").strip()
_CASHFLOW_ECS_TASK_DEFINITION = os.getenv("CASHFLOW_ECS_TASK_DEFINITION", "").strip()
_CASHFLOW_ECS_CONTAINER_NAME = os.getenv("CASHFLOW_ECS_CONTAINER_NAME", "cashflow-worker").strip() or "cashflow-worker"
_CASHFLOW_ECS_SUBNETS = [part.strip() for part in os.getenv("CASHFLOW_ECS_SUBNETS", "").split(",") if part.strip()]
_CASHFLOW_ECS_SECURITY_GROUPS = [part.strip() for part in os.getenv("CASHFLOW_ECS_SECURITY_GROUPS", "").split(",") if part.strip()]
_CASHFLOW_ECS_ASSIGN_PUBLIC_IP = os.getenv("CASHFLOW_ECS_ASSIGN_PUBLIC_IP", "false").strip().lower() in {"1", "true", "yes", "enabled"}
_LOCAL_JOB_PROCS: dict[str, subprocess.Popen[str]] = {}
_LOCAL_JOB_LOCK = threading.Lock()
_MONITOR_STARTED = False
_ORPHAN_JOB_AGE_SECONDS = 60 * 60
_DEFAULT_ECS_CURRENT_ASSETS_WORKERS = max(1, int(os.getenv("CASHFLOW_MAX_WORKERS", "4")))

_MODE_DEFAULTS = {
    "current_assets": CashflowJobDefaults(
        mode="current_assets",
        buy_num="93rd",
        purchase_date="2026-02-24",
        target=7.9,
        cprshock=1.0,
        cdrshock=1.0,
        workers=_DEFAULT_ECS_CURRENT_ASSETS_WORKERS if _CASHFLOW_EXECUTION_MODE == "ecs_task" else 1,
        current_assets_file="current_assets.csv",
        current_assets_output="",
    ),
    "sg": CashflowJobDefaults(
        mode="sg",
        buy_num="93rd",
        purchase_date="2026-02-24",
        target=7.9,
        cprshock=1.0,
        cdrshock=1.0,
        workers=1,
        prime_file="02-19-2026 Exhibit A To Form Of Sale Notice_sg.xlsx",
        sfy_file="FX3_02-19-2026_ExhibitAtoFormofSaleNotice_sg.xlsx",
        master_sheet="MASTER_SHEET.xlsx",
        notes_sheet="MASTER_SHEET - Notes.xlsx",
    ),
    "cibc": CashflowJobDefaults(
        mode="cibc",
        buy_num="93rd",
        purchase_date="2026-02-24",
        target=7.9,
        cprshock=1.0,
        cdrshock=1.0,
        workers=1,
        prime_file="02-19-2026 Exhibit A To Form Of Sale Notice_cibc.xlsx",
        sfy_file="FX3_02-19-2026_ExhibitAtoFormofSaleNotice_cibc.xlsx",
        master_sheet="MASTER_SHEET.xlsx",
        notes_sheet="MASTER_SHEET - Notes.xlsx",
    ),
}

_AWS_SAFE_CURRENT_ASSETS_WORKERS = _DEFAULT_ECS_CURRENT_ASSETS_WORKERS if _CASHFLOW_EXECUTION_MODE == "ecs_task" else 1


def _running_in_ecs() -> bool:
    return bool(os.getenv("ECS_CONTAINER_METADATA_URI_V4") or os.getenv("AWS_EXECUTION_ENV"))


def _normalize_job_request(req: CashflowJobRequest) -> CashflowJobRequest:
    request_data = req.model_dump()
    if request_data["mode"] == "current_assets" and _running_in_ecs():
        request_data["workers"] = min(int(request_data.get("workers") or 1), _AWS_SAFE_CURRENT_ASSETS_WORKERS)
    return CashflowJobRequest(**request_data)


def _ensure_cashflow_job_table() -> None:
    with db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cashflow_job (
              job_id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              mode TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL,
              started_at TIMESTAMPTZ NULL,
              completed_at TIMESTAMPTZ NULL,
              request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
              output_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
              progress_percent INTEGER NOT NULL DEFAULT 0,
              progress_message TEXT NULL,
              log_messages_json JSONB NOT NULL DEFAULT '[]'::jsonb,
              error_detail TEXT NULL,
              cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
              owner_instance TEXT NULL,
              worker_pid INTEGER NULL,
              worker_task_arn TEXT NULL,
              last_heartbeat TIMESTAMPTZ NULL
            )
            """
        )
        conn.execute("ALTER TABLE cashflow_job ADD COLUMN IF NOT EXISTS cancel_requested BOOLEAN NOT NULL DEFAULT FALSE")
        conn.execute("ALTER TABLE cashflow_job ADD COLUMN IF NOT EXISTS owner_instance TEXT NULL")
        conn.execute("ALTER TABLE cashflow_job ADD COLUMN IF NOT EXISTS worker_pid INTEGER NULL")
        conn.execute("ALTER TABLE cashflow_job ADD COLUMN IF NOT EXISTS worker_task_arn TEXT NULL")
        conn.execute("ALTER TABLE cashflow_job ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMPTZ NULL")


def _s3_client():
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - dependency wiring issue
        raise HTTPException(status_code=500, detail="boto3 is not installed in this environment.") from exc
    return boto3.client("s3", region_name=AWS_REGION)


def _ecs_client():
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - dependency wiring issue
        raise HTTPException(status_code=500, detail="boto3 is not installed in this environment.") from exc
    return boto3.client("ecs", region_name=AWS_REGION)


def _is_s3_error(exc: Exception) -> bool:
    return exc.__class__.__module__.startswith("botocore")


def _folder_prefix(folder: CashflowFolder) -> str:
    parts = [_CASHFLOW_PREFIX, folder]
    return "/".join(part for part in parts if part)


def _object_key(folder: CashflowFolder, name: str) -> str:
    safe_name = PurePosixPath(name).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid file name.")
    return f"{_folder_prefix(folder)}/{safe_name}"


def _key_to_entry(folder: CashflowFolder, key: str, size: int, last_modified: datetime | None) -> CashflowFileEntry:
    prefix = f"{_folder_prefix(folder)}/"
    name = key[len(prefix):] if key.startswith(prefix) else PurePosixPath(key).name
    return CashflowFileEntry(
        key=key,
        name=name,
        folder=folder,
        size=size,
        last_modified=last_modified,
    )


def _list_folder_files(folder: CashflowFolder) -> list[CashflowFileEntry]:
    prefix = f"{_folder_prefix(folder)}/"
    client = _s3_client()
    paginator = client.get_paginator("list_objects_v2")
    files: list[CashflowFileEntry] = []
    try:
        for page in paginator.paginate(Bucket=_CASHFLOW_BUCKET, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item["Key"]
                if key.endswith("/"):
                    continue
                files.append(
                    _key_to_entry(
                        folder=folder,
                        key=key,
                        size=int(item.get("Size", 0)),
                        last_modified=item.get("LastModified"),
                    )
                )
    except Exception as exc:  # noqa: BLE001
        if not _is_s3_error(exc):
            raise
        raise HTTPException(status_code=502, detail=f"S3 list failed: {exc}") from exc
    files.sort(key=lambda item: (item.last_modified or datetime.min.replace(tzinfo=timezone.utc), item.name), reverse=True)
    return files


def _row_to_job_response(row: dict[str, Any]) -> CashflowJobResponse:
    return CashflowJobResponse(
        job_id=row["job_id"],
        status=row["status"],
        mode=row["mode"],
        created_at=row["created_at"],
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        request=row.get("request_json") or {},
        output_files=[CashflowFileEntry(**item) for item in (row.get("output_files_json") or [])],
        progress_percent=row.get("progress_percent") or 0,
        progress_message=row.get("progress_message"),
        log_messages=row.get("log_messages_json") or [],
        error_detail=row.get("error_detail"),
        cancel_requested=bool(row.get("cancel_requested")),
    )


def _serialize_output_files(entries: list[CashflowFileEntry]) -> list[dict[str, Any]]:
    return [entry.model_dump(mode="json") for entry in entries]


def _reconcile_orphaned_job(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("status") not in {"QUEUED", "RUNNING"}:
        return row
    if _CASHFLOW_EXECUTION_MODE == "worker":
        return row

    now = datetime.now(timezone.utc)
    started_at = row.get("started_at") or row.get("created_at")
    age_seconds = (now - started_at).total_seconds() if started_at else 0
    owner_instance = row.get("owner_instance")
    worker_pid = row.get("worker_pid")
    worker_task_arn = row.get("worker_task_arn")
    cancel_requested = bool(row.get("cancel_requested"))
    last_heartbeat = row.get("last_heartbeat") or started_at
    heartbeat_age_seconds = (now - last_heartbeat).total_seconds() if last_heartbeat else age_seconds

    if worker_task_arn and _is_ecs_task_active(worker_task_arn):
        return row
    if owner_instance == _INSTANCE_ID and _is_pid_alive(worker_pid):
        return row

    is_orphan = False
    if worker_task_arn and not _is_ecs_task_active(worker_task_arn):
        is_orphan = heartbeat_age_seconds >= 30
    elif owner_instance == _INSTANCE_ID and worker_pid and not _is_pid_alive(worker_pid):
        is_orphan = True
    elif cancel_requested and age_seconds >= 10:
        is_orphan = True
    elif (not owner_instance or owner_instance != _INSTANCE_ID) and heartbeat_age_seconds >= _ORPHAN_JOB_AGE_SECONDS:
        is_orphan = True

    if not is_orphan:
        return row

    terminal_status = "CANCELLED" if cancel_requested else "FAILED"
    terminal_message = "Cancelled" if cancel_requested else "Failed"
    detail = None if cancel_requested else "Job became orphaned after worker process exited or service restarted."
    _set_job_state(
        row["job_id"],
        status=terminal_status,
        completed_at=now,
        progress_message=terminal_message,
        error_detail=detail,
    )

    row = dict(row)
    row["status"] = terminal_status
    row["completed_at"] = now
    row["progress_message"] = terminal_message
    row["error_detail"] = detail
    return row


def _job_cancel_requested(job_id: str) -> bool:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT cancel_requested FROM cashflow_job WHERE job_id = %(job_id)s",
            {"job_id": job_id},
        ).fetchone()
    return bool(row and row.get("cancel_requested"))


def _job_worker_task_arn(job_id: str) -> str | None:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT worker_task_arn FROM cashflow_job WHERE job_id = %(job_id)s",
            {"job_id": job_id},
        ).fetchone()
    return row.get("worker_task_arn") if row else None


def _is_pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _load_job_request(job_id: str) -> CashflowJobRequest:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT request_json FROM cashflow_job WHERE job_id = %(job_id)s",
            {"job_id": job_id},
        ).fetchone()
    if not row:
        raise RuntimeError(f"Cashflow job not found: {job_id}")
    return CashflowJobRequest(**(row.get("request_json") or {}))


def _kill_local_process(job_id: str) -> bool:
    with _LOCAL_JOB_LOCK:
        proc = _LOCAL_JOB_PROCS.get(job_id)
    if proc is None or proc.poll() is not None:
        return False
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        return False


def _ecs_task_network_configuration() -> dict[str, Any]:
    if not _CASHFLOW_ECS_SUBNETS or not _CASHFLOW_ECS_SECURITY_GROUPS:
        raise RuntimeError("Cashflow ECS network configuration is incomplete.")
    return {
        "awsvpcConfiguration": {
            "subnets": _CASHFLOW_ECS_SUBNETS,
            "securityGroups": _CASHFLOW_ECS_SECURITY_GROUPS,
            "assignPublicIp": "ENABLED" if _CASHFLOW_ECS_ASSIGN_PUBLIC_IP else "DISABLED",
        }
    }


def _is_ecs_task_active(task_arn: str | None) -> bool:
    if not task_arn or not _CASHFLOW_ECS_CLUSTER:
        return False
    try:
        response = _ecs_client().describe_tasks(cluster=_CASHFLOW_ECS_CLUSTER, tasks=[task_arn])
    except Exception:  # noqa: BLE001
        return False
    tasks = response.get("tasks") or []
    if not tasks:
        return False
    last_status = (tasks[0].get("lastStatus") or "").upper()
    return last_status not in {"STOPPED", "DEPROVISIONING"}


def _stop_ecs_task(task_arn: str | None, reason: str) -> bool:
    if not task_arn or not _CASHFLOW_ECS_CLUSTER:
        return False
    try:
        _ecs_client().stop_task(cluster=_CASHFLOW_ECS_CLUSTER, task=task_arn, reason=reason)
        return True
    except Exception:  # noqa: BLE001
        return False


def _start_cashflow_job_monitor() -> None:
    global _MONITOR_STARTED
    if _MONITOR_STARTED:
        return

    def _monitor_loop() -> None:
        while True:
            with _LOCAL_JOB_LOCK:
                tracked = list(_LOCAL_JOB_PROCS.items())
            for job_id, proc in tracked:
                if _job_cancel_requested(job_id) and proc.poll() is None:
                    _kill_local_process(job_id)

                exit_code = proc.poll()
                if exit_code is None:
                    continue

                with _LOCAL_JOB_LOCK:
                    _LOCAL_JOB_PROCS.pop(job_id, None)

                job = _job_snapshot(job_id)
                if job.status in {"COMPLETED", "FAILED", "CANCELLED"}:
                    continue
                if job.cancel_requested:
                    _set_job_state(
                        job_id,
                        status="CANCELLED",
                        completed_at=datetime.now(timezone.utc),
                        progress_message="Cancelled",
                        error_detail=None,
                    )
                    _append_job_log(job_id, "Job cancelled", 100)
                elif exit_code != 0:
                    _set_job_state(
                        job_id,
                        status="FAILED",
                        completed_at=datetime.now(timezone.utc),
                        progress_message="Failed",
                        error_detail=f"Worker exited with code {exit_code}",
                    )
                    _append_job_log(job_id, f"Worker exited with code {exit_code}")
            time.sleep(2)

    thread = threading.Thread(target=_monitor_loop, name="cashflow-job-monitor", daemon=True)
    thread.start()
    _MONITOR_STARTED = True


def _launch_cashflow_worker(job_id: str) -> int:
    if _CASHFLOW_EXECUTION_MODE == "ecs_task" and _running_in_ecs():
        if not _CASHFLOW_ECS_CLUSTER or not _CASHFLOW_ECS_TASK_DEFINITION:
            raise RuntimeError("Cashflow ECS execution is enabled but task settings are missing.")
        response = _ecs_client().run_task(
            cluster=_CASHFLOW_ECS_CLUSTER,
            taskDefinition=_CASHFLOW_ECS_TASK_DEFINITION,
            launchType="FARGATE",
            networkConfiguration=_ecs_task_network_configuration(),
            overrides={
                "containerOverrides": [
                    {
                        "name": _CASHFLOW_ECS_CONTAINER_NAME,
                        "command": [
                            "python",
                            "-m",
                            "cashflow.worker",
                            job_id,
                        ],
                    }
                ]
            },
        )
        failures = response.get("failures") or []
        if failures:
            reason = failures[0].get("reason") or failures[0].get("detail") or "unknown failure"
            raise RuntimeError(f"ECS run_task failed: {reason}")
        tasks = response.get("tasks") or []
        if not tasks:
            raise RuntimeError("ECS run_task returned no tasks.")
        task_arn = tasks[0]["taskArn"]
        _set_job_state(job_id, owner_instance=_INSTANCE_ID, worker_pid=None, worker_task_arn=task_arn)
        return 0

    _start_cashflow_job_monitor()
    proc = subprocess.Popen(
        [sys.executable, "-m", "cashflow.worker", job_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    with _LOCAL_JOB_LOCK:
        _LOCAL_JOB_PROCS[job_id] = proc
    _set_job_state(job_id, owner_instance=_INSTANCE_ID, worker_pid=proc.pid, worker_task_arn=None)
    return proc.pid


def _expected_output_names(req: CashflowJobRequest) -> list[str]:
    if req.mode == "current_assets":
        output_name = req.current_assets_output.strip()
        return [PurePosixPath(output_name).name] if output_name else []

    buyer = req.mode
    raw_suffix = f"{req.buy_num}_{buyer}"
    return [
        f"SFC_cashflows_{raw_suffix}.csv",
        f"TWG_cashflows_{raw_suffix}.csv",
        f"loans_data_{raw_suffix}.csv",
        f"cashflows_{req.buy_num}_{req.target}_{buyer}.xlsx",
    ]


def _try_head_output_file(client, name: str) -> CashflowFileEntry | None:
    key = _object_key("outputs", name)
    try:
        head = client.head_object(Bucket=_CASHFLOW_BUCKET, Key=key)
    except Exception as exc:  # noqa: BLE001
        if not _is_s3_error(exc):
            raise
        response = getattr(exc, "response", {}) or {}
        error = response.get("Error", {}) or {}
        if str(error.get("Code", "")).lower() in {"404", "nosuchkey", "notfound"}:
            return None
        raise
    return _key_to_entry(
        folder="outputs",
        key=key,
        size=int(head.get("ContentLength", 0)),
        last_modified=head.get("LastModified"),
    )


def _reconcile_job_outputs(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("status") == "COMPLETED" and row.get("output_files_json"):
        return row

    request_json = row.get("request_json") or {}
    try:
        req = CashflowJobRequest(**request_json)
    except Exception:  # noqa: BLE001
        return row

    expected_names = _expected_output_names(req)
    if not expected_names:
        return row

    client = _s3_client()
    found_entries: list[CashflowFileEntry] = []
    for name in expected_names:
        entry = _try_head_output_file(client, name)
        if entry is None:
            return row
        found_entries.append(entry)

    completed_at = row.get("completed_at")
    if completed_at is None:
        completed_at = max(
            (entry.last_modified for entry in found_entries if entry.last_modified is not None),
            default=datetime.now(timezone.utc),
        )

    serialized_outputs = _serialize_output_files(found_entries)
    _set_job_state(
        row["job_id"],
        status="COMPLETED",
        completed_at=completed_at,
        output_files=serialized_outputs,
        progress_percent=100,
        progress_message="Completed",
        error_detail=None,
    )

    row = dict(row)
    row["status"] = "COMPLETED"
    row["completed_at"] = completed_at
    row["output_files_json"] = serialized_outputs
    row["progress_percent"] = 100
    row["progress_message"] = "Completed"
    row["error_detail"] = None
    return row


def _job_snapshot(job_id: str) -> CashflowJobResponse:
    _ensure_cashflow_job_table()
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM cashflow_job WHERE job_id = %(job_id)s",
            {"job_id": job_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Cashflow job not found: {job_id}")
    row = _reconcile_orphaned_job(row)
    row = _reconcile_job_outputs(row)
    return _row_to_job_response(row)


def _set_job_state(job_id: str, **updates: Any) -> None:
    if not updates:
        return
    _ensure_cashflow_job_table()

    assignments: list[str] = []
    params: dict[str, Any] = {"job_id": job_id}
    json_fields = {"request": "request_json", "output_files": "output_files_json", "log_messages": "log_messages_json"}

    for field, value in updates.items():
        column = json_fields.get(field, field)
        assignments.append(f"{column} = %({column})s")
        params[column] = Json(value) if field in json_fields else value

    with db_conn() as conn:
        conn.execute(
            f"UPDATE cashflow_job SET {', '.join(assignments)} WHERE job_id = %(job_id)s",
            params,
        )


def _append_job_log(job_id: str, message: str, progress_percent: int | None = None) -> None:
    job = _job_snapshot(job_id)
    logs = list(job.log_messages)
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    logs.append(f"{timestamp} {message}")
    updates: dict[str, Any] = {
        "log_messages": logs[-50:],
        "progress_message": message,
        "last_heartbeat": datetime.now(timezone.utc),
    }
    if progress_percent is not None:
        updates["progress_percent"] = max(0, min(100, int(progress_percent)))
    _set_job_state(job_id, **updates)


def _download_to_path(client, folder: CashflowFolder, file_name: str, destination: Path) -> Path:
    key = _object_key(folder, file_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        client.download_file(_CASHFLOW_BUCKET, key, str(destination))
    except Exception as exc:  # noqa: BLE001
        if not _is_s3_error(exc):
            raise
        raise RuntimeError(f"Unable to download {file_name} from {folder}: {exc}") from exc
    return destination


def _upload_output_file(client, local_path: Path) -> CashflowFileEntry:
    key = _object_key("outputs", local_path.name)
    try:
        client.upload_file(str(local_path), _CASHFLOW_BUCKET, key)
        head = client.head_object(Bucket=_CASHFLOW_BUCKET, Key=key)
    except Exception as exc:  # noqa: BLE001
        if not _is_s3_error(exc):
            raise
        raise RuntimeError(f"Unable to upload {local_path.name}: {exc}") from exc
    return _key_to_entry(
        folder="outputs",
        key=key,
        size=int(head.get("ContentLength", local_path.stat().st_size)),
        last_modified=head.get("LastModified"),
    )


def _run_cashflow_job(job_id: str, req: CashflowJobRequest) -> None:
    if _job_cancel_requested(job_id):
        _set_job_state(
            job_id,
            status="CANCELLED",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            progress_percent=100,
            progress_message="Cancelled",
            error_detail=None,
            last_heartbeat=datetime.now(timezone.utc),
        )
        _append_job_log(job_id, "Job cancelled before start", 100)
        return

    _set_job_state(
        job_id,
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
        last_heartbeat=datetime.now(timezone.utc),
    )
    _append_job_log(job_id, f"Job started for {req.mode}", 1)
    client = _s3_client()

    try:
        with tempfile.TemporaryDirectory(prefix=f"cashflow-{job_id}-") as tmp_dir:
            work_root = Path(tmp_dir)
            input_dir = work_root / "inputs"
            output_dir = work_root / "outputs"
            input_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            if req.mode == "current_assets":
                _append_job_log(job_id, f"Downloading {req.current_assets_file} from inputs", 3)
                input_path = _download_to_path(client, "inputs", req.current_assets_file, input_dir / req.current_assets_file)
                output_name = req.current_assets_output.strip() or f"cashflows_{datetime.now(timezone.utc):%Y%m%d}.xlsx"
                output_path = output_dir / PurePosixPath(output_name).name
                run_pipeline(
                    input_path=str(input_path),
                    output_path=str(output_path),
                    cprshock=req.cprshock,
                    cdrshock=req.cdrshock,
                    irr_target=req.target,
                    workers=req.workers,
                    progress_callback=lambda pct, msg: _append_job_log(job_id, msg, pct),
                    should_cancel=lambda: _job_cancel_requested(job_id),
                )
                produced_paths = [output_path]
            else:
                prime_name = req.prime_file or _MODE_DEFAULTS[req.mode].prime_file
                sfy_name = req.sfy_file or _MODE_DEFAULTS[req.mode].sfy_file
                if not prime_name or not sfy_name:
                    raise RuntimeError(f"Missing source workbook configuration for {req.mode}.")
                _append_job_log(job_id, f"Downloading {req.mode.upper()} source workbooks", 3)
                outputs = run_purchase_package(
                    prime_file=str(_download_to_path(client, "inputs", prime_name, input_dir / prime_name)),
                    sfy_file=str(_download_to_path(client, "inputs", sfy_name, input_dir / sfy_name)),
                    master_sheet=str(_download_to_path(client, "inputs", req.master_sheet, input_dir / req.master_sheet)),
                    notes_sheet=str(_download_to_path(client, "inputs", req.notes_sheet, input_dir / req.notes_sheet)),
                    purchase_date=req.purchase_date,
                    output_dir=str(output_dir),
                    buy_num=req.buy_num,
                    buyer=req.mode,
                    irr_target=req.target,
                    cprshock=req.cprshock,
                    cdrshock=req.cdrshock,
                    progress_callback=lambda pct, msg: _append_job_log(job_id, msg, pct),
                    should_cancel=lambda: _job_cancel_requested(job_id),
                )
                produced_paths = [Path(path_str) for path_str in outputs.values()]

            _append_job_log(job_id, "Uploading generated output files", 98)
            uploaded_files = [_upload_output_file(client, path) for path in produced_paths]

        _set_job_state(
            job_id,
            status="COMPLETED",
            completed_at=datetime.now(timezone.utc),
            output_files=_serialize_output_files(uploaded_files),
            progress_percent=100,
            progress_message="Completed",
            last_heartbeat=datetime.now(timezone.utc),
        )
        _append_job_log(job_id, f"Uploaded {len(uploaded_files)} output files", 100)
    except InterruptedError:
        _set_job_state(
            job_id,
            status="CANCELLED",
            completed_at=datetime.now(timezone.utc),
            progress_percent=100,
            progress_message="Cancelled",
            error_detail=None,
            last_heartbeat=datetime.now(timezone.utc),
        )
        _append_job_log(job_id, "Job cancelled", 100)
    except Exception as exc:  # noqa: BLE001
        _set_job_state(
            job_id,
            status="FAILED",
            completed_at=datetime.now(timezone.utc),
            progress_message="Failed",
            error_detail=str(exc),
            last_heartbeat=datetime.now(timezone.utc),
        )
        _append_job_log(job_id, f"Job failed: {exc}")


def run_cashflow_worker_main(job_id: str) -> None:
    _ensure_cashflow_job_table()
    req = _load_job_request(job_id)
    _run_cashflow_job(job_id, req)


@router.get("/defaults", response_model=CashflowDefaultsResponse)
def get_cashflow_defaults():
    """Return default UI values for each cashflow mode."""
    return CashflowDefaultsResponse(
        bucket=_CASHFLOW_BUCKET,
        defaults=_MODE_DEFAULTS,
    )


@router.get("/files/{folder}", response_model=list[CashflowFileEntry])
def list_cashflow_files(folder: CashflowFolder):
    """List cashflow input or output files from S3."""
    return _list_folder_files(folder)


@router.post("/files/{folder}", response_model=CashflowFileEntry, status_code=201)
async def upload_cashflow_file(folder: CashflowFolder, file: UploadFile = File(...)):
    """Upload a file into the managed inputs folder."""
    if folder != "inputs":
        raise HTTPException(status_code=400, detail="Only the inputs folder accepts uploads.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file name is required.")
    key = _object_key(folder, file.filename)
    client = _s3_client()
    try:
        body = await file.read()
        client.put_object(Bucket=_CASHFLOW_BUCKET, Key=key, Body=body)
        head = client.head_object(Bucket=_CASHFLOW_BUCKET, Key=key)
    except Exception as exc:  # noqa: BLE001
        if not _is_s3_error(exc):
            raise
        raise HTTPException(status_code=502, detail=f"S3 upload failed: {exc}") from exc
    return _key_to_entry(
        folder=folder,
        key=key,
        size=int(head.get("ContentLength", len(body))),
        last_modified=head.get("LastModified"),
    )


@router.get("/files/{folder}/download")
def download_cashflow_file(folder: CashflowFolder, key: str = Query(..., min_length=1)):
    """Stream a cashflow file from S3 back to the browser."""
    client = _s3_client()
    try:
        obj = client.get_object(Bucket=_CASHFLOW_BUCKET, Key=key)
    except Exception as exc:  # noqa: BLE001
        if not _is_s3_error(exc):
            raise
        raise HTTPException(status_code=404, detail=f"Unable to fetch {key}: {exc}") from exc
    file_name = PurePosixPath(key).name
    headers = {"Content-Disposition": f'attachment; filename="{file_name}"'}
    return StreamingResponse(
        obj["Body"].iter_chunks(chunk_size=1024 * 1024),
        media_type=obj.get("ContentType", "application/octet-stream"),
        headers=headers,
    )


@router.post("/jobs", response_model=CashflowJobResponse, status_code=202)
def create_cashflow_job(req: CashflowJobRequest):
    """Queue a cashflow generation job."""
    _ensure_cashflow_job_table()
    req = _normalize_job_request(req)
    job_id = f"cashflow-{uuid4()}"
    job = {
        "job_id": job_id,
        "status": "QUEUED",
        "mode": req.mode,
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
        "request": req.model_dump(),
        "output_files": [],
        "progress_percent": 0,
        "progress_message": "Queued",
        "log_messages": ["Queued for execution"],
        "error_detail": None,
        "cancel_requested": False,
        "last_heartbeat": datetime.now(timezone.utc),
    }
    with db_conn() as conn:
        stale_rows = conn.execute(
            """
            SELECT *
            FROM cashflow_job
            WHERE mode = %(mode)s
              AND status IN ('QUEUED', 'RUNNING')
            """,
            {"mode": req.mode},
        ).fetchall()
        for stale_row in stale_rows:
            _reconcile_orphaned_job(stale_row)
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%(mode)s))", {"mode": req.mode})
        existing = conn.execute(
            """
            SELECT job_id
            FROM cashflow_job
            WHERE mode = %(mode)s
              AND status IN ('QUEUED', 'RUNNING')
            LIMIT 1
            """,
            {"mode": req.mode},
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"A {req.mode} cashflow job is already running: {existing['job_id']}",
            )
        conn.execute(
            """
            INSERT INTO cashflow_job (
              job_id, status, mode, created_at, started_at, completed_at,
              request_json, output_files_json, progress_percent, progress_message,
              log_messages_json, error_detail, cancel_requested, owner_instance, worker_pid, worker_task_arn, last_heartbeat
            )
            VALUES (
              %(job_id)s, %(status)s, %(mode)s, %(created_at)s, %(started_at)s, %(completed_at)s,
              %(request_json)s::jsonb, %(output_files_json)s::jsonb, %(progress_percent)s, %(progress_message)s,
              %(log_messages_json)s::jsonb, %(error_detail)s, %(cancel_requested)s, %(owner_instance)s, %(worker_pid)s, %(worker_task_arn)s, %(last_heartbeat)s
            )
            """,
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "mode": job["mode"],
                "created_at": job["created_at"],
                "started_at": job["started_at"],
                "completed_at": job["completed_at"],
                "request_json": Json(job["request"]),
                "output_files_json": Json(job["output_files"]),
                "progress_percent": job["progress_percent"],
                "progress_message": job["progress_message"],
                "log_messages_json": Json(job["log_messages"]),
                "error_detail": job["error_detail"],
                "cancel_requested": False,
                "owner_instance": None,
                "worker_pid": None,
                "worker_task_arn": None,
                "last_heartbeat": job["last_heartbeat"],
            },
        )
    try:
        _launch_cashflow_worker(job_id)
    except Exception as exc:  # noqa: BLE001
        _set_job_state(
            job_id,
            status="FAILED",
            completed_at=datetime.now(timezone.utc),
            progress_message="Failed",
            error_detail=f"Unable to start worker: {exc}",
        )
        raise HTTPException(status_code=500, detail=f"Unable to start cashflow worker: {exc}") from exc
    return CashflowJobResponse(**job)


@router.get("/jobs", response_model=list[CashflowJobResponse])
def list_cashflow_jobs(limit: int = Query(default=20, ge=1, le=100)):
    """List recent cashflow jobs."""
    _ensure_cashflow_job_table()
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM cashflow_job
            ORDER BY created_at DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
    return [_row_to_job_response(_reconcile_job_outputs(_reconcile_orphaned_job(row))) for row in rows]


@router.get("/jobs/{job_id}", response_model=CashflowJobResponse)
def get_cashflow_job(job_id: str):
    """Fetch status for a single cashflow job."""
    return _job_snapshot(job_id)


@router.post("/jobs/{job_id}/cancel", response_model=CashflowJobResponse)
def cancel_cashflow_job(job_id: str):
    """Request cancellation for a running or queued cashflow job."""
    job = _job_snapshot(job_id)
    if job.status in {"COMPLETED", "FAILED", "CANCELLED"}:
        return job

    _set_job_state(
        job_id,
        cancel_requested=True,
        progress_message="Cancellation requested",
    )
    _append_job_log(job_id, "Cancellation requested")
    if not _kill_local_process(job_id):
        _stop_ecs_task(_job_worker_task_arn(job_id), f"Cancellation requested for {job_id}")
    return _job_snapshot(job_id)
