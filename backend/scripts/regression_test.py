"""Data regression test harness for pipeline output validation.

Discovers buy-date test case folders, runs the pipeline CLI against each,
diffs generated outputs against expected outputs byte-for-byte, and prints
a summary report.

Usage (from repo root):
    python backend/scripts/regression_test.py
    python backend/scripts/regression_test.py --test-data C:\\Users\\omack\\Downloads\\TestData
    python backend/scripts/regression_test.py --pdate 2026-02-24 --tday 2026-02-19
    python backend/scripts/regression_test.py --no-cleanup  # keep generated outputs for inspection

TestData folder structure:
    <test-data-dir>/
        {buy_date_folder}/          # e.g. 93rd_buy or any name
            files_required/         # pipeline input files live here
            outputs/
                <expected output files>
            output_share/           # optional
                <expected output_share files>

Each buy-date folder is run independently. The pipeline CLI is called with
    --folder <buy_date_folder> --pdate <pdate> --tday <tday>
and outputs land in backend/cli_debug/{run_id}/.

Generated outputs are compared file-by-file against the expected outputs.
Missing files, extra files, and byte-level differences are all reported.

Exit code: 0 if all cases PASS, 1 if any case FAILS.
"""
import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Return the repo root (parent of backend/)."""
    return Path(__file__).resolve().parent.parent.parent


def _default_backend_dir() -> Path:
    return _repo_root() / "backend"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_test_cases(test_data_dir: Path) -> list[Path]:
    """Return sorted list of valid test-case directories under test_data_dir."""
    if not test_data_dir.exists():
        print(f"[WARN] Test data directory not found: {test_data_dir}", file=sys.stderr)
        return []

    cases = []
    for subdir in sorted(test_data_dir.iterdir()):
        if not subdir.is_dir():
            continue
        # Input files live in files_required/ subdirectory
        files_required = subdir / "files_required"
        has_files = files_required.is_dir() and any(f.is_file() for f in files_required.iterdir())
        # Must have outputs/ or output_share/
        has_expected = (subdir / "outputs").is_dir() or (subdir / "output_share").is_dir()
        if not has_files:
            print(f"[WARN] Skipping {subdir.name}: no input files found in files_required/")
            continue
        if not has_expected:
            print(f"[WARN] Skipping {subdir.name}: no outputs/ or output_share/ directory")
            continue
        cases.append(subdir)

    return cases


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _load_dates_config(test_data_dir: Path) -> dict:
    """Load optional dates.json from TestData root. Returns {folder_name: {pdate, tday}}."""
    config_path = test_data_dir / "dates.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as exc:
        print(f"[WARN] Could not read dates.json: {exc}")
        return {}


def _derive_dates(folder_name: str, cli_pdate: str | None, cli_tday: str | None, dates_config: dict | None = None) -> tuple[str, str]:
    """Return (pdate, tday) for a test case.

    Priority:
    1. CLI args (--pdate / --tday) override everything.
    2. dates.json entry for this folder name.
    3. If folder name looks like YYYY-MM-DD use it as pdate; tday = today.
    4. Fall back: folder name as pdate, today as tday.
    """
    today_str = date.today().isoformat()

    if cli_pdate and cli_tday:
        return cli_pdate, cli_tday

    # Check dates.json config
    if dates_config and folder_name in dates_config:
        entry = dates_config[folder_name]
        pdate = cli_pdate or entry.get("pdate", folder_name)
        tday = cli_tday or entry.get("tday", today_str)
        return pdate, tday

    # Try to parse folder name as YYYY-MM-DD
    try:
        datetime.strptime(folder_name, "%Y-%m-%d")
        pdate = folder_name
    except ValueError:
        pdate = folder_name  # use as-is; CLI will handle or reject

    tday = cli_tday if cli_tday else today_str
    pdate = cli_pdate if cli_pdate else pdate

    return pdate, tday


# ---------------------------------------------------------------------------
# Output directory discovery
# ---------------------------------------------------------------------------

def _find_generated_output_dir(cli_debug_dir: Path, started_after: float) -> Path | None:
    """Find the most recently modified cli_debug/{run_id}/ subdir created after started_after epoch."""
    if not cli_debug_dir.exists():
        return None

    candidates = []
    for subdir in cli_debug_dir.iterdir():
        if not subdir.is_dir():
            continue
        try:
            mtime = subdir.stat().st_mtime
        except OSError:
            continue
        if mtime >= started_after:
            candidates.append((mtime, subdir))

    if not candidates:
        return None

    # Return the most recently modified
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------

def _collect_files(directory: Path) -> dict[str, Path]:
    """Return {relative_path_str: absolute_path} for all files recursively in directory."""
    result = {}
    if not directory.exists():
        return result
    for f in directory.rglob("*"):
        if f.is_file():
            rel = str(f.relative_to(directory))
            result[rel] = f
    return result


def _diff_directories(
    generated_dir: Path,
    expected_dir: Path,
    label: str,
) -> tuple[list[str], list[str], list[str]]:
    """Compare two directories. Returns (diffs, missing, extras).

    diffs   — files that exist in both but differ
    missing — files in expected but not in generated
    extras  — files in generated but not in expected
    """
    diffs: list[str] = []
    missing: list[str] = []
    extras: list[str] = []

    if not expected_dir.exists():
        return diffs, missing, extras

    expected_files = _collect_files(expected_dir)
    generated_files = _collect_files(generated_dir) if generated_dir.exists() else {}

    for rel, exp_path in expected_files.items():
        display = f"{label}/{rel}"
        if rel not in generated_files:
            missing.append(display)
        else:
            try:
                same = filecmp.cmp(str(generated_files[rel]), str(exp_path), shallow=False)
            except OSError as exc:
                diffs.append(f"{display} (compare error: {exc})")
                continue
            if not same:
                diffs.append(display)

    for rel in generated_files:
        if rel not in expected_files:
            extras.append(f"{label}/{rel}")

    return diffs, missing, extras


# ---------------------------------------------------------------------------
# Per-test-case runner
# ---------------------------------------------------------------------------

def run_test_case(
    test_case_dir: Path,
    backend_dir: Path,
    cli_pdate: str | None,
    cli_tday: str | None,
    no_cleanup: bool,
    dates_config: dict | None = None,
) -> dict:
    """Run one test case. Returns result dict."""
    result = {
        "name": test_case_dir.name,
        "status": "FAILED",
        "pipeline_ok": False,
        "diffs": [],
        "missing": [],
        "extra": [],
        "error": None,
        "generated_dir": None,
    }

    pdate, tday = _derive_dates(test_case_dir.name, cli_pdate, cli_tday, dates_config)
    input_dir = test_case_dir / "files_required"
    print(f"\n[BUY DATE: {test_case_dir.name}]")
    print(f"  pdate={pdate}  tday={tday}")
    print(f"  Input dir: {input_dir}")

    cli_debug_dir = backend_dir / "cli_debug"

    try:
        started_epoch = datetime.now().timestamp()

        proc = subprocess.run(
            [
                sys.executable,
                "scripts/run_pipeline_cli.py",
                "--folder", str(input_dir),
                "--pdate", pdate,
                "--tday", tday,
            ],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )

        pipeline_ok = proc.returncode == 0
        result["pipeline_ok"] = pipeline_ok

        if proc.stdout:
            for line in proc.stdout.splitlines():
                print(f"  [CLI] {line}")
        if proc.stderr:
            for line in proc.stderr.splitlines():
                print(f"  [CLI STDERR] {line}")

        if not pipeline_ok:
            result["error"] = f"Pipeline exited with code {proc.returncode}"
            print(f"  Pipeline: FAILED (exit code {proc.returncode})")
            return result

        print("  Pipeline: OK")

        # Find generated output dir
        generated_dir = _find_generated_output_dir(cli_debug_dir, started_epoch)
        if generated_dir is None:
            result["error"] = "No output directory found in cli_debug/ after run"
            print("  Output dir: NOT FOUND")
            return result

        result["generated_dir"] = generated_dir
        print(f"  Output dir: {generated_dir}")

        # Diff outputs/
        expected_outputs = test_case_dir / "outputs"
        if expected_outputs.exists():
            d, m, e = _diff_directories(generated_dir, expected_outputs, "outputs")
            result["diffs"].extend(d)
            result["missing"].extend(m)
            result["extra"].extend(e)

        # Diff output_share/ — the pipeline puts _share alongside the run dir
        expected_share = test_case_dir / "output_share"
        if expected_share.exists():
            # cli_debug/{run_id} is the base; check for a sibling _share dir or subdir
            # The pipeline appends output_share files to a _share subfolder of output_dir
            generated_share = Path(str(generated_dir) + "_share")
            if not generated_share.exists():
                # Fallback: check for output_share/ subdirectory inside run dir
                generated_share = generated_dir / "output_share"
            d, m, e = _diff_directories(generated_share, expected_share, "output_share")
            result["diffs"].extend(d)
            result["missing"].extend(m)
            result["extra"].extend(e)

        # Determine overall pass/fail
        total_issues = len(result["diffs"]) + len(result["missing"]) + len(result["extra"])
        result["status"] = "PASS" if total_issues == 0 else "FAILED"

        # Print diff summary
        if total_issues == 0:
            print("  Diff result: PASS (0 diffs)")
        else:
            print(f"  Diff result: FAIL ({total_issues} differences)")
            for item in result["diffs"]:
                print(f"    DIFF: {item} (generated differs from expected)")
            for item in result["missing"]:
                print(f"    MISSING: {item} (expected but not generated)")
            for item in result["extra"]:
                print(f"    EXTRA: {item} (generated but not expected)")

    except subprocess.TimeoutExpired:
        result["error"] = "Pipeline timed out after 300 seconds"
        print("  Pipeline: FAILED (timeout)")
    except Exception as exc:
        result["error"] = str(exc)
        print(f"  Pipeline: FAILED (exception: {exc})")
    finally:
        # Cleanup generated output dir
        if not no_cleanup and result.get("generated_dir") is not None:
            gen = result["generated_dir"]
            try:
                shutil.rmtree(str(gen))
                # Also remove _share dir if it exists
                share_dir = Path(str(gen) + "_share")
                if share_dir.exists():
                    shutil.rmtree(str(share_dir))
            except OSError as exc:
                print(f"  [WARN] Could not clean up {gen}: {exc}")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Data regression harness: runs the pipeline against each buy-date folder "
            "in TestData and diffs outputs against expected values."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
TestData structure:
  <test-data-dir>/
    {buy_date_folder}/
      files_required/    <- pipeline input files
      outputs/           <- expected pipeline outputs
      output_share/      <- expected output_share files (optional)

Examples:
  python backend/scripts/regression_test.py
  python backend/scripts/regression_test.py --test-data C:\\Users\\omack\\Downloads\\TestData
  python backend/scripts/regression_test.py --pdate 2026-02-24 --tday 2026-02-19
  python backend/scripts/regression_test.py --no-cleanup
""",
    )
    parser.add_argument(
        "--test-data",
        type=str,
        default=r"C:\Users\omack\Downloads\TestData",
        help="Root directory containing buy-date test case folders. "
             r"Default: C:\Users\omack\Downloads\TestData",
    )
    parser.add_argument(
        "--backend-dir",
        type=str,
        default=None,
        help="Path to the backend/ directory. Default: auto-detected from script location.",
    )
    parser.add_argument(
        "--pdate",
        type=str,
        default=None,
        help="Purchase date YYYY-MM-DD. Applied to ALL test cases. "
             "If omitted, derived from each folder name (or today if folder name is not a date).",
    )
    parser.add_argument(
        "--tday",
        type=str,
        default=None,
        help="Base date YYYY-MM-DD for file naming. Applied to ALL test cases. "
             "Default: today (or derived from folder name).",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not delete generated cli_debug/{run_id}/ directories after each test case. "
             "Useful for inspecting outputs when a diff fails.",
    )
    args = parser.parse_args()

    test_data_dir = Path(args.test_data)
    backend_dir = Path(args.backend_dir) if args.backend_dir else _default_backend_dir()

    if not backend_dir.exists():
        print(f"ERROR: backend directory not found: {backend_dir}", file=sys.stderr)
        sys.exit(1)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print(f"REGRESSION TEST REPORT — {now_str}")
    print(f"Test data: {test_data_dir}")
    print("=" * 60)

    test_cases = discover_test_cases(test_data_dir)
    dates_config = _load_dates_config(test_data_dir)

    if not test_cases:
        print("\nNo valid test cases found. Nothing to run.")
        print("\n" + "=" * 60)
        print("SUMMARY: 0 PASSED / 0 FAILED / 0 TOTAL")
        print("=" * 60)
        sys.exit(0)

    results = []
    for case_dir in test_cases:
        result = run_test_case(
            test_case_dir=case_dir,
            backend_dir=backend_dir,
            cli_pdate=args.pdate,
            cli_tday=args.tday,
            no_cleanup=args.no_cleanup,
            dates_config=dates_config,
        )
        results.append(result)

    # Final summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] != "PASS")
    total = len(results)

    print("\n" + "=" * 60)
    print(f"SUMMARY: {passed} PASSED / {failed} FAILED / {total} TOTAL")
    print("=" * 60)

    if failed > 0:
        print("\nFailed cases:")
        for r in results:
            if r["status"] != "PASS":
                err_note = f" — {r['error']}" if r["error"] else ""
                print(f"  FAIL: {r['name']}{err_note}")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
