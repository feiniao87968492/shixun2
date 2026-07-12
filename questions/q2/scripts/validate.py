#!/usr/bin/env python3
"""Validation and sensitivity analysis for q2."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402


def validate_outputs(root: Path, *, require_validation_table: bool = True) -> pd.DataFrame:
    question_dir = root / "questions" / "q2"
    tables = question_dir / "artifacts" / "tables"
    figures = question_dir / "artifacts" / "figures"
    figure_data = question_dir / "artifacts" / "figure_data"
    models = question_dir / "artifacts" / "models"
    rows = []

    def add(check: str, kind: str, path: Path | None, passed: bool, details: str = "") -> None:
        rows.append(
            {
                "check": check,
                "kind": kind,
                "path": str(path.relative_to(root)) if path is not None else "",
                "passed": bool(passed),
                "details": details,
            }
        )

    required_tables = [
        "q2_data_split.csv",
        "q2_spin_geometry_check.csv",
        "q2_supervised_cv_results.csv",
        "q2_supervised_metrics.csv",
        "q2_supervised_predictions.csv",
        "q2_supervised_bootstrap_ci.csv",
        "q2_supervised_error_groups.csv",
        "q2_supervised_repeated_split.csv",
        "q2_ode_representative_records.csv",
        "q2_ode_parameters.csv",
        "q2_ode_parameter_surface.csv",
        "q2_ode_model_comparison.csv",
        "q2_ode_test_predictions.csv",
        "q2_ode_test_metrics.csv",
        "q2_ode_failures.csv",
        "q2_ode_validation_checks.csv",
        "q2_typical_records.csv",
        "q2_ode_typical_errors.csv",
        "q2_typical_trajectories.csv",
        "q2_ode_sensitivity.csv",
    ]
    if require_validation_table:
        required_tables.append("q2_validation_checks.csv")
    for filename in required_tables:
        path = tables / filename
        add(filename, "table", path, path.exists() and path.stat().st_size > 0)

    required_figures = [
        "q2_prediction_scatter_carry",
        "q2_prediction_scatter_apex",
        "q2_residuals_carry",
        "q2_residuals_apex",
        "q2_ode_model_comparison",
        "q2_ode_parameter_surface",
        "q2_typical_trajectories_3d",
        "q2_typical_trajectories_side",
        "q2_typical_trajectories_top",
        "q2_ode_sensitivity",
    ]
    for stem in required_figures:
        for suffix, kind, base in [
            (".png", "figure", figures),
            (".csv", "figure_data", figure_data),
            (".meta.json", "figure_metadata", figure_data),
        ]:
            path = base / f"{stem}{suffix}"
            add(f"{stem}{suffix}", kind, path, path.exists() and path.stat().st_size > 0)

    for filename in ["q2_carry_model.joblib", "q2_apex_model.joblib"]:
        path = models / filename
        add(filename, "model", path, path.exists() and path.stat().st_size > 0)
    ode_parameters_json = models / "q2_ode_parameters.json"
    add(
        "q2_ode_parameters.json",
        "model_metadata",
        ode_parameters_json,
        ode_parameters_json.exists() and ode_parameters_json.stat().st_size > 0,
    )

    split_path = tables / "q2_data_split.csv"
    if split_path.exists():
        split = pd.read_csv(split_path)
        train_n = int((split["split"] == "train").sum())
        test_n = int((split["split"] == "test").sum())
        add("split_row_count", "schema", split_path, len(split) == 735)
        add("split_train_test_counts", "numeric", split_path, train_n == 514 and test_n == 221)
        add("split_record_id_unique", "schema", split_path, split["record_id"].is_unique)

    metrics_path = tables / "q2_supervised_metrics.csv"
    if metrics_path.exists():
        metrics = pd.read_csv(metrics_path)
        add("supervised_dummy_present", "schema", metrics_path, "dummy" in set(metrics["model"]))
        add(
            "supervised_one_selected_per_target",
            "schema",
            metrics_path,
            metrics.groupby("target")["selected"].sum().eq(1).all(),
        )
        add(
            "supervised_metrics_finite",
            "numeric",
            metrics_path,
            metrics[["rmse", "mape", "mae", "r2", "mdape"]].notna().all().all(),
        )

    predictions_path = tables / "q2_supervised_predictions.csv"
    if predictions_path.exists():
        predictions = pd.read_csv(predictions_path)
        add("supervised_prediction_row_count", "schema", predictions_path, len(predictions) == 4420)

    ode_checks_path = tables / "q2_ode_validation_checks.csv"
    if ode_checks_path.exists():
        ode_checks = pd.read_csv(ode_checks_path)
        add("ode_validation_checks_pass", "numeric", ode_checks_path, ode_checks["passed"].astype(bool).all())
        add(
            "ode_lift_invariant_checks_present",
            "schema",
            ode_checks_path,
            {
                "positive_backspin_lifts_up",
                "zero_sidespin_zero_direction_lateral_near_zero",
                "full_ode_variants_present",
            }.issubset(set(ode_checks["check"])),
        )

    ode_metrics_path = tables / "q2_ode_test_metrics.csv"
    if ode_metrics_path.exists():
        ode_metrics = pd.read_csv(ode_metrics_path)
        add(
            "ode_full_variants_present",
            "schema",
            ode_metrics_path,
            {"vacuum", "drag", "constant_lift", "spin_factor_lift"}.issubset(set(ode_metrics["model"])),
        )
        add(
            "ode_failure_rate_recorded",
            "numeric",
            ode_metrics_path,
            "flight_failure_rate" in ode_metrics.columns and ode_metrics["flight_failure_rate"].notna().all(),
        )

    parameters_path = tables / "q2_ode_parameters.csv"
    if parameters_path.exists():
        parameters = pd.read_csv(parameters_path)
        add(
            "ode_parameter_rows_present",
            "schema",
            parameters_path,
            {"C_D", "C_L", "k_L"}.issubset(set(parameters["parameter"])),
        )

    typical_path = tables / "q2_typical_records.csv"
    if typical_path.exists():
        typical = pd.read_csv(typical_path)
        add("typical_targets_present", "schema", typical_path, set(typical["target_distance_yd"]) == {100, 150, 200})
        add("typical_sample_ids_unique", "schema", typical_path, typical["sample_id"].is_unique)

    trajectories_path = tables / "q2_typical_trajectories.csv"
    if trajectories_path.exists():
        trajectories = pd.read_csv(trajectories_path)
        add(
            "typical_trajectory_coordinates_finite",
            "numeric",
            trajectories_path,
            trajectories[["x_m", "y_m", "z_m", "x_yd", "y_yd", "z_yd"]].notna().all().all(),
        )

    sensitivity_path = tables / "q2_ode_sensitivity.csv"
    if sensitivity_path.exists():
        sensitivity = pd.read_csv(sensitivity_path)
        add(
            "ode_sensitivity_scope_present",
            "schema",
            sensitivity_path,
            {"parameter", "integration", "assumption"}.issubset(set(sensitivity["sensitivity_type"])),
        )

    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q2 validation")
    parser.add_argument("--config", default="configs/default.yaml")
    return parser.parse_args()


def main() -> int:
    _ = parse_args()
    root = project_root()
    checks = validate_outputs(root, require_validation_table=False)
    save_table(checks, stem="q2_validation_checks", question_dir=root / "questions" / "q2")
    failed = checks[~checks["passed"]]
    if not failed.empty:
        print(f"[error] q2 validation failed: {failed['check'].tolist()}")
        return 1
    print(f"[ok] q2 validation passed: {len(checks)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
