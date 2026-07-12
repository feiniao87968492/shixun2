#!/usr/bin/env python3
"""Paper-level visualization for q2."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.artifacts import save_figure_bundle  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402


def _selected_predictions(question_dir: Path) -> pd.DataFrame:
    tables = question_dir / "artifacts" / "tables"
    predictions = pd.read_csv(tables / "q2_supervised_predictions.csv")
    metrics = pd.read_csv(tables / "q2_supervised_metrics.csv")
    selected = metrics[metrics["selected"].astype(bool)][["target", "feature_set", "model"]]
    return predictions.merge(selected, on=["target", "feature_set", "model"], how="inner")


def create_visualizations(*, root: Path, dpi: int = 300) -> dict[str, dict[str, Path]]:
    question_dir = root / "questions" / "q2"
    tables = question_dir / "artifacts" / "tables"
    outputs: dict[str, dict[str, Path]] = {}
    selected = _selected_predictions(question_dir)
    target_stems = {
        "carry_distance_yd": "carry",
        "apex_height_yd": "apex",
    }
    for target, stem_suffix in target_stems.items():
        data = selected[selected["target"] == target].copy()
        fig, ax = plt.subplots(figsize=(5.2, 4.2))
        ax.scatter(data["actual"], data["predicted"], s=18, alpha=0.72)
        low = min(data["actual"].min(), data["predicted"].min())
        high = max(data["actual"].max(), data["predicted"].max())
        ax.plot([low, high], [low, high], color="#444444", linewidth=1.0)
        ax.set_xlabel("Actual (yd)")
        ax.set_ylabel("Predicted (yd)")
        ax.set_title(f"{stem_suffix} prediction")
        outputs[f"q2_prediction_scatter_{stem_suffix}"] = save_figure_bundle(
            fig=fig,
            data=data,
            stem=f"q2_prediction_scatter_{stem_suffix}",
            question_dir=question_dir,
            title=f"Q2 {stem_suffix} prediction scatter",
            source_script="questions/q2/scripts/visualize.py",
            notes="Selected supervised model on fixed test split.",
            dpi=dpi,
        )
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(5.2, 4.2))
        ax.scatter(data["predicted"], data["residual"], s=18, alpha=0.72)
        ax.axhline(0.0, color="#444444", linewidth=1.0)
        ax.set_xlabel("Predicted (yd)")
        ax.set_ylabel("Residual, predicted - actual (yd)")
        ax.set_title(f"{stem_suffix} residuals")
        outputs[f"q2_residuals_{stem_suffix}"] = save_figure_bundle(
            fig=fig,
            data=data,
            stem=f"q2_residuals_{stem_suffix}",
            question_dir=question_dir,
            title=f"Q2 {stem_suffix} residual plot",
            source_script="questions/q2/scripts/visualize.py",
            notes="Residual diagnostics for selected supervised model.",
            dpi=dpi,
        )
        plt.close(fig)

    ode_metrics = pd.read_csv(tables / "q2_ode_model_comparison.csv")
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    x = range(len(ode_metrics))
    ax.bar([value - 0.18 for value in x], ode_metrics["carry_rmse"], width=0.36, label="carry RMSE")
    ax.bar([value + 0.18 for value in x], ode_metrics["apex_rmse"], width=0.36, label="apex RMSE")
    ax.set_xticks(list(x), ode_metrics["model"])
    ax.set_ylabel("RMSE (yd)")
    ax.set_title("ODE first-stage model comparison")
    ax.legend()
    outputs["q2_ode_model_comparison"] = save_figure_bundle(
        fig=fig,
        data=ode_metrics,
        stem="q2_ode_model_comparison",
        question_dir=question_dir,
        title="Q2 ODE model comparison",
        source_script="questions/q2/scripts/visualize.py",
        notes="Vacuum and drag-only ODE models on the fixed test split.",
        dpi=dpi,
    )
    plt.close(fig)

    surface = pd.read_csv(tables / "q2_ode_parameter_surface.csv")
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    ax.plot(surface["cd"], surface["objective"], marker="o")
    ax.set_xlabel("C_D")
    ax.set_ylabel("Training objective")
    ax.set_title("Preliminary drag-only parameter scan")
    outputs["q2_ode_parameter_surface"] = save_figure_bundle(
        fig=fig,
        data=surface,
        stem="q2_ode_parameter_surface",
        question_dir=question_dir,
        title="Q2 preliminary drag parameter surface",
        source_script="questions/q2/scripts/visualize.py",
        notes="First-stage one-dimensional C_D scan; not final C_D/C_L calibration.",
        dpi=dpi,
    )
    plt.close(fig)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q2 visualization")
    parser.add_argument("--config", default="configs/default.yaml")
    return parser.parse_args()


def main() -> int:
    _ = parse_args()
    root = project_root()
    create_visualizations(root=root)
    print("[ok] q2 figures regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
