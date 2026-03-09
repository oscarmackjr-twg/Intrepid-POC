"""Run Final Funding SG and CIBC workbooks using app standard inputs and outputs.

Expects workbook scripts to read FOLDER from environment (Path(os.environ.get("FOLDER"))).
We prepare a temp directory with the same structure as the pipeline (files_required/ under FOLDER),
run the script, then copy FOLDER/output and FOLDER/output_share into storage outputs area
under final_funding_sg/ or final_funding_cibc/ so results appear in the Program Runs file manager.
"""
import os
import shutil
import subprocess
import sys
import logging
import tempfile
from pathlib import Path
from typing import Optional

from config.settings import settings
from storage import get_storage_backend

logger = logging.getLogger(__name__)

FINAL_FUNDING_SG_PREFIX = "final_funding_sg"
FINAL_FUNDING_CIBC_PREFIX = "final_funding_cibc"

# Bundled scripts (same input/output convention: files_required, output, output_share)
_BUNDLED_DIR = Path(__file__).resolve().parent.parent / "scripts"
_BUNDLED_SG = _BUNDLED_DIR / "final_funding_sg.py"
_BUNDLED_CIBC = _BUNDLED_DIR / "final_funding_cibc.py"


def _prepare_temp_input_from_local(input_base: str) -> str:
    """Copy local input_base (must contain files_required/) to a temp dir. Returns path to work dir that has files_required/."""
    base = Path(input_base).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Input directory does not exist: {base}")
    files_required = base / "files_required"
    if not files_required.is_dir():
        raise FileNotFoundError(f"Input directory must contain files_required/: {base}")
    parent = Path(tempfile.mkdtemp(prefix="loan_engine_final_funding_"))
    work_dir = parent / "work"
    work_dir.mkdir()
    try:
        shutil.copytree(base, work_dir, dirs_exist_ok=True)
        return str(work_dir.resolve())
    except Exception:
        shutil.rmtree(parent, ignore_errors=True)
        raise


def _prepare_temp_input_from_s3(prefix: str) -> str:
    """Sync S3 inputs prefix to temp dir. Returns path to temp dir (with files_required under it if prefix is like 'input')."""
    from orchestration.s3_input_sync import sync_s3_input_to_temp
    input_storage = get_storage_backend(area="inputs")
    return sync_s3_input_to_temp(input_storage, prefix)


def _run_workbook_script(script_path: str, folder: str) -> None:
    """Run the workbook Python script with FOLDER env set."""
    env = os.environ.copy()
    env["FOLDER"] = folder
    # Use sys.executable so the subprocess always runs under the same interpreter
    # (and thus the same venv) as the backend — avoids missing-package errors on
    # Windows where the system `python` may differ from the venv python.
    python_exe = os.environ.get("PYTHON") or sys.executable
    logger.debug("Running %s with interpreter %s, FOLDER=%s", script_path, python_exe, folder)
    result = subprocess.run(
        [python_exe, script_path],
        env=env,
        cwd=str(Path(script_path).parent),
        capture_output=True,
        text=True,
        timeout=3600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Script failed: {result.stderr or result.stdout or 'unknown error'}")


def _upload_local_output_to_storage(local_folder: str, output_prefix: str) -> None:
    """Copy local_folder/output to outputs area and local_folder/output_share to output_share area (same convention as main runs)."""
    folder_path = Path(local_folder)
    output_storage = get_storage_backend(area="outputs")
    share_storage = get_storage_backend(area="output_share")
    # output -> outputs area under output_prefix
    src_out = folder_path / "output"
    if src_out.is_dir():
        for f in src_out.rglob("*"):
            if f.is_file():
                rel = f.relative_to(src_out)
                key = f"{output_prefix}/{rel.as_posix()}"
                output_storage.write_file(key, f.read_bytes())
                logger.debug("Uploaded %s -> outputs/%s", f, key)
    # output_share -> output_share area under output_prefix
    src_share = folder_path / "output_share"
    if src_share.is_dir():
        for f in src_share.rglob("*"):
            if f.is_file():
                rel = f.relative_to(src_share)
                key = f"{output_prefix}/{rel.as_posix()}"
                share_storage.write_file(key, f.read_bytes())
                logger.debug("Uploaded %s -> output_share/%s", f, key)


def _bridge_cashflow_outputs_to_inputs(temp_dir: str, storage_type: str) -> None:
    """Copy current_assets.csv from outputs storage area into temp files_required/ if present.

    This bridges cashflow outputs into Final Funding inputs without requiring Ops to
    manually download and re-upload the file. Silent no-op when file is absent.
    """
    files_required = Path(temp_dir) / "files_required"
    try:
        output_storage = get_storage_backend(area="outputs")
        all_outputs = output_storage.list_files("", recursive=True)
    except Exception as e:
        logger.warning("Cashflow bridge: could not list outputs area (%s) — skipping", e)
        return
    candidates = [
        f for f in all_outputs
        if f.path.endswith("current_assets.csv")
    ]
    if not candidates:
        logger.debug("Cashflow bridge: no current_assets.csv in outputs area — skipping")
        return
    # Sort by last_modified descending — take the most recent
    candidates.sort(key=lambda f: f.last_modified or "", reverse=True)
    best = candidates[0]
    try:
        content = output_storage.read_file(best.path)
        files_required.mkdir(parents=True, exist_ok=True)
        (files_required / "current_assets.csv").write_bytes(content)
        logger.info("Cashflow bridge: copied %s → files_required/current_assets.csv", best.path)
    except Exception as e:
        logger.warning("Cashflow bridge: failed to copy %s (%s) — skipping", best.path, e)


def _resolve_script_path(env_key: str, settings_attr: str, bundled: Path) -> str:
    """Use env/settings path if set and file exists; otherwise use bundled script if present."""
    script_path = getattr(settings, settings_attr, None) or os.environ.get(env_key)
    if script_path and Path(script_path).exists():
        return str(Path(script_path).resolve())
    if bundled.exists():
        return str(bundled)
    raise FileNotFoundError(
        f"{env_key} not set or file not found, and bundled script missing at {bundled}. "
        "Set it to the path of the script. Script must use folder = Path(os.environ.get('FOLDER')) at the top, "
        "with input under folder/files_required and output under folder/output and folder/output_share."
    )


def execute_final_funding_sg(folder: Optional[str] = None) -> str:
    """
    Run Final Funding SG workbook. Uses app inputs (folder or INPUT_DIR) and writes to outputs/final_funding_sg/.
    Same convention as main runs: input from files_required, output to output and output_share.
    Returns output prefix for file manager.
    """
    script_path = _resolve_script_path("FINAL_FUNDING_SG_SCRIPT_PATH", "FINAL_FUNDING_SG_SCRIPT_PATH", _BUNDLED_SG)
    return _execute_final_funding(script_path, FINAL_FUNDING_SG_PREFIX, folder)


def execute_final_funding_cibc(folder: Optional[str] = None) -> str:
    """
    Run Final Funding CIBC workbook. Uses app inputs and writes to outputs/final_funding_cibc/.
    Same convention as main runs: input from files_required, output to output and output_share.
    Returns output prefix for file manager.
    """
    script_path = _resolve_script_path("FINAL_FUNDING_CIBC_SCRIPT_PATH", "FINAL_FUNDING_CIBC_SCRIPT_PATH", _BUNDLED_CIBC)
    return _execute_final_funding(script_path, FINAL_FUNDING_CIBC_PREFIX, folder)


def _execute_final_funding(script_path: str, output_prefix: str, folder: Optional[str]) -> str:
    storage_type = getattr(settings, "STORAGE_TYPE", "local")
    temp_dir = None
    try:
        if storage_type == "s3":
            from orchestration.s3_input_sync import remove_temp_input_dir
            # For S3, sync from the configured inputs area root (S3_INPUT/S3_INPUTS_PREFIX).
            # The folder argument, when provided, is a sub-prefix under that inputs area
            # (e.g. "legacy"), not including the inputs base itself. If the UI sends the
            # literal S3_INPUT (e.g. "input"), treat that as the root of the inputs area
            # to avoid doubling the prefix (input/input/...).
            base_input_prefix = (getattr(settings, "S3_INPUT", None) or getattr(settings, "S3_INPUTS_PREFIX", "input") or "").strip("/")
            requested = (folder or "").strip("/")
            if not requested or requested == base_input_prefix:
                s3_prefix = ""
            else:
                s3_prefix = requested
            temp_dir = _prepare_temp_input_from_s3(s3_prefix)
            try:
                _bridge_cashflow_outputs_to_inputs(temp_dir, "s3")
                _run_workbook_script(script_path, temp_dir)
                _upload_local_output_to_storage(temp_dir, output_prefix)
            finally:
                remove_temp_input_dir(temp_dir)
        else:
            input_base = folder or getattr(settings, "INPUT_DIR", "./data/inputs")
            # If folder is a path segment under INPUT_DIR (e.g. "legacy"), resolve it
            if folder and not Path(folder).is_absolute():
                input_base = str(Path(settings.INPUT_DIR) / folder)
            else:
                input_base = folder or str(Path(settings.INPUT_DIR).resolve())
            logger.info("Final funding local input_base=%s (resolved from INPUT_DIR=%s, folder=%s)", input_base, settings.INPUT_DIR, folder)
            temp_dir = _prepare_temp_input_from_local(input_base)
            try:
                _bridge_cashflow_outputs_to_inputs(temp_dir, "local")
                _run_workbook_script(script_path, temp_dir)
                _upload_local_output_to_storage(temp_dir, output_prefix)
            finally:
                try:
                    shutil.rmtree(Path(temp_dir).parent, ignore_errors=True)
                except Exception:
                    pass
        return output_prefix
    except Exception as e:
        logger.exception("Final funding run failed: %s", e)
        raise
