#!/usr/bin/env python3
"""Paper-level visualization for q3."""

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


def _plot_hole(ax) -> None:
    ax.scatter([200.0], [0.0], marker="*", s=130, color="#b42318", label="hole")


def create_visualizations(*, root: Path, dpi: int = 300) -> dict[str, dict[str, Path]]:
    question_dir = root / "questions" / "q3"
    tables = question_dir / "artifacts" / "tables"
    outputs: dict[str, dict[str, Path]] = {}

    trajectory = pd.read_csv(tables / "q3_optimal_trajectory.csv")
    fig = plt.figure(figsize=(6.4, 5.0))
    ax = fig.add_subplot(111, projection="3d")
    for model, subset in trajectory.groupby("model"):
        ax.plot(subset["x_yd"], subset["y_yd"], subset["z_yd"], label=model)
        land = subset.iloc[-1]
        ax.scatter([land["x_yd"]], [land["y_yd"]], [land["z_yd"]], s=35)
        ax.plot([land["x_yd"], 200.0], [land["y_yd"], 0.0], [0.0, 0.0], linestyle="--", linewidth=1.0)
    ax.scatter([0.0], [0.0], [0.0], marker="o", s=45, color="#111111", label="start")
    ax.scatter([200.0], [0.0], [0.0], marker="*", s=110, color="#b42318", label="hole")
    ax.set_xlabel("x (yd)")
    ax.set_ylabel("y (yd)")
    ax.set_zlabel("z (yd)")
    ax.set_title("Q3 robust optimum ODE trajectory")
    ax.legend()
    outputs["q3_optimal_trajectory_3d"] = save_figure_bundle(
        fig=fig,
        data=trajectory,
        stem="q3_optimal_trajectory_3d",
        question_dir=question_dir,
        title="Q3 robust optimum trajectory 3D",
        source_script="questions/q3/scripts/visualize.py",
        notes="Trajectory includes start, landing point, hole, and landing-to-hole error line.",
        dpi=dpi,
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for model, subset in trajectory.groupby("model"):
        ax.plot(subset["x_yd"], subset["z_yd"], label=model)
        apex = subset.loc[subset["z_yd"].idxmax()]
        land = subset.iloc[-1]
        ax.scatter([apex["x_yd"]], [apex["z_yd"]], s=30)
        ax.scatter([land["x_yd"]], [land["z_yd"]], s=30)
    ax.axvline(200.0, color="#b42318", linestyle="--", linewidth=1.0, label="hole x")
    ax.set_xlabel("x (yd)")
    ax.set_ylabel("z (yd)")
    ax.set_title("Q3 robust trajectory side view")
    ax.legend()
    outputs["q3_optimal_trajectory_side"] = save_figure_bundle(
        fig=fig,
        data=trajectory,
        stem="q3_optimal_trajectory_side",
        question_dir=question_dir,
        title="Q3 robust optimum trajectory side view",
        source_script="questions/q3/scripts/visualize.py",
        notes="Side view marks apex, landing point, and hole x-position.",
        dpi=dpi,
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for model, subset in trajectory.groupby("model"):
        ax.plot(subset["x_yd"], subset["y_yd"], label=model)
        land = subset.iloc[-1]
        ax.scatter([land["x_yd"]], [land["y_yd"]], s=35)
        ax.plot([land["x_yd"], 200.0], [land["y_yd"], 0.0], linestyle="--", linewidth=1.0)
    _plot_hole(ax)
    ax.scatter([0.0], [0.0], marker="o", s=35, color="#111111", label="start")
    ax.set_xlabel("x (yd)")
    ax.set_ylabel("y (yd)")
    ax.set_title("Q3 robust trajectory top view")
    ax.legend()
    outputs["q3_optimal_trajectory_top"] = save_figure_bundle(
        fig=fig,
        data=trajectory,
        stem="q3_optimal_trajectory_top",
        question_dir=question_dir,
        title="Q3 robust optimum trajectory top view",
        source_script="questions/q3/scripts/visualize.py",
        notes="Top view marks start, landing point, hole, and landing-to-hole error line.",
        dpi=dpi,
    )
    plt.close(fig)

    for stem, x_col, y_col, title in [
        ("q3_objective_slice_speed_angle", "ball_speed_mph", "launch_angle_deg", "Speed-angle objective slice"),
        ("q3_objective_slice_spin", "spin_rate_rpm", "spin_axis_deg", "Spin objective slice"),
    ]:
        data = pd.read_csv(tables / f"{stem}.csv")
        grid = data[data["row_type"] == "grid"].copy()
        fig, ax = plt.subplots(figsize=(6.0, 4.6))
        pivot = grid.pivot_table(index=y_col, columns=x_col, values="objective_yd", aggfunc="mean")
        contour = ax.contourf(pivot.columns, pivot.index, pivot.to_numpy(), levels=18, cmap="viridis")
        fig.colorbar(contour, ax=ax, label="Objective (yd)")
        train = data[data["row_type"] == "train"]
        ax.scatter(train[x_col], train[y_col], s=8, alpha=0.22, color="#ffffff", edgecolor="none", label="train")
        nominal = data[data["row_type"] == "nominal_optimum"]
        robust = data[data["row_type"] == "joint_robust_recommended_optimum"]
        if robust.empty:
            robust = data[data["row_type"] == "robust_recommended_optimum"]
        ax.scatter(nominal[x_col], nominal[y_col], marker="x", s=80, color="#b42318", label="nominal")
        ax.scatter(robust[x_col], robust[y_col], marker="o", s=65, facecolors="none", edgecolors="#111111", label="robust")
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(title)
        ax.legend(loc="best")
        outputs[stem] = save_figure_bundle(
            fig=fig,
            data=data,
            stem=stem,
            question_dir=question_dir,
            title=f"Q3 {title}",
            source_script="questions/q3/scripts/visualize.py",
            notes="Contour grid uses the selected q3 surrogate objective and overlays train samples plus nominal/robust optima.",
            dpi=dpi,
        )
        plt.close(fig)

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q3 visualization")
    parser.add_argument("--config", default="configs/default.yaml")
    return parser.parse_args()


def main() -> int:
    _ = parse_args()
    root = project_root()
    create_visualizations(root=root)
    print("[ok] q3 figures regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
