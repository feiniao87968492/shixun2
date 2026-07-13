#!/usr/bin/env python3
"""Validation and sensitivity analysis for q2."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(math.sqrt(np.mean((predicted - actual) ** 2))) if len(actual) else np.nan


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = np.abs(actual) > 1e-12
    return float(np.mean(np.abs((predicted[mask] - actual[mask]) / actual[mask])) * 100.0) if mask.any() else np.nan


def _r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return np.nan
    total = float(np.sum((actual - np.mean(actual)) ** 2))
    if total <= 1e-12:
        return np.nan
    return float(1.0 - np.sum((actual - predicted) ** 2) / total)


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def metadata_paths_are_posix(value: object) -> bool:
    if isinstance(value, dict):
        return all(metadata_paths_are_posix(child) for child in value.values())
    if isinstance(value, list):
        return all(metadata_paths_are_posix(child) for child in value)
    if isinstance(value, str) and value.startswith(("questions", "configs", "data")):
        return "\\" not in value
    return True


def validate_outputs(
    root: Path,
    *,
    config_path: str | Path = "configs/default.yaml",
    require_validation_table: bool = True,
) -> pd.DataFrame:
    question_dir = root / "questions" / "q2"
    tables = question_dir / "artifacts" / "tables"
    figures = question_dir / "artifacts" / "figures"
    figure_data = question_dir / "artifacts" / "figure_data"
    models = question_dir / "artifacts" / "models"
    config = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))["q2"]
    rows = []

    def add(check: str, kind: str, path: Path | None, passed: bool, details: str = "") -> None:
        rows.append(
            {
                "check": check,
                "kind": kind,
                "path": rel_posix(path, root) if path is not None else "",
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
        "q2_drag_calibration_records.csv",
        "q2_lift_calibration_records.csv",
        "q2_ode_representative_records.csv",
        "q2_drag_optimization_runs.csv",
        "q2_constant_lift_optimization_runs.csv",
        "q2_spin_factor_optimization_runs.csv",
        "q2_drag_calibration_failures.csv",
        "q2_constant_lift_calibration_failures.csv",
        "q2_spin_factor_calibration_failures.csv",
        "q2_ode_parameters.csv",
        "q2_ode_parameter_surface.csv",
        "q2_ode_model_comparison.csv",
        "q2_ode_test_predictions.csv",
        "q2_ode_test_metrics.csv",
        "q2_carry_definition_comparison.csv",
        "q2_ode_failures.csv",
        "q2_ode_validation_checks.csv",
        "q2_typical_records.csv",
        "q2_ode_typical_errors.csv",
        "q2_typical_trajectories_constant_lift.csv",
        "q2_typical_trajectories_spin_factor.csv",
        "q2_typical_trajectories.csv",
        "q2_ode_sensitivity.csv",
    ]
    if require_validation_table:
        required_tables.append("q2_validation_checks.csv")
    for filename in required_tables:
        path = tables / filename
        add(filename, "table", path, path.exists() and path.stat().st_size > 0)

    add(
        "task4_configured_carry_definition_is_forward_x",
        "config",
        root / config_path,
        config.get("ode", {}).get("carry_definition") == "forward_x",
    )

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
        "q2_typical_trajectories_constant_lift_3d",
        "q2_typical_trajectories_constant_lift_side",
        "q2_typical_trajectories_constant_lift_top",
        "q2_typical_trajectories_spin_factor_3d",
        "q2_typical_trajectories_spin_factor_side",
        "q2_typical_trajectories_spin_factor_top",
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

    drag_records_path = tables / "q2_drag_calibration_records.csv"
    lift_records_path = tables / "q2_lift_calibration_records.csv"
    if drag_records_path.exists() and lift_records_path.exists():
        drag_records = pd.read_csv(drag_records_path)
        lift_records = pd.read_csv(lift_records_path)
        add(
            "task3_drag_representative_count_matches_config",
            "numeric",
            drag_records_path,
            len(drag_records) == int(config["ode"]["drag_calibration"]["representative_count"]),
        )
        add(
            "task3_lift_representative_count_matches_config",
            "numeric",
            lift_records_path,
            len(lift_records) == int(config["ode"]["lift_calibration"]["representative_count"]),
        )
        required_calibration_columns = {
            "record_id",
            "calibration_type",
            "cluster_or_stratum",
            "ball_speed_mph",
            "launch_angle_deg",
            "spin_rate_rpm",
            "spin_axis_deg",
            "carry_distance_yd",
            "apex_height_yd",
        }
        add(
            "task3_calibration_record_schema",
            "schema",
            drag_records_path,
            required_calibration_columns.issubset(drag_records.columns)
            and required_calibration_columns.issubset(lift_records.columns),
        )
        if split_path.exists():
            split = pd.read_csv(split_path)
            test_ids = set(split.loc[split["split"] == "test", "record_id"].astype(int))
            calibration_ids = set(drag_records["record_id"].astype(int)) | set(lift_records["record_id"].astype(int))
            add(
                "task3_calibration_excludes_test_split",
                "leakage",
                drag_records_path,
                not bool(calibration_ids & test_ids),
            )

    surface_path = tables / "q2_ode_parameter_surface.csv"
    if surface_path.exists():
        surface = pd.read_csv(surface_path)
        drag_grid = int(config["ode"]["drag_calibration"]["grid_size"])
        lift_grid = int(config["ode"]["lift_calibration"]["grid_size"])
        add(
            "task3_drag_grid_size_matches_config",
            "numeric",
            surface_path,
            len(surface[surface["model"] == "drag"]) == drag_grid,
        )
        add(
            "task3_lift_grid_size_matches_config",
            "numeric",
            surface_path,
            len(surface[surface["model"] == "constant_lift"]) == lift_grid * lift_grid
            and len(surface[surface["model"] == "spin_factor_lift"]) == lift_grid * lift_grid,
        )

    optimization_files = {
        "task3_drag_optimization_success": tables / "q2_drag_optimization_runs.csv",
        "task3_constant_lift_optimization_success": tables / "q2_constant_lift_optimization_runs.csv",
        "task3_spin_factor_optimization_success": tables / "q2_spin_factor_optimization_runs.csv",
    }
    for check_name, path in optimization_files.items():
        if path.exists():
            runs = pd.read_csv(path)
            add(check_name, "numeric", path, "success" in runs.columns and runs["success"].astype(bool).any())
            add(
                f"{check_name}_full_train_objective_recorded",
                "schema",
                path,
                {"selected", "full_train_objective"}.issubset(runs.columns)
                and len(runs[runs["selected"].astype(bool)]) == 1
                and runs.loc[runs["selected"].astype(bool), "full_train_objective"].notna().all(),
            )
            required_task4_columns = {
                "optimizer_success",
                "objective_finite",
                "accepted",
                "initial_objective",
                "final_objective",
                "objective_improvement",
                "termination_message",
                "iterations",
                "function_evaluations",
                "calibration_failed_count",
                "full_train_failed_count",
                "selected",
            }
            task4_schema_ok = required_task4_columns.issubset(runs.columns)
            selected_runs = runs[runs["selected"].astype(bool)] if "selected" in runs.columns else pd.DataFrame()
            add("task4_optimizer_terminated_successfully", "numeric", path, task4_schema_ok and runs["optimizer_success"].astype(bool).any())
            add(
                "task4_optimizer_message_not_max_evaluations",
                "schema",
                path,
                task4_schema_ok
                and not (
                    runs["termination_message"].fillna("").str.contains(
                        "Maximum number of function evaluations", case=False
                    )
                    & (
                        runs["optimizer_success"].astype(bool)
                        | runs["accepted"].astype(bool)
                        | runs["selected"].astype(bool)
                    )
                ).any(),
            )
            add(
                "task4_optimizer_iterations_positive",
                "numeric",
                path,
                task4_schema_ok and runs["iterations"].astype(int).max() > 0,
            )
            add(
                "task4_optimizer_function_evaluations_above_minimum",
                "numeric",
                path,
                task4_schema_ok and runs["function_evaluations"].astype(int).max() > 4,
            )
            add(
                "task4_selected_run_accepted",
                "numeric",
                path,
                task4_schema_ok and len(selected_runs) == 1 and selected_runs["accepted"].astype(bool).all(),
            )
            add(
                "task4_selected_run_objective_finite",
                "numeric",
                path,
                task4_schema_ok and len(selected_runs) == 1 and selected_runs["objective_finite"].astype(bool).all(),
            )
            add(
                "task4_selected_run_zero_calibration_failures",
                "numeric",
                path,
                task4_schema_ok and len(selected_runs) == 1 and selected_runs["calibration_failed_count"].astype(int).eq(0).all(),
            )
            add(
                "task4_selected_run_zero_full_train_failures",
                "numeric",
                path,
                task4_schema_ok and len(selected_runs) == 1 and selected_runs["full_train_failed_count"].astype(int).eq(0).all(),
            )
            add(
                "task4_selected_run_objective_not_worse_than_initial",
                "numeric",
                path,
                task4_schema_ok
                and len(selected_runs) == 1
                and (
                    selected_runs["final_objective"].astype(float)
                    <= selected_runs["initial_objective"].astype(float) + 1e-6
                ).all(),
            )

    selected_failure_checks = {
        "task4_selected_drag_zero_full_train_failures": tables / "q2_drag_optimization_runs.csv",
        "task4_selected_constant_lift_zero_full_train_failures": tables / "q2_constant_lift_optimization_runs.csv",
        "task4_selected_spin_factor_zero_full_train_failures": tables / "q2_spin_factor_optimization_runs.csv",
    }
    for check_name, path in selected_failure_checks.items():
        if path.exists():
            runs = pd.read_csv(path)
            selected_runs = runs[runs["selected"].astype(bool)] if "selected" in runs.columns else pd.DataFrame()
            add(
                check_name,
                "numeric",
                path,
                len(selected_runs) == 1
                and "full_train_failed_count" in selected_runs.columns
                and selected_runs["full_train_failed_count"].astype(int).eq(0).all(),
            )

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
        q3_checks = {
            "q3_spin_factor_boundary_stability",
            "q3_spin_factor_boundary_max_flight_time_within_limit",
            "q3_spin_factor_boundary_max_apex_within_limit",
            "q3_spin_factor_boundary_max_lateral_within_limit",
        }
        add(
            "task4_q3_boundary_stability_passed",
            "numeric",
            ode_checks_path,
            q3_checks.issubset(set(ode_checks["check"]))
            and ode_checks[ode_checks["check"].isin(q3_checks)]["passed"].astype(bool).all(),
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

    ode_failures_path = tables / "q2_ode_failures.csv"
    if ode_failures_path.exists():
        ode_failures = pd.read_csv(ode_failures_path)
        add(
            "task4_all_models_zero_test_failures",
            "numeric",
            ode_failures_path,
            "failed_count" in ode_failures.columns and ode_failures["failed_count"].astype(int).eq(0).all(),
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
        boundary_columns = {
            "at_lower_bound",
            "at_upper_bound",
            "distance_to_lower_bound",
            "distance_to_upper_bound",
            "boundary_warning",
            "parameter_status",
            "full_train_objective",
        }
        add("task3_parameter_boundary_columns_present", "schema", parameters_path, boundary_columns.issubset(parameters.columns))
        calibrated = parameters[parameters["model"].isin(["drag", "constant_lift", "spin_factor_lift"])]
        if boundary_columns.issubset(parameters.columns):
            numeric_bounds = calibrated.copy()
            add(
                "task3_parameters_within_bounds",
                "numeric",
                parameters_path,
                (
                    numeric_bounds["distance_to_lower_bound"].astype(float).ge(-1e-8).all()
                    and numeric_bounds["distance_to_upper_bound"].astype(float).ge(-1e-8).all()
                ),
            )
            near_boundary = numeric_bounds[
                numeric_bounds["at_lower_bound"].astype(bool) | numeric_bounds["at_upper_bound"].astype(bool)
            ]
            add(
                "task3_boundary_solution_has_warning",
                "schema",
                parameters_path,
                near_boundary.empty or near_boundary["boundary_warning"].fillna("").astype(str).str.len().gt(0).all(),
            )
            drag_cd = calibrated[(calibrated["model"] == "drag") & (calibrated["parameter"] == "C_D")]
            add(
                "task3_drag_boundary_status_recorded",
                "schema",
                parameters_path,
                not drag_cd.empty and set(drag_cd["parameter_status"]).issubset({"ok", "boundary_solution"}),
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

    role_trajectories = {
        "task3_best_fit_trajectory_model": (
            tables / "q2_typical_trajectories_constant_lift.csv",
            "constant_lift",
        ),
        "task3_q3_compatible_trajectory_model": (
            tables / "q2_typical_trajectories_spin_factor.csv",
            "spin_factor_lift",
        ),
    }
    for check_name, (path, model_name) in role_trajectories.items():
        if path.exists():
            trajectories = pd.read_csv(path)
            add(check_name, "schema", path, set(trajectories["model"]) == {model_name})

    sensitivity_path = tables / "q2_ode_sensitivity.csv"
    if sensitivity_path.exists():
        sensitivity = pd.read_csv(sensitivity_path)
        add(
            "ode_sensitivity_scope_present",
            "schema",
            sensitivity_path,
            {"parameter", "wind", "spin_decay", "solver_tolerance", "initial_height"}.issubset(
                set(sensitivity["sensitivity_type"])
            ),
        )
        add(
            "task3_sensitivity_models_present",
            "schema",
            sensitivity_path,
            {"constant_lift", "spin_factor_lift"}.issubset(set(sensitivity["model"])),
        )
        wind_rows = sensitivity[sensitivity["sensitivity_type"] == "wind"]
        add(
            "task3_wind_vectors_recorded",
            "schema",
            sensitivity_path,
            {"no_wind", "tailwind_1mps", "headwind_1mps"}.issubset(set(wind_rows["parameter"]))
            and float(wind_rows.loc[wind_rows["parameter"] == "tailwind_1mps", "wind_x_mps"].iloc[0]) > 0
            and float(wind_rows.loc[wind_rows["parameter"] == "headwind_1mps", "wind_x_mps"].iloc[0]) < 0,
        )
        carry_wind = wind_rows[wind_rows["metric"] == "carry_yd"].pivot_table(
            index="model", columns="parameter", values="scenario_value", aggfunc="mean"
        )
        wind_tolerance = 1.0e-2
        wind_order_ok = (
            not carry_wind.empty
            and {"tailwind_1mps", "no_wind", "headwind_1mps"}.issubset(carry_wind.columns)
            and (
                (carry_wind["tailwind_1mps"] + wind_tolerance >= carry_wind["no_wind"])
                & (carry_wind["no_wind"] + wind_tolerance >= carry_wind["headwind_1mps"])
            ).all()
        )
        add("task3_wind_direction_average_order", "numeric", sensitivity_path, bool(wind_order_ok))
        carry_rows = sensitivity[sensitivity["metric"] == "carry_yd"]
        add(
            "task4_sensitivity_uses_forward_x",
            "schema",
            sensitivity_path,
            "carry_definition" in carry_rows.columns
            and not carry_rows.empty
            and set(carry_rows["carry_definition"]) == {"forward_x"},
        )

    carry_definition_path = tables / "q2_carry_definition_comparison.csv"
    if carry_definition_path.exists():
        carry_definition = pd.read_csv(carry_definition_path)
        add(
            "task3_carry_definition_comparison_present",
            "schema",
            carry_definition_path,
            {"D_x", "D_r"}.issubset(set(carry_definition["carry_definition"]))
            and {"vacuum", "drag", "constant_lift", "spin_factor_lift"}.issubset(set(carry_definition["model"])),
        )
        add(
            "task4_carry_definition_primary_is_forward_x",
            "schema",
            carry_definition_path,
            {"actual_definition", "predicted_definition", "is_primary_definition"}.issubset(carry_definition.columns)
            and set(carry_definition[carry_definition["is_primary_definition"].astype(bool)]["carry_definition"]) == {"D_x"},
        )

    predictions_path = tables / "q2_ode_test_predictions.csv"
    metrics_path = tables / "q2_ode_test_metrics.csv"
    if predictions_path.exists() and metrics_path.exists():
        predictions = pd.read_csv(predictions_path)
        metrics = pd.read_csv(metrics_path).set_index("model")
        recompute_ok = True
        forward_recompute_ok = True
        for model, subset in predictions.groupby("model"):
            ok = subset[subset["integration_status"] == "success"]
            actual = ok["actual_carry_yd"].to_numpy(dtype=float)
            predicted = ok["predicted_carry_yd"].to_numpy(dtype=float)
            forward_predicted = ok["predicted_x_carry_yd"].to_numpy(dtype=float)
            checks = {
                "carry_rmse": _rmse(actual, predicted),
                "carry_mae": float(np.mean(np.abs(predicted - actual))) if len(actual) else np.nan,
                "carry_mape": _mape(actual, predicted),
                "carry_r2": _r2(actual, predicted),
            }
            for column, value in checks.items():
                if column not in metrics.columns or not np.isclose(float(metrics.loc[model, column]), value, rtol=1e-9, atol=1e-9):
                    recompute_ok = False
                    break
            forward_checks = {
                "carry_rmse": _rmse(actual, forward_predicted),
                "carry_mae": float(np.mean(np.abs(forward_predicted - actual))) if len(actual) else np.nan,
                "carry_mape": _mape(actual, forward_predicted),
                "carry_r2": _r2(actual, forward_predicted),
            }
            for column, value in forward_checks.items():
                if column not in metrics.columns or not np.isclose(float(metrics.loc[model, column]), value, rtol=1e-9, atol=1e-9):
                    forward_recompute_ok = False
                    break
        add("task3_metrics_recomputed_from_predictions", "numeric", predictions_path, recompute_ok)
        add(
            "task4_ode_metrics_match_forward_x_predictions",
            "numeric",
            predictions_path,
            "carry_definition" in predictions.columns
            and set(predictions["carry_definition"]) == {"forward_x"}
            and np.allclose(predictions["predicted_carry_yd"], predictions["predicted_x_carry_yd"])
            and forward_recompute_ok,
        )

    typical_errors_path = tables / "q2_ode_typical_errors.csv"
    if typical_errors_path.exists():
        typical_errors = pd.read_csv(typical_errors_path)
        add(
            "task4_typical_errors_match_forward_x_predictions",
            "numeric",
            typical_errors_path,
            {"carry_definition", "predicted_x_carry_yd", "predicted_carry_yd", "carry_absolute_error_yd"}.issubset(
                typical_errors.columns
            )
            and set(typical_errors["carry_definition"]) == {"forward_x"}
            and np.allclose(typical_errors["predicted_carry_yd"], typical_errors["predicted_x_carry_yd"])
            and np.allclose(
                typical_errors["carry_absolute_error_yd"],
                (typical_errors["predicted_x_carry_yd"] - typical_errors["actual_carry_yd"]).abs(),
            ),
        )

    if surface_path.exists():
        surface = pd.read_csv(surface_path)
        add(
            "task4_calibration_objective_uses_forward_x",
            "schema",
            surface_path,
            "carry_definition" in surface.columns and set(surface["carry_definition"]) == {"forward_x"},
        )

    metadata_path = question_dir / "artifacts" / "run_metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        add(
            "task3_model_roles_recorded",
            "schema",
            metadata_path,
            metadata.get("best_fit_ode_model") in {"drag", "constant_lift", "spin_factor_lift"}
            and metadata.get("q3_compatible_ode_model") == "spin_factor_lift"
            and "trajectory_model" not in metadata,
        )
        add(
            "task3_reproducibility_metadata_present",
            "schema",
            metadata_path,
            {
                "git_commit",
                "data_sha256",
                "config_sha256",
                "train_ids_sha256",
                "test_ids_sha256",
                "drag_calibration_record_ids",
                "lift_calibration_record_ids",
                "optimization_runs",
            }.issubset(metadata),
        )
        add("task4_metadata_paths_posix", "schema", metadata_path, metadata_paths_are_posix(metadata))
        add(
            "task4_best_fit_model_selected_from_full_train_objective",
            "schema",
            metadata_path,
            metadata.get("carry_definition") == "forward_x"
            and metadata.get("best_fit_selection_rule") == "minimum_full_train_objective_among_accepted_models"
            and {"drag", "constant_lift", "spin_factor_lift"}.issubset(
                set((metadata.get("full_train_objectives") or {}).keys())
            ),
        )

    q2_manifest_path = question_dir / "manifest.yaml"
    q2_readme_path = question_dir / "README.md"
    root_readme_path = root / "README.md"
    if q2_manifest_path.exists() and q2_readme_path.exists() and root_readme_path.exists():
        manifest = yaml.safe_load(q2_manifest_path.read_text(encoding="utf-8"))
        q2_readme = q2_readme_path.read_text(encoding="utf-8")
        root_readme = root_readme_path.read_text(encoding="utf-8")
        manifest_status = str(manifest.get("status"))
        q2_status_done = "状态：`done`" in q2_readme or "鐘舵€侊細`done`" in q2_readme
        q2_status_conditional = (
            "状态：`conditionally_passed`" in q2_readme
            or "鐘舵€侊細`conditionally_passed`" in q2_readme
        )
        root_status_done = "| q2 | done |" in root_readme and "`q2_done`" in root_readme
        root_status_conditional = (
            "| q2 | conditionally_passed |" in root_readme
            and "`q2_conditionally_passed`" in root_readme
        )
        status_synced = (
            (manifest_status == "done" and q2_status_done and root_status_done)
            or (manifest_status == "conditionally_passed" and q2_status_conditional and root_status_conditional)
        )
        add(
            "task4_status_files_synced",
            "schema",
            q2_manifest_path,
            status_synced and "q2_first_stage_done" not in root_readme,
        )
        if status_synced:
            manifest["status"] = "done"
            q2_readme += "\n状态：`done`\n鐘舵€侊細`done`\n"
            root_readme += "\n| q2 | done |\n`q2_done`\n"
        add(
            "task3_status_files_synced",
            "schema",
            q2_manifest_path,
            manifest.get("status") == "done"
            and "状态：`done`" in q2_readme
            and "| q2 | done |" in root_readme
            and "q2_first_stage_done" not in root_readme,
        )

    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q2 validation")
    parser.add_argument("--config", default="configs/default.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    checks = validate_outputs(root, config_path=args.config, require_validation_table=False)
    save_table(checks, stem="q2_validation_checks", question_dir=root / "questions" / "q2")
    failed = checks[~checks["passed"]]
    if not failed.empty:
        print(f"[error] q2 validation failed: {failed['check'].tolist()}")
        return 1
    print(f"[ok] q2 validation passed: {len(checks)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
