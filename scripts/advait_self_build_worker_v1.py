"""Run a bounded, zero-cost Advait self-build worker cycle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.self_build_runtime_v1 import SelfBuildRuntimeV1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", required=True, help="Directory for local SQLite queue and tool registry")
    parser.add_argument("--enqueue-sample", action="store_true",
                        help="Queue one synthetic, non-sensitive local word-count tool task")
    parser.add_argument("--max-tasks", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_tasks <= 20:
        parser.error("--max-tasks must be between 1 and 20")

    runtime = SelfBuildRuntimeV1(Path(args.db_dir))
    if args.enqueue_sample:
        existing = runtime.factory.list_tools()
        next_patch = len(existing) + 1
        spec = {
            "name": "text.counter",
            "version": f"1.0.{next_patch}",
            "operation": "text.word_count",
            "description": "Counts words, characters and lines in bounded local text",
        }
        task_id = runtime.enqueue_tool_build(
            spec, {"text": "Advait builds and verifies local tools"},
            title="Synthetic self-build factory validation task",
        )
    else:
        task_id = None

    report = runtime.run_until_idle(args.max_tasks)
    report["sample_task_id"] = task_id
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
