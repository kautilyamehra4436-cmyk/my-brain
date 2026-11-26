"""One-request OpenRouter :free smoke check via the canonical provider router."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.openrouter_smoke_common import run_smoke


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    return run_smoke("v3", args.model, 35)


if __name__ == "__main__":
    sys.exit(main())
