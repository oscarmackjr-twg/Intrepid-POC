"""Cashflow worker entrypoint used by local subprocesses and ECS tasks."""

from __future__ import annotations

import sys

from cashflow.routes import run_cashflow_worker_main


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m cashflow.worker <job_id>")
    run_cashflow_worker_main(sys.argv[1])


if __name__ == "__main__":
    main()

