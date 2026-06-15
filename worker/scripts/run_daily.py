"""CLI wrapper around the daily pipeline (the scheduler will call /run-daily later).

Usage (from worker/):
    python scripts/run_daily.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline import run_daily  # noqa: E402


def main() -> None:
    summary = run_daily()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
