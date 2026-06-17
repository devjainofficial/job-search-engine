"""CLI: delete-my-data (DPDP). Erases a user and all derived personal data.

Usage (from worker/):
    python scripts/delete_user.py --user-id <uuid>
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import delete_user_data  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete a user and all their data.")
    parser.add_argument("--user-id", required=True, help="users.id (uuid)")
    args = parser.parse_args()
    print(delete_user_data(args.user_id))


if __name__ == "__main__":
    main()
