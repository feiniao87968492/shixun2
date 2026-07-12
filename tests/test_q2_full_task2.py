from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
Q2 = ROOT / "questions" / "q2"
SCRIPTS = Q2 / "scripts"
TABLES = Q2 / "artifacts" / "tables"
FIGURES = Q2 / "artifacts" / "figures"
FIGURE_DATA = Q2 / "artifacts" / "figure_data"
MODELS = Q2 / "artifacts" / "models"


def load_q2_module(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"q2_full_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_q2_config_defines_full_ode_hierarchy_and_bounds() -> None:
    config = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))["q2"]

    assert config["ode"]["model_variants"] == [
        "vacuum",
        "drag",
        "constant_lift",
        "spin_factor_lift",
    ]
    bounds = config["ode"]["parameter_bounds"]
    assert {"cd", "cl", "lift_scale"}.issubset(bounds)
    assert len(bounds["cd"]) == len(bounds["cl"]) == len(bounds["lift_scale"]) == 2
    assert bounds["cd"][0] < bounds["cd"][1]
    assert bounds["cl"][0] < bounds["cl"][1]
    assert bounds["lift_scale"][0] < bounds["lift_scale"][1]


def test_lift_ode_supports_backspin_and_lateral_symmetry() -> None:
    ode_model = load_q2_module("ode_model")
    config = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))["q2"]
    constants = ode_model.PhysicalConstants.from_config(config["physics"])
    solver = {**config["ode"]["solver"], "max_step": 0.05}
    row = pd.Series(
        {
            "record_id": 1,
            "ball_speed_mph": 150.0,
            "launch_angle_deg": 12.0,
            "launch_direction_deg": 0.0,
            "spin_rate_rpm": 3000.0,
            "spin_axis_deg": 0.0,
            "carry_distance_yd": 160.0,
            "apex_height_yd": 30.0,
            "lateral_offset_yd": 0.0,
        }
    )

    drag, _ = ode_model.simulate_shot(
        row,
        model="drag",
        constants=constants,
        solver=solver,
        cd=0.20,
    )
    lifted, trajectory = ode_model.simulate_shot(
        row,
        model="constant_lift",
        constants=constants,
        solver=solver,
        cd=0.20,
        cl=0.20,
        keep_trajectory=True,
    )
    spin_factor, _ = ode_model.simulate_shot(
        row,
        model="spin_factor_lift",
        constants=constants,
        solver=solver,
        cd=0.20,
        lift_scale=1.0,
    )

    assert lifted["integration_status"] == "success"
    assert spin_factor["integration_status"] == "success"
    assert lifted["predicted_apex_yd"] > drag["predicted_apex_yd"]
    assert abs(lifted["predicted_lateral_yd"]) < 1e-6
    assert {"time_s", "x_m", "y_m", "z_m", "x_yd", "y_yd", "z_yd"}.issubset(trajectory.columns)
    assert trajectory[["x_m", "y_m", "z_m"]].notna().all().all()


def test_full_task2_tables_have_required_models_and_schemas() -> None:
    metrics = pd.read_csv(TABLES / "q2_ode_test_metrics.csv")
    parameters = pd.read_csv(TABLES / "q2_ode_parameters.csv")
    surface = pd.read_csv(TABLES / "q2_ode_parameter_surface.csv")
    predictions = pd.read_csv(TABLES / "q2_ode_test_predictions.csv")
    typical = pd.read_csv(TABLES / "q2_typical_records.csv")
    typical_errors = pd.read_csv(TABLES / "q2_ode_typical_errors.csv")
    trajectories = pd.read_csv(TABLES / "q2_typical_trajectories.csv")
    sensitivity = pd.read_csv(TABLES / "q2_ode_sensitivity.csv")
    repeated_split = pd.read_csv(TABLES / "q2_supervised_repeated_split.csv")
    validation = pd.read_csv(TABLES / "q2_ode_validation_checks.csv")

    expected_models = {"vacuum", "drag", "constant_lift", "spin_factor_lift"}
    assert expected_models.issubset(set(metrics["model"]))
    assert expected_models.issubset(set(predictions["model"]))
    assert {"C_D", "C_L", "k_L"}.issubset(set(parameters["parameter"]))
    assert {"cd", "objective"}.issubset(surface.columns)
    assert "cl" in surface.columns or "lift_scale" in surface.columns

    assert set(typical["target_distance_yd"]) == {100, 150, 200}
    assert {
        "target_distance_yd",
        "sample_id",
        "actual_carry_yd",
        "distance_to_target_yd",
        "ball_speed_mph",
        "launch_angle_deg",
        "launch_direction_deg",
        "spin_rate_rpm",
        "spin_axis_deg",
    }.issubset(typical.columns)
    assert {
        "sample_id",
        "target_group",
        "model",
        "actual_carry_yd",
        "predicted_carry_yd",
        "carry_absolute_error_yd",
        "carry_relative_error_pct",
        "actual_apex_yd",
        "predicted_apex_yd",
        "apex_absolute_error_yd",
        "apex_relative_error_pct",
        "actual_lateral_yd",
        "predicted_lateral_yd",
        "lateral_absolute_error_yd",
        "flight_time_s",
        "integration_status",
    }.issubset(typical_errors.columns)
    assert expected_models.issubset(set(typical_errors["model"]))

    assert {
        "sample_id",
        "target_group",
        "model",
        "time_s",
        "x_m",
        "y_m",
        "z_m",
        "x_yd",
        "y_yd",
        "z_yd",
    }.issubset(trajectories.columns)
    assert {"parameter", "relative_change", "metric", "baseline_value", "scenario_value", "delta"}.issubset(
        sensitivity.columns
    )
    assert {"target", "metric", "mean", "std", "runs", "model_win_frequency"}.issubset(repeated_split.columns)

    assert {
        "positive_backspin_lifts_up",
        "zero_sidespin_zero_direction_lateral_near_zero",
        "full_ode_variants_present",
    }.issubset(set(validation["check"]))
    assert validation["passed"].astype(bool).all()


def test_full_task2_figures_have_same_stem_data_and_metadata() -> None:
    stems = [
        "q2_ode_parameter_surface",
        "q2_typical_trajectories_3d",
        "q2_typical_trajectories_side",
        "q2_typical_trajectories_top",
        "q2_ode_model_comparison",
        "q2_ode_sensitivity",
    ]
    for stem in stems:
        assert (FIGURES / f"{stem}.png").stat().st_size > 0
        assert (FIGURE_DATA / f"{stem}.csv").stat().st_size > 0
        assert (FIGURE_DATA / f"{stem}.meta.json").stat().st_size > 0

    assert (MODELS / "q2_ode_parameters.json").stat().st_size > 0
