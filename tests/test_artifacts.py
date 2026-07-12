from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.artifacts import save_figure_bundle, save_table  # noqa: E402


def test_artifact_csv_writers_use_stable_float_precision(tmp_path: Path) -> None:
    frame = pd.DataFrame({"metric": ["x"], "value": [1.2345678901234567]})

    table_path = save_table(frame, stem="stable_table", question_dir=tmp_path)["csv"]
    assert table_path.read_bytes() == b"metric,value\nx,1.23456789012\n"

    fig = Figure()
    ax = fig.subplots()
    ax.plot([0, 1], [0, 1])

    bundle = save_figure_bundle(
        fig=fig,
        data=frame,
        stem="stable_figure",
        question_dir=tmp_path,
        title="Stable figure",
        source_script="tests/test_artifacts.py",
    )
    assert bundle["data"].read_bytes() == b"metric,value\nx,1.23456789012\n"
    assert b"\r" not in bundle["metadata"].read_bytes()
