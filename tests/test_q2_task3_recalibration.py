from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
Q2 = ROOT / "questions" / "q2"
TABLES = Q2 / "artifacts" / "tables"
FIGURES = Q2 / "artifacts" / "figures"
FIGURE_DATA = Q2 / "artifacts" / "figure_data"


def read_config() -> dict:
    return yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))["q2"]


def require_csv(path: Path) -> pd.DataFrame:
    assert path.exists(), f"missing expected task3 artifact: {path.relative_to(ROOT)}"
    assert path.stat().st_size > 0, f"empty task3 artifact: {path.relative_to(ROOT)}"
    return pd.read_csv(path)


def test_task3_config_declares_initial_height_and_separate_calibration_wiring() -> None:
    config = read_config()

    assert config["physics"]["initial_height_m"] == pytest.approx(0.01)
    assert config["physics"]["initial_height_type"] == "numerical_convention"

    drag = config["ode"]["drag_calibration"]
    lift = config["ode"]["lift_calibration"]
    assert drag["representative_count"] == 36
    assert drag["grid_size"] == 10
    assert lift["representative_count"] == 24
    assert lift["grid_size"] == 6
    assert (drag["representative_count"], drag["grid_size"]) != (
        lift["representative_count"],
        lift["grid_size"],
    )


def test_task3_calibration_records_and_optimization_runs_are_separate() -> None:
    config = read_config()
    drag_records = require_csv(TABLES / "q2_drag_calibration_records.csv")
    lift_records = require_csv(TABLES / "q2_lift_calibration_records.csv")

    expected_columns = {
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
    assert expected_columns.issubset(drag_records.columns)
    assert expected_columns.issubset(lift_records.columns)
    assert len(drag_records) == int(config["ode"]["drag_calibration"]["representative_count"])
    assert len(lift_records) == int(config["ode"]["lift_calibration"]["representative_count"])
    assert set(drag_records["calibration_type"]) == {"drag"}
    assert set(lift_records["calibration_type"]) == {"lift"}

    expectations = {
        "q2_drag_optimization_runs.csv": {"initial_cd", "final_cd"},
        "q2_constant_lift_optimization_runs.csv": {"initial_cd", "initial_lift", "final_cd", "final_lift"},
        "q2_spin_factor_optimization_runs.csv": {"initial_cd", "initial_lift", "final_cd", "final_lift"},
    }
    for filename, model_columns in expectations.items():
        runs = require_csv(TABLES / filename)
        assert {
            "objective",
            "success",
            "message",
            "iterations",
            "coarse_grid_rank",
            "selected",
            "full_train_objective",
        }.issubset(runs.columns)
        assert model_columns.issubset(runs.columns)
        assert runs["success"].astype(bool).any(), f"{filename} has no successful local optimization"
        selected = runs[runs["selected"].astype(bool)]
        assert len(selected) == 1, f"{filename} must mark exactly one selected optimization run"
        assert selected["full_train_objective"].notna().all(), f"{filename} lacks full-train objective evidence"


def test_task3_parameters_include_boundary_metadata_and_model_roles() -> None:
    parameters = require_csv(TABLES / "q2_ode_parameters.csv")
    assert {
        "at_lower_bound",
        "at_upper_bound",
        "distance_to_lower_bound",
        "distance_to_upper_bound",
        "boundary_warning",
        "parameter_status",
        "full_train_objective",
    }.issubset(parameters.columns)

    drag_cd = parameters[(parameters["model"] == "drag") & (parameters["parameter"] == "C_D")].iloc[0]
    assert drag_cd["parameter_status"] in {"ok", "boundary_solution"}
    if bool(drag_cd["at_lower_bound"]):
        assert drag_cd["parameter_status"] == "boundary_solution"
        assert str(drag_cd["boundary_warning"])

    metadata = json.loads((Q2 / "artifacts" / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["best_fit_ode_model"] == "constant_lift"
    assert metadata["q3_compatible_ode_model"] == "spin_factor_lift"
    assert "trajectory_model" not in metadata


def test_task3_dual_trajectory_sets_and_figure_bundles_exist() -> None:
    for model_key, model_name in [
        ("constant_lift", "constant_lift"),
        ("spin_factor", "spin_factor_lift"),
    ]:
        trajectories = require_csv(TABLES / f"q2_typical_trajectories_{model_key}.csv")
        assert set(trajectories["model"]) == {model_name}
        assert {"sample_id", "target_group", "time_s", "x_m", "y_m", "z_m", "x_yd", "y_yd", "z_yd"}.issubset(
            trajectories.columns
        )
        for suffix in ["3d", "side", "top"]:
            stem = f"q2_typical_trajectories_{model_key}_{suffix}"
            assert (FIGURES / f"{stem}.png").stat().st_size > 0
            assert (FIGURE_DATA / f"{stem}.csv").stat().st_size > 0
            meta_path = FIGURE_DATA / f"{stem}.meta.json"
            assert meta_path.stat().st_size > 0
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            meta_text = json.dumps(metadata, ensure_ascii=False)
            assert model_name in meta_text


def test_task3_sensitivity_carry_definition_and_validation_scope() -> None:
    sensitivity = require_csv(TABLES / "q2_ode_sensitivity.csv")
    assert {"model", "sensitivity_type", "parameter", "metric", "baseline_value", "scenario_value", "delta"}.issubset(
        sensitivity.columns
    )
    assert {"constant_lift", "spin_factor_lift"}.issubset(set(sensitivity["model"]))
    assert {"parameter", "wind", "spin_decay", "solver_tolerance", "initial_height"}.issubset(
        set(sensitivity["sensitivity_type"])
    )
    wind_rows = sensitivity[sensitivity["sensitivity_type"] == "wind"]
    assert {"no_wind", "tailwind_1mps", "headwind_1mps"}.issubset(set(wind_rows["parameter"]))
    carry = wind_rows[wind_rows["metric"] == "carry_yd"].pivot_table(
        index="model", columns="parameter", values="scenario_value", aggfunc="mean"
    )
    assert ((carry["tailwind_1mps"] > carry["no_wind"]) & (carry["no_wind"] > carry["headwind_1mps"])).all()

    carry_def = require_csv(TABLES / "q2_carry_definition_comparison.csv")
    assert {"model", "carry_definition", "rmse", "mae", "mape", "bias"}.issubset(carry_def.columns)
    assert {"D_x", "D_r"}.issubset(set(carry_def["carry_definition"]))
    assert {"vacuum", "drag", "constant_lift", "spin_factor_lift"}.issubset(set(carry_def["model"]))

    validation = require_csv(TABLES / "q2_validation_checks.csv")
    required_checks = {
        "task3_drag_representative_count_matches_config",
        "task3_lift_representative_count_matches_config",
        "task3_drag_optimization_success",
        "task3_constant_lift_optimization_success",
        "task3_spin_factor_optimization_success",
        "task3_wind_direction_average_order",
        "task3_metrics_recomputed_from_predictions",
        "task3_status_files_synced",
    }
    assert required_checks.issubset(set(validation["check"]))
    assert validation[validation["check"].isin(required_checks)]["passed"].astype(bool).all()


def test_task3_run_metadata_records_reproducibility_inputs() -> None:
    metadata = json.loads((Q2 / "artifacts" / "run_metadata.json").read_text(encoding="utf-8"))
    required = {
        "git_commit",
        "data_path",
        "data_sha256",
        "config_path",
        "config_sha256",
        "python_version",
        "package_versions",
        "train_ids_sha256",
        "test_ids_sha256",
        "drag_calibration_record_ids",
        "lift_calibration_record_ids",
        "best_fit_ode_model",
        "q3_compatible_ode_model",
        "optimization_runs",
    }
    assert required.issubset(metadata)
    assert len(metadata["git_commit"]) >= 7
    assert len(metadata["data_sha256"]) == 64
    assert len(metadata["config_sha256"]) == 64
    assert len(metadata["train_ids_sha256"]) == 64
    assert len(metadata["test_ids_sha256"]) == 64
    assert metadata["drag_calibration_record_ids"]
    assert metadata["lift_calibration_record_ids"]
    assert {
        "drag",
        "constant_lift",
        "spin_factor_lift",
    }.issubset(metadata["optimization_runs"])
