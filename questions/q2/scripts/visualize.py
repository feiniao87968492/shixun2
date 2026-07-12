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
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    x = range(len(ode_metrics))
    ax.bar([value - 0.18 for value in x], ode_metrics["carry_rmse"], width=0.36, label="carry RMSE")
    ax.bar([value + 0.18 for value in x], ode_metrics["apex_rmse"], width=0.36, label="apex RMSE")
    ax.set_xticks(list(x), ode_metrics["model"], rotation=15, ha="right")
    ax.set_ylabel("RMSE (yd)")
    ax.set_title("ODE model comparison")
    ax.legend()
    outputs["q2_ode_model_comparison"] = save_figure_bundle(
        fig=fig,
        data=ode_metrics,
        stem="q2_ode_model_comparison",
        question_dir=question_dir,
        title="Q2 ODE model comparison",
        source_script="questions/q2/scripts/visualize.py",
        notes="Vacuum, drag, constant-lift, and spin-factor-lift ODE models on the fixed test split.",
        dpi=dpi,
    )
    plt.close(fig)

    surface = pd.read_csv(tables / "q2_ode_parameter_surface.csv")
    plot_surface = surface[surface["model"] == "constant_lift"].copy()
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    if not plot_surface.empty and "cl" in plot_surface.columns:
        pivot = plot_surface.pivot_table(index="cl", columns="cd", values="objective", aggfunc="mean")
        image = ax.imshow(
            pivot.to_numpy(dtype=float),
            origin="lower",
            aspect="auto",
            extent=[pivot.columns.min(), pivot.columns.max(), pivot.index.min(), pivot.index.max()],
            cmap="viridis",
        )
        fig.colorbar(image, ax=ax, label="Training objective")
        ax.set_ylabel("C_L")
    else:
        ax.plot(surface["cd"], surface["objective"], marker="o")
        ax.set_ylabel("Training objective")
    ax.set_xlabel("C_D")
    ax.set_title("ODE parameter surface")
    outputs["q2_ode_parameter_surface"] = save_figure_bundle(
        fig=fig,
        data=surface,
        stem="q2_ode_parameter_surface",
        question_dir=question_dir,
        title="Q2 ODE parameter surface",
        source_script="questions/q2/scripts/visualize.py",
        notes="Train-only representative grid scans for drag, constant lift, and spin-factor lift.",
        dpi=dpi,
    )
    plt.close(fig)

    trajectories_path = tables / "q2_typical_trajectories.csv"
    if trajectories_path.exists():
        trajectories = pd.read_csv(trajectories_path)
        fig = plt.figure(figsize=(6.0, 4.8))
        ax = fig.add_subplot(111, projection="3d")
        for label, data in trajectories.groupby("target_group"):
            ax.plot(data["x_yd"], data["y_yd"], data["z_yd"], label=str(label))
        ax.set_xlabel("x (yd)")
        ax.set_ylabel("y (yd)")
        ax.set_zlabel("z (yd)")
        ax.set_title("Typical trajectories")
        ax.legend()
        outputs["q2_typical_trajectories_3d"] = save_figure_bundle(
            fig=fig,
            data=trajectories,
            stem="q2_typical_trajectories_3d",
            question_dir=question_dir,
            title="Q2 typical trajectories 3D",
            source_script="questions/q2/scripts/visualize.py",
            notes="Spin-factor-lift trajectories for fixed-test 100/150/200 yd typical records.",
            dpi=dpi,
        )
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(5.8, 4.0))
        for label, data in trajectories.groupby("target_group"):
            ax.plot(data["x_yd"], data["z_yd"], label=str(label))
        ax.set_xlabel("x (yd)")
        ax.set_ylabel("z (yd)")
        ax.set_title("Typical trajectories side view")
        ax.legend()
        outputs["q2_typical_trajectories_side"] = save_figure_bundle(
            fig=fig,
            data=trajectories,
            stem="q2_typical_trajectories_side",
            question_dir=question_dir,
            title="Q2 typical trajectories side view",
            source_script="questions/q2/scripts/visualize.py",
            notes="x-z side view for fixed-test 100/150/200 yd typical records.",
            dpi=dpi,
        )
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(5.8, 4.0))
        for label, data in trajectories.groupby("target_group"):
            ax.plot(data["x_yd"], data["y_yd"], label=str(label))
        ax.set_xlabel("x (yd)")
        ax.set_ylabel("y (yd)")
        ax.set_title("Typical trajectories top view")
        ax.legend()
        outputs["q2_typical_trajectories_top"] = save_figure_bundle(
            fig=fig,
            data=trajectories,
            stem="q2_typical_trajectories_top",
            question_dir=question_dir,
            title="Q2 typical trajectories top view",
            source_script="questions/q2/scripts/visualize.py",
            notes="x-y top view for fixed-test 100/150/200 yd typical records.",
            dpi=dpi,
        )
        plt.close(fig)

    sensitivity_path = tables / "q2_ode_sensitivity.csv"
    if sensitivity_path.exists():
        sensitivity = pd.read_csv(sensitivity_path)
        data = sensitivity[sensitivity["metric"] == "carry_yd"].copy()
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        labels = data["sensitivity_type"] + ":" + data["parameter"].astype(str)
        ax.bar(range(len(data)), data["delta"])
        ax.set_xticks(range(len(data)), labels, rotation=75, ha="right")
        ax.set_ylabel("Delta carry (yd)")
        ax.set_title("ODE sensitivity")
        outputs["q2_ode_sensitivity"] = save_figure_bundle(
            fig=fig,
            data=sensitivity,
            stem="q2_ode_sensitivity",
            question_dir=question_dir,
            title="Q2 ODE sensitivity",
            source_script="questions/q2/scripts/visualize.py",
            notes="Parameter, numerical integration, wind, and spin-decay perturbations on typical records.",
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
