#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.paths import project_root  # noqa: E402
from analysis import run_analysis  # noqa: E402

IMPLEMENTED = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q1 modeling pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    question_dir = root / "questions" / "q1"

    steps = [
        "load and validate inputs",
        "preprocess data",
        "run baseline",
        "fit or solve main model",
        "validate and diagnose",
        "run sensitivity analysis",
        "save tables, figures, figure data, and metadata",
        "update evidence records",
    ]
    if args.dry_run:
        print("q1 planned pipeline:")
        for index, step in enumerate(steps, start=1):
            print(f"  {index}. {step}")
        print(f"question_dir={question_dir}")
        print(f"config={root / args.config}")
        return 0

    result = run_analysis(root=root, config_path=args.config)
    run_summary = result["run_summary"]
    print("[ok] q1 pipeline completed")
    print(f"question_dir={question_dir}")
    print("summary_order_features=" + ", ".join(run_summary["summary_order_features"]))
    print("stable_key_features=" + ", ".join(run_summary["stable_key_features"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
