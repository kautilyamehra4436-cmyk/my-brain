"""Run read-only root-file vetting on one public GitHub repository."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.repository_vetting_v1 import GitHubRepositoryVetterV1, VettingError


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Public GitHub owner/name")
    args=parser.parse_args()
    try:
        result=GitHubRepositoryVetterV1().inspect(args.repo)
    except (VettingError, ValueError) as exc:
        print(json.dumps({"status":"blocked","reason":str(exc),
                          "installed":False,"executed":False},sort_keys=True))
        return 2
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
