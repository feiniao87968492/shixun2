from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
Q2 = ROOT / "questions" / "q2"
TABLES = Q2 / "artifacts" / "tables"


def read_config() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))["q2"]


def require_csv(path: Path) -> pd.DataFrame:
    assert path.exists(), f"missing expected task4 artifact: {path.relative_to(ROOT)}"
    assert path.stat().st_size > 0, f"empty task4 artifact: {path.relative_to(ROOT)}"
    return pd.read_csv(path)


def load_ode_module() -> Any:
    spec = importlib.util.spec_from_file_location("q2_task4_ode_model", Q2 / "scripts" / "ode_model.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_posix_paths(value: Any) -> None:
    if isinstance(value, dict):
        for child in value.values():
            assert_posix_paths(child)
    elif isinstance(value, list):
        for child in value:
            assert_posix_paths(child)
    elif isinstance(value, str) and (value.startswith("questions") or value.startswith("configs") or value.startswith("data")):
        assert "\\" not in value, f"metadata path is not POSIX style: {value}"


def test_task4_config_declares_forward_carry_and_real_optimizer_controls() -> None:
    ode = read_config()["ode"]

    assert ode["carry_definition"] == "forward_x"
    assert ode["calibration_failure_penalty"] == pytest.approx(100.0)

    local = ode["local_optimization"]
    assert local["method"] == "Powell"
    assert int(local["maxiter"]) >= 40
    assert int(local["maxfev"]) >= 120
    assert float(local["xtol"]) <= 1.0e-4
    assert float(local["ftol"]) <= 1.0e-6
    assert float(local["minimum_improvement"]) > 0.0


def test_task4_ode_api_requires_explicit_carry_definition() -> None:
    ode_model = load_ode_module()
    prediction = {
        "predicted_x_carry_yd": 180.0,
        "predicted_radial_carry_yd": 183.5,
    }

    assert ode_model.select_predicted_carry(prediction, "forward_x") == pytest.approx(180.0)
    assert ode_model.select_predicted_carry(prediction, "radial") == pytest.approx(183.5)
    with pytest.raises(ValueError):
        ode_model.select_predicted_carry(prediction, "ambiguous")

    signature = inspect.signature(ode_model.simulate_shot)
    assert "carry_definition" in signature.parameters


def test_task4_optimization_runs_record_real_termination_and_acceptance() -> None:
    required_columns = {
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

    for filename in [
        "q2_drag_optimization_runs.csv",
        "q2_constant_lift_optimization_runs.csv",
        "q2_spin_factor_optimization_runs.csv",
    ]:
        runs = require_csv(TABLES / filename)
        assert required_columns.issubset(runs.columns), filename
        max_eval = runs["termination_message"].fillna("").str.contains(
            "Maximum number of function evaluations", case=False
        )
        assert not (
            max_eval
            & (
                runs["optimizer_success"].astype(bool)
                | runs["accepted"].astype(bool)
                | runs["selected"].astype(bool)
            )
        ).any()
        assert runs["function_evaluations"].astype(int).max() > 4
        assert runs["iterations"].astype(int).max() > 0

        selected = runs[runs["selected"].astype(bool)]
        assert len(selected) == 1
        row = selected.iloc[0]
        assert bool(row["optimizer_success"])
        assert bool(row["objective_finite"])
        assert bool(row["accepted"])
        assert int(row["calibration_failed_count"]) == 0
        assert int(row["full_train_failed_count"]) == 0
        assert float(row["final_objective"]) <= float(row["initial_objective"]) + 1.0e-6


def test_task4_forward_x_carry_is_the_primary_metric_everywhere() -> None:
    predictions = require_csv(TABLES / "q2_ode_test_predictions.csv")
    metrics = require_csv(TABLES / "q2_ode_test_metrics.csv").set_index("model")
    typical = require_csv(TABLES / "q2_ode_typical_errors.csv")
    sensitivity = require_csv(TABLES / "q2_ode_sensitivity.csv")
    comparison = require_csv(TABLES / "q2_carry_definition_comparison.csv")

    assert set(predictions["carry_definition"]) == {"forward_x"}
    assert np.allclose(predictions["predicted_carry_yd"], predictions["predicted_x_carry_yd"])

    for model, subset in predictions.groupby("model"):
        ok = subset[subset["integration_status"] == "success"]
        actual = ok["actual_carry_yd"].to_numpy(dtype=float)
        predicted = ok["predicted_x_carry_yd"].to_numpy(dtype=float)
        rmse = float(np.sqrt(np.mean((predicted - actual) ** 2)))
        assert float(metrics.loc[model, "carry_rmse"]) == pytest.approx(rmse, abs=1e-9)

    assert set(typical["carry_definition"]) == {"forward_x"}
    assert np.allclose(typical["predicted_carry_yd"], typical["predicted_x_carry_yd"])
    assert np.allclose(
        typical["carry_absolute_error_yd"],
        (typical["predicted_x_carry_yd"] - typical["actual_carry_yd"]).abs(),
    )

    carry_sensitivity = sensitivity[sensitivity["metric"] == "carry_yd"]
    assert set(carry_sensitivity["carry_definition"]) == {"forward_x"}

    assert {"actual_definition", "predicted_definition", "is_primary_definition"}.issubset(comparison.columns)
    primary = comparison[comparison["is_primary_definition"].astype(bool)]
    assert set(primary["carry_definition"]) == {"D_x"}
    assert set(primary["actual_definition"]) == {"carry_distance_yd"}
    assert set(primary["predicted_definition"]) == {"predicted_x_carry_yd"}


def test_task4_failure_tables_and_q3_boundary_checks_exist() -> None:
    for filename, model in [
        ("q2_drag_calibration_failures.csv", "drag"),
        ("q2_constant_lift_calibration_failures.csv", "constant_lift"),
        ("q2_spin_factor_calibration_failures.csv", "spin_factor_lift"),
    ]:
        failures = require_csv(TABLES / filename)
        assert {"model", "record_id", "stage", "integration_status", "solver_message"}.issubset(failures.columns)
        assert set(failures["model"].dropna()) <= {model}

    ode_checks = require_csv(TABLES / "q2_ode_validation_checks.csv")
    q3_checks = {
        "q3_spin_factor_boundary_stability",
        "q3_spin_factor_boundary_max_flight_time_within_limit",
        "q3_spin_factor_boundary_max_apex_within_limit",
        "q3_spin_factor_boundary_max_lateral_within_limit",
    }
    assert q3_checks.issubset(set(ode_checks["check"]))
    assert ode_checks[ode_checks["check"].isin(q3_checks)]["passed"].astype(bool).all()


def test_task4_validation_records_new_acceptance_checks() -> None:
    validation = require_csv(TABLES / "q2_validation_checks.csv")
    required = {
        "task4_configured_carry_definition_is_forward_x",
        "task4_optimizer_terminated_successfully",
        "task4_optimizer_message_not_max_evaluations",
        "task4_optimizer_iterations_positive",
        "task4_optimizer_function_evaluations_above_minimum",
        "task4_selected_run_accepted",
        "task4_selected_run_objective_finite",
        "task4_selected_run_zero_calibration_failures",
        "task4_selected_run_zero_full_train_failures",
        "task4_ode_metrics_match_forward_x_predictions",
        "task4_typical_errors_match_forward_x_predictions",
        "task4_sensitivity_uses_forward_x",
        "task4_calibration_objective_uses_forward_x",
        "task4_selected_drag_zero_full_train_failures",
        "task4_selected_constant_lift_zero_full_train_failures",
        "task4_selected_spin_factor_zero_full_train_failures",
        "task4_all_models_zero_test_failures",
        "task4_metadata_paths_posix",
        "task4_q3_boundary_stability_passed",
        "task4_status_files_synced",
    }
    assert required.issubset(set(validation["check"]))
    assert validation[validation["check"].isin(required)]["passed"].astype(bool).all()


def test_task4_metadata_records_posix_paths_and_auto_model_selection() -> None:
    metadata = json.loads((Q2 / "artifacts" / "run_metadata.json").read_text(encoding="utf-8"))
    assert_posix_paths(metadata)

    assert metadata["carry_definition"] == "forward_x"
    assert metadata["best_fit_selection_rule"] == "minimum_full_train_objective_among_accepted_models"
    assert {"drag", "constant_lift", "spin_factor_lift"}.issubset(metadata["full_train_objectives"])
    assert metadata["q3_compatible_boundary_checks_passed"] is True
