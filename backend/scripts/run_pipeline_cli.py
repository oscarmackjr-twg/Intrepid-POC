"""Run the pipeline from the command line for troubleshooting.

Use this when a run is stuck in the UI (e.g. "Running eligibility checks") and you need
full logs and stack traces to find the failure. All pipeline log output goes to stdout.

Database: same as the app. Set DATABASE_URL (and for QA, STORAGE_TYPE=s3, AWS creds) in backend/.env
or in the environment. The script loads backend/.env when run from repo root.
For QA (S3): use --sync-s3 to pull inputs to a temp dir.

Usage:

  # Run with local folder and optional pdate (from repo root, with backend on PYTHONPATH or run from backend/)
  python backend/scripts/run_pipeline_cli.py --folder path/to/inputs --pdate 2026-03-04

  # QA: sync S3 inputs to temp dir and run (same as API does)
  python backend/scripts/run_pipeline_cli.py --sync-s3 --pdate 2026-03-04

  # Re-run using the same parameters as an existing (e.g. stuck) run. Loads pdate, input path, etc. from DB.
  # Use --sync-s3 if that run used S3 inputs.
  python backend/scripts/run_pipeline_cli.py --run-id run_886742a6378a_20260301_223021 --sync-s3

  # Optional: IRR target, sales team, tday (base date for file naming)
  python backend/scripts/run_pipeline_cli.py --folder ./legacy --pdate 2026-03-04 --irr-target 8.05 --tday 2026-03-01
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Add backend to path when run as script
_script_dir = Path(__file__).resolve().parent
_backend = _script_dir.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Load backend/.env so DATABASE_URL and other settings are found when run from repo root.
# (Pydantic-settings looks for .env in the current working directory.)
_backend_env = _backend / ".env"
_cwd = os.getcwd()
if _backend_env.exists():
    try:
        os.chdir(_backend)
    finally:
        pass  # chdir back after importing
# Import settings now so .env is loaded from backend/ when present
import config.settings as _settings_module  # noqa: F401
if _backend_env.exists():
    os.chdir(_cwd)

# Configure logging to stdout so all pipeline phases and errors are visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)

from db.connection import SessionLocal
from db.models import PipelineRun
from config.settings import settings
from orchestration.run_context import RunContext
from orchestration.pipeline import PipelineExecutor
from orchestration.s3_input_sync import sync_s3_input_to_temp, remove_temp_input_dir
from storage import get_storage_backend


def main():
    parser = argparse.ArgumentParser(
        description="Run the pipeline from the command line (full logs to stdout for troubleshooting).",
        epilog="Example: python backend/scripts/run_pipeline_cli.py --run-id run_xxx --sync-s3",
    )
    parser.add_argument("--folder", type=str, help="Local input folder path (ignored if --run-id or --sync-s3 without --folder).")
    parser.add_argument("--pdate", type=str, help="Purchase date YYYY-MM-DD. Default: next Tuesday.")
    parser.add_argument("--tday", type=str, help="Base date YYYY-MM-DD for file naming. Default: today.")
    parser.add_argument("--irr-target", type=float, default=8.05, help="IRR target percentage.")
    parser.add_argument("--sales-team-id", type=int, default=None, help="Sales team ID.")
    parser.add_argument(
        "--run-id",
        type=str,
        metavar="RUN_ID",
        help="Use parameters from this run (pdate, input path, etc.). Use --sync-s3 if that run used S3.",
    )
    parser.add_argument(
        "--sync-s3",
        action="store_true",
        help="Sync S3 inputs to a temp dir and use as folder (required for QA when inputs are in S3).",
    )
    args = parser.parse_args()

    temp_dir = None
    folder = None
    context = None

    if args.run_id:
        db = SessionLocal()
        try:
            run = db.query(PipelineRun).filter(PipelineRun.run_id == args.run_id).first()
            if not run:
                print(f"Run not found: {args.run_id}", file=sys.stderr)
                sys.exit(1)
            pdate = run.pdate
            tday = run.pdate  # match file naming to original run
            input_path = run.input_file_path or ""
            output_dir = run.output_dir or f"runs/cli_{args.run_id[:20]}"
            sales_team_id = run.sales_team_id
            irr_target = run.irr_target if run.irr_target is not None else args.irr_target
            print(f"Re-running with same parameters as run_id={args.run_id}: pdate={pdate}, input_file_path={input_path}")
        finally:
            db.close()

        context = RunContext.create(
            sales_team_id=sales_team_id,
            created_by_id=None,
            pdate=pdate,
            irr_target=irr_target,
            tday=tday,
        )
        context.input_file_path = input_path
        context.output_dir = f"cli_debug/{context.run_id}"
        if args.sync_s3 or settings.STORAGE_TYPE == "s3":
            print("Syncing S3 inputs...")
            input_storage = get_storage_backend(area="inputs")
            temp_dir = sync_s3_input_to_temp(input_storage, "")
            folder = temp_dir
            print(f"S3 sync done, folder={folder}")
        else:
            # Local: use input path as folder (may be a prefix like "sales_team_1"; for local, a path)
            folder = input_path if input_path else args.folder
            if not folder or not Path(folder).exists():
                print(f"Local folder not found: {folder}. Use --sync-s3 for S3 runs.", file=sys.stderr)
                sys.exit(1)
    else:
        context = RunContext.create(
            sales_team_id=args.sales_team_id,
            created_by_id=None,
            pdate=args.pdate,
            irr_target=args.irr_target,
            tday=args.tday,
        )
        if args.sync_s3:
            print("Syncing S3 inputs...")
            input_storage = get_storage_backend(area="inputs")
            temp_dir = sync_s3_input_to_temp(input_storage, "")
            folder = temp_dir
            context.input_file_path = ""
            context.output_dir = f"cli_debug/{context.run_id}"
            print(f"S3 sync done, folder={folder}")
        else:
            folder = args.folder
            if not folder:
                print("Provide --folder or --sync-s3 (or --run-id with --sync-s3).", file=sys.stderr)
                sys.exit(1)
            context.input_file_path = folder
            context.output_dir = f"cli_debug/{context.run_id}"

    try:
        print(f"Pipeline starting run_id={context.run_id} folder={folder} pdate={context.pdate}")
        with PipelineExecutor(context) as executor:
            result = executor.execute(folder)
        print("Pipeline completed successfully.")
        print(f"  Run ID: {result['run_id']}")
        print(f"  Total loans: {result['total_loans']}")
        print(f"  Total balance: ${result['total_balance']:,.2f}")
        print(f"  Exceptions: {result['exceptions_count']}")
        sys.exit(0)
    except Exception as e:
        print(f"Pipeline failed: {e}", file=sys.stderr)
        logging.exception("Pipeline execution failed")
        sys.exit(1)
    finally:
        if temp_dir:
            remove_temp_input_dir(temp_dir)


if __name__ == "__main__":
    main()
