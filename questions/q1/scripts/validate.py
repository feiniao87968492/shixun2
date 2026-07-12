#!/usr/bin/env python3
"""Validation and sensitivity analysis for q1."""

from __future__ import annotations

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


def main() -> int:
    root = project_root()
    checks = validate_outputs(root)
    save_table(checks, stem="q1_validation_checks", question_dir=root / "questions" / "q1")
    failed = checks[~checks["passed"]]
    if not failed.empty:
        print(f"[error] q1 validation failed: {len(failed)} missing/empty artifacts")
        print(failed[["kind", "path"]].to_string(index=False))
        return 1
    print(f"[ok] q1 validation passed: {len(checks)} artifact checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
