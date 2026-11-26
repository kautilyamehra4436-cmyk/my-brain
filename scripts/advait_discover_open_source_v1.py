"""Run a bounded GitHub public open-source discovery query for Advait."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.opensource_discovery_v1 import DiscoveryError, GitHubOpenSourceDiscoveryV1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Capability request, e.g. 'python csv data processing'")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    try:
        result = GitHubOpenSourceDiscoveryV1().search(args.query, limit=args.limit)
    except DiscoveryError as exc:
        print(json.dumps({"status": "unavailable", "reason": str(exc),
                          "installed": False, "executed": False}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in {"candidates_found", "needs_clarification",
                                     "no_verified_license_candidates"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
