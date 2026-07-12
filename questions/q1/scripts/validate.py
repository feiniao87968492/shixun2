#!/usr/bin/env python3
"""Validation and sensitivity analysis for q1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis import validate_outputs  # noqa: E402
from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="validate q1 generated artifacts and numeric checks")
    parser.add_argument("--config", default="configs/default.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    del args
    root = project_root()
    checks = validate_outputs(root)
    save_table(checks, stem="q1_validation_checks", question_dir=root / "questions" / "q1")
    failed = checks[~checks["passed"]]
    if not failed.empty:
        print(f"[error] q1 validation failed: {len(failed)} checks")
        print(failed[["check", "kind", "path", "details"]].to_string(index=False))
        return 1
    print(f"[ok] q1 validation passed: {len(checks)} artifact checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
