from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
Q2 = ROOT / "questions" / "q2"
SCRIPTS = Q2 / "scripts"
TABLES = Q2 / "artifacts" / "tables"


def load_q2_module(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"q2_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_q2_config_and_manifest_follow_task2_contract() -> None:
    config = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((Q2 / "manifest.yaml").read_text(encoding="utf-8"))

    assert "q2" in config
    physics = config["q2"]["physics"]
    assert physics["mass_kg"] == 0.0456
    assert physics["diameter_m"] == 0.04267
    assert physics["air_density_kg_m3"] == 1.225
    assert physics["gravity_m_s2"] == 9.80665
    assert "raw OCR" in physics["source"]

    upstream = set(manifest["inputs"]["upstream_artifacts"])
    assert "questions/q1/artifacts/tables/q1_feature_importance.csv" not in upstream
    assert {
        "questions/q1/artifacts/tables/q1_feature_summary.csv",
        "questions/q1/artifacts/tables/q1_data_audit.csv",
        "questions/q1/artifacts/tables/q1_invalid_zero_records.csv",
    }.issubset(upstream)
    assert manifest["status"] in {"first_stage_done", "done"}


def test_fixed_split_is_saved_and_is_70_30_with_no_overlap() -> None:
    split = pd.read_csv(TABLES / "q2_data_split.csv")

    assert {"record_id", "split", "random_seed"}.issubset(split.columns)
    assert len(split) == 735
    assert split["record_id"].is_unique
    assert set(split["split"]) == {"train", "test"}
    assert set(split["random_seed"]) == {2026}
    assert int((split["split"] == "train").sum()) == 514
    assert int((split["split"] == "test").sum()) == 221


def test_supervised_first_stage_artifacts_cover_models_targets_and_test_metrics() -> None:
    metrics = pd.read_csv(TABLES / "q2_supervised_metrics.csv")
    predictions = pd.read_csv(TABLES / "q2_supervised_predictions.csv")
    ci = pd.read_csv(TABLES / "q2_supervised_bootstrap_ci.csv")
    groups = pd.read_csv(TABLES / "q2_supervised_error_groups.csv")

    expected_models = {"dummy", "linear", "ridge", "extra_trees", "hist_gradient_boosting"}
    expected_targets = {"carry_distance_yd", "apex_height_yd"}
    assert expected_models.issubset(set(metrics["model"]))
    assert expected_targets == set(metrics["target"])
    assert {"launch_state_model", "full_shot_model"}.issubset(set(metrics["feature_set"]))
    assert {"rmse", "mape", "mae", "r2", "mdape", "selected"}.issubset(metrics.columns)
    assert metrics[["rmse", "mape", "mae", "mdape"]].notna().all().all()
    assert (metrics[["rmse", "mape", "mae", "mdape"]] >= 0).all().all()
    assert metrics.groupby("target")["selected"].sum().to_dict() == {
        "apex_height_yd": 1,
        "carry_distance_yd": 1,
    }

    assert len(predictions) == 221 * len(expected_targets) * 2 * len(expected_models)
    assert {"record_id", "target", "feature_set", "model", "actual", "predicted", "residual"}.issubset(
        predictions.columns
    )
    assert {"metric", "ci_low", "ci_high"}.issubset(ci.columns)
    assert {"ball_speed_mph", "launch_angle_deg", "spin_rate_rpm"}.issubset(set(groups["group_feature"]))


def test_ode_first_stage_units_vacuum_and_drag_outputs_are_verified() -> None:
    preprocessing = load_q2_module("preprocessing")
    ode_model = load_q2_module("ode_model")
    validation = pd.read_csv(TABLES / "q2_ode_validation_checks.csv")
    parameters = pd.read_csv(TABLES / "q2_ode_parameters.csv")
    metrics = pd.read_csv(TABLES / "q2_ode_test_metrics.csv")
    comparison = pd.read_csv(TABLES / "q2_ode_model_comparison.csv")
    failures = pd.read_csv(TABLES / "q2_ode_failures.csv")

    assert preprocessing.mph_to_mps(1.0) == 0.44704
    assert round(preprocessing.rpm_to_rad_s(60.0), 12) == round(2 * 3.141592653589793, 12)
    assert round(preprocessing.yd_to_m(1.0), 12) == 0.9144

    assert set(validation["check"]).issuperset(
        {
            "mph_to_mps",
            "rpm_to_rad_s",
            "yd_to_m",
            "vacuum_numeric_matches_analytic",
            "drag_model_reduces_vacuum_carry",
        }
    )
    assert validation["passed"].astype(bool).all()
    assert float(validation.loc[validation["check"] == "vacuum_numeric_matches_analytic", "value"].iloc[0]) < 1e-3

    assert {"vacuum", "drag"}.issubset(set(metrics["model"]))
    assert {"carry_rmse", "carry_mape", "apex_rmse", "apex_mape", "flight_failure_rate"}.issubset(
        metrics.columns
    )
    assert {"vacuum", "drag"}.issubset(set(comparison["model"]))
    drag_stage = parameters.loc[
        (parameters["model"] == "drag") & (parameters["parameter"] == "C_D"),
        "calibration_stage",
    ].iloc[0]
    assert drag_stage in {"preliminary_drag_only", "train_representative_grid"}
    assert {"vacuum", "drag"}.issubset(set(failures["model"]))

    config = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))["q2"]
    constants = ode_model.PhysicalConstants.from_config(config["physics"])
    assert constants.mass_kg == 0.0456
    assert constants.radius_m == 0.04267 / 2
