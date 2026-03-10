"""Run the Tagging phase: splits loans between SG and CIBC.

Uses the bundled backend/scripts/tagging.py (mirrors loan_engine tagging.py logic).
After running, the four split exhibit files (_sg.xlsx, _cibc.xlsx) are copied back
into the real INPUT_DIR/files_required/ so that Final Funding can read them directly.
"""
import os
import shutil
import subprocess
import sys
import logging
import tempfile
from pathlib import Path

from config.settings import settings
from storage import get_storage_backend

logger = logging.getLogger(__name__)

TAGGING_OUTPUT_PREFIX = "tagging"
_BUNDLED_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "tagging.py"


def _run_tagging_script(script_path: str, folder: str, pdate: str = "", irr_target: float = 7.9) -> None:
    env = os.environ.copy()
    env["FOLDER"] = folder
    env["PDATE"] = pdate
    env["IRR_TARGET"] = str(irr_target)
    python_exe = os.environ.get("PYTHON") or sys.executable
    result = subprocess.run(
        [python_exe, script_path],
        env=env,
        cwd=str(Path(script_path).parent),
        capture_output=True,
        text=True,
        timeout=3600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Tagging script failed: {result.stderr or result.stdout or 'unknown error'}")
    logger.info("Tagging script stdout: %s", result.stdout[-2000:] if result.stdout else "")


def _copy_split_files_to_input(temp_dir: str, input_files_required: Path) -> None:
    """Copy the _sg and _cibc exhibit files from temp files_required back to the real input directory."""
    src = Path(temp_dir) / "files_required"
    input_files_required.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in src.glob("*"):
        if f.is_file() and ("_sg." in f.name or "_cibc." in f.name):
            dest = input_files_required / f.name
            shutil.copy2(f, dest)
            logger.info("Tagging: copied %s -> %s", f.name, dest)
            copied += 1
    logger.info("Tagging: copied %d split files to %s", copied, input_files_required)


def execute_tagging(pdate: str = "", irr_target: float = 7.9) -> str:
    """
    Execute the Tagging program run.
    - Reads raw exhibit files from INPUT_DIR/files_required/
    - Writes _sg.xlsx and _cibc.xlsx split files back to INPUT_DIR/files_required/
    - Also uploads output/ files to outputs/tagging/ for the file manager
    Returns the output prefix path ('tagging').
    """
    script_path = str(_BUNDLED_SCRIPT)
    if not _BUNDLED_SCRIPT.exists():
        raise FileNotFoundError(f"Bundled tagging script not found: {_BUNDLED_SCRIPT}")

    storage_type = getattr(settings, "STORAGE_TYPE", "local")

    if storage_type == "s3":
        from orchestration.s3_input_sync import sync_s3_input_to_temp, remove_temp_input_dir
        input_storage = get_storage_backend(area="inputs")
        temp_dir = sync_s3_input_to_temp(input_storage, "")
        (Path(temp_dir) / "output").mkdir(exist_ok=True)
        try:
            _run_tagging_script(script_path, temp_dir, pdate, irr_target)
            # Upload split files back to S3 inputs area
            for f in (Path(temp_dir) / "files_required").glob("*"):
                if f.is_file() and ("_sg." in f.name or "_cibc." in f.name):
                    input_storage.write_file(f"files_required/{f.name}", f.read_bytes())
                    logger.info("Tagging: uploaded %s to S3 inputs", f.name)
            # Upload output/ to outputs/tagging/
            output_storage = get_storage_backend(area="outputs")
            for f in (Path(temp_dir) / "output").rglob("*"):
                if f.is_file():
                    key = f"{TAGGING_OUTPUT_PREFIX}/{f.relative_to(Path(temp_dir) / 'output').as_posix()}"
                    output_storage.write_file(key, f.read_bytes())
        finally:
            remove_temp_input_dir(temp_dir)
        return TAGGING_OUTPUT_PREFIX

    # Local storage
    input_base = Path(settings.INPUT_DIR).resolve()
    input_files_required = input_base / "files_required"
    if not input_files_required.is_dir():
        raise FileNotFoundError(f"files_required/ not found under INPUT_DIR: {input_base}")

    parent = Path(tempfile.mkdtemp(prefix="loan_engine_tagging_"))
    work_dir = parent / "work"
    work_dir.mkdir()
    try:
        shutil.copytree(input_base, work_dir, dirs_exist_ok=True)
        (work_dir / "output").mkdir(exist_ok=True)
        _run_tagging_script(script_path, str(work_dir), pdate, irr_target)
        # Copy split files back to the real input files_required/
        _copy_split_files_to_input(str(work_dir), input_files_required)
        # Copy output/ to outputs/tagging/ for file manager
        output_base = Path(settings.OUTPUT_DIR) / TAGGING_OUTPUT_PREFIX
        output_base.mkdir(parents=True, exist_ok=True)
        for f in (work_dir / "output").rglob("*"):
            if f.is_file():
                dest = output_base / f.relative_to(work_dir / "output")
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
    finally:
        shutil.rmtree(parent, ignore_errors=True)

    return TAGGING_OUTPUT_PREFIX
