#!/usr/bin/env python3
"""Paper-level visualization for q1."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis import (  # noqa: E402
    clean_golf_data,
    create_visualizations,
    load_config,
    load_raw_golf_data,
)
from modeling_common.paths import project_root  # noqa: E402


def main() -> int:
    root = project_root()
    qdir = root / "questions" / "q1"
    tables_dir = qdir / "artifacts" / "tables"
    required = {
        "q1_pearson_correlation": "q1_pearson_correlation.csv",
        "q1_spearman_correlation": "q1_spearman_correlation.csv",
        "q1_feature_ranking": "q1_feature_ranking.csv",
        "q1_rank_stability": "q1_rank_stability.csv",
    }
    if not all((tables_dir / filename).exists() for filename in required.values()):
        raise SystemExit("Run questions/q1/scripts/pipeline.py before visualize.py")

    import pandas as pd

    tables = {name: pd.read_csv(tables_dir / filename) for name, filename in required.items()}
    clean = clean_golf_data(load_raw_golf_data(root))
    config = load_config(root, "configs/default.yaml")
    create_visualizations(
        clean=clean,
        tables=tables,
        question_dir=qdir,
        dpi=int(config.get("plot", {}).get("dpi", 300)),
    )
    print("[ok] q1 figures regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
