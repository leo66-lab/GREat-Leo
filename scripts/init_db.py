from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules import repository as repo  # noqa: E402
from modules import services  # noqa: E402
from modules.config import DB_PATH  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the GRE Vocabulary SQLite database.")
    parser.add_argument("--seed", action="store_true", help="Insert sample GRE vocabulary data.")
    args = parser.parse_args()

    repo.ensure_bootstrap_data()
    print(f"Database ready: {DB_PATH}")
    if args.seed:
        result = services.seed_sample_data()
        print(f"Sample data ready: {result}")


if __name__ == "__main__":
    main()

