from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
Q3 = ROOT / "questions" / "q3"
TABLES = Q3 / "artifacts" / "tables"
FIGURES = Q3 / "artifacts" / "figures"
FIGURE_DATA = Q3 / "artifacts" / "figure_data"
MODELS = Q3 / "artifacts" / "models"


def require_csv(path: Path) -> pd.DataFrame:
    assert path.exists(), f"missing q3 task5 artifact: {path.relative_to(ROOT)}"
    assert path.stat().st_size > 0, f"empty q3 task5 artifact: {path.relative_to(ROOT)}"
    return pd.read_csv(path)


def read_config() -> dict[str, Any]:
    config = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))
    assert "q3" in config
    return config["q3"]


def assert_posix_paths(value: Any) -> None:
    if isinstance(value, dict):
        for child in value.values():
            assert_posix_paths(child)
    elif isinstance(value, list):
        for child in value:
            assert_posix_paths(child)
    elif isinstance(value, str) and (
        value.startswith("questions") or value.startswith("configs") or value.startswith("data")
    ):
        assert "\\" not in value, f"metadata path is not POSIX style: {value}"


def test_task5_config_and_manifest_use_final_q2_dependencies() -> None:
    q3_config = read_config()
    assert q3_config["target"]["forward_distance_yd"] == pytest.approx(200.0)
    assert q3_config["fixed_inputs"]["launch_direction_deg"] == pytest.approx(0.0)
    assert q3_config["baseline"]["sample_count"] >= 20_000
    assert q3_config["differential_evolution"]["seeds"] == [2026, 2027, 2028, 2029, 2030]
    assert q3_config["perturbation"]["simulations"] >= 2_000
    assert set(q3_config["ode_verification"]["models"]) >= {"constant_lift", "spin_factor_lift"}

    manifest = yaml.safe_load((Q3 / "manifest.yaml").read_text(encoding="utf-8"))
    upstream = set(manifest["inputs"]["upstream_artifacts"])
    required = {
        "questions/q2/artifacts/models/q2_carry_model.joblib",
        "questions/q2/artifacts/models/q2_apex_model.joblib",
        "questions/q2/artifacts/models/q2_ode_parameters.json",
        "questions/q2/artifacts/run_metadata.json",
        "questions/q2/artifacts/tables/q2_data_split.csv",
        "questions/q2/artifacts/tables/q2_validation_checks.csv",
    }
    assert required.issubset(upstream)
    assert "questions/q2/artifacts/models/q2_prediction_model.joblib" not in upstream
    assert manifest["status"] == "done"


def test_task5_core_artifacts_and_figures_exist() -> None:
    for stem in [
        "q3_dependency_audit",
        "q3_lateral_model_metrics",
        "q3_lateral_predictions",
        "q3_surrogate_ensemble_metrics",
        "q3_search_bounds",
        "q3_support_threshold",
        "q3_training_support",
        "q3_best_observed_baseline",
        "q3_sampling_baseline",
        "q3_optimization_runs",
        "q3_top_candidates",
        "q3_optimal_parameters",
        "q3_parameter_robustness",
        "q3_model_crosscheck",
        "q3_target_distance_sensitivity",
        "q3_ode_crosscheck",
        "q3_optimal_trajectory",
        "q3_validation_checks",
    ]:
        require_csv(TABLES / f"{stem}.csv")

    assert (MODELS / "q3_lateral_model.joblib").exists()
    assert (Q3 / "artifacts" / "run_metadata.json").exists()

    for stem in [
        "q3_optimal_trajectory_3d",
        "q3_optimal_trajectory_side",
        "q3_optimal_trajectory_top",
        "q3_objective_slice_speed_angle",
        "q3_objective_slice_spin",
    ]:
        assert (FIGURES / f"{stem}.png").exists(), stem
        require_csv(FIGURE_DATA / f"{stem}.csv")
        assert (FIGURE_DATA / f"{stem}.meta.json").exists(), stem


def test_task5_lateral_surrogate_uses_fixed_split_without_mape_selection() -> None:
    audit = require_csv(TABLES / "q3_dependency_audit.csv")
    assert audit["passed"].astype(bool).all()
    values = dict(zip(audit["check"], audit["value"], strict=False))
    assert int(values["q2_train_count"]) == 514
    assert int(values["q2_test_count"]) == 221
    assert int(values["q2_split_overlap_count"]) == 0
    assert values["q3_ode_verified"] == "true"

    metrics = require_csv(TABLES / "q3_lateral_model_metrics.csv")
    expected_models = {"dummy", "linear", "ridge", "hist_gradient_boosting", "extra_trees"}
    assert expected_models.issubset(set(metrics["model"]))
    assert "mape" not in {column.lower() for column in metrics.columns}
    assert metrics["selected"].astype(bool).sum() == 1
    selected = metrics[metrics["selected"].astype(bool)].iloc[0]
    assert selected["selection_metric"] == "cv_rmse"
    assert math.isfinite(float(selected["test_rmse"]))
    assert math.isfinite(float(selected["test_bias"]))

    predictions = require_csv(TABLES / "q3_lateral_predictions.csv")
    assert len(predictions) == 221
    assert {"record_id", "actual_lateral_yd", "predicted_lateral_yd", "residual_yd"}.issubset(
        predictions.columns
    )


def test_task5_optimization_objective_and_support_are_consistent() -> None:
    config = read_config()
    optimal = require_csv(TABLES / "q3_optimal_parameters.csv")
    assert {"nominal_optimum", "robust_recommended_optimum"}.issubset(set(optimal["candidate_type"]))

    for row in optimal.itertuples(index=False):
        assert config["variables"]["ball_speed_mph"]["lower"] <= row.ball_speed_mph <= config["variables"]["ball_speed_mph"]["upper"]
        assert config["variables"]["launch_angle_deg"]["lower"] <= row.launch_angle_deg <= config["variables"]["launch_angle_deg"]["upper"]
        assert config["variables"]["spin_rate_rpm"]["lower"] <= row.spin_rate_rpm <= config["variables"]["spin_rate_rpm"]["upper"]
        assert config["variables"]["spin_axis_deg"]["lower"] <= row.spin_axis_deg <= config["variables"]["spin_axis_deg"]["upper"]
        assert row.launch_direction_deg == pytest.approx(0.0)
        manual = math.sqrt(
            (row.predicted_carry_yd - config["target"]["forward_distance_yd"]) ** 2
            + (row.predicted_lateral_yd - config["target"]["lateral_yd"]) ** 2
        )
        assert row.objective_yd == pytest.approx(manual, abs=1e-9)

    nominal = optimal.set_index("candidate_type").loc["nominal_optimum"]
    robust = optimal.set_index("candidate_type").loc["robust_recommended_optimum"]
    assert robust["support_category"] == "supported"
    assert float(robust["objective_yd"]) <= float(nominal["objective_yd"]) + float(
        config["near_optimal_tolerance_yd"]
    ) + 1e-9

    observed = require_csv(TABLES / "q3_best_observed_baseline.csv").iloc[0]
    assert float(nominal["objective_yd"]) <= float(observed["observed_objective_yd"]) + 1e-9

    sampling = require_csv(TABLES / "q3_sampling_baseline.csv")
    assert int(sampling["sample_count"].iloc[0]) >= 20_000
    assert len(sampling) == 100
    assert float(nominal["objective_yd"]) <= float(sampling["objective_yd"].min()) + 1e-9

    runs = require_csv(TABLES / "q3_optimization_runs.csv")
    assert set(runs["seed"]) == {2026, 2027, 2028, 2029, 2030}
    assert runs["success"].astype(bool).all()
    assert runs["objective_yd"].notna().all()
    assert runs["function_evaluations"].astype(int).gt(0).all()


def test_task5_robustness_model_crosscheck_and_ode_are_recomputable() -> None:
    config = read_config()
    optimal = require_csv(TABLES / "q3_optimal_parameters.csv")
    robust = optimal.set_index("candidate_type").loc["robust_recommended_optimum"]
    robustness = require_csv(TABLES / "q3_parameter_robustness.csv")
    robust_detail = robustness[robustness["candidate_id"] == robust["candidate_id"]]
    assert len(robust_detail) >= int(config["perturbation"]["simulations"])
    recomputed_p90 = float(robust_detail["miss_distance_yd"].quantile(0.90))
    assert float(robust["p90_miss_distance_yd"]) == pytest.approx(recomputed_p90, abs=1e-9)

    crosscheck = require_csv(TABLES / "q3_model_crosscheck.csv")
    assert crosscheck["carry_model_member"].nunique() >= 5
    assert crosscheck["lateral_model_member"].nunique() >= 5
    assert {"stable_across_models", "moderately_model_sensitive", "highly_model_sensitive"}.issuperset(
        set(crosscheck["model_sensitivity_class"])
    )
    summary = crosscheck.drop_duplicates("candidate_id")
    assert summary["objective_prediction_std"].ge(0.0).all()

    sensitivity = require_csv(TABLES / "q3_target_distance_sensitivity.csv")
    assert {195.0, 200.0, 205.0}.issubset(set(sensitivity["target_distance_yd"].astype(float)))

    ode = require_csv(TABLES / "q3_ode_crosscheck.csv")
    assert {"best_observed_baseline", "nominal_optimum", "robust_recommended_optimum"}.issubset(
        set(ode["candidate_type"])
    )
    assert {"constant_lift", "spin_factor_lift"}.issubset(set(ode["model"]))
    assert ode["integration_status"].eq("success").all()
    assert ode["q2_parameter_git_commit"].astype(str).str.len().gt(0).all()
    assert ode["verification_claim"].str.contains("crosscheck", case=False).all()

    trajectory = require_csv(TABLES / "q3_optimal_trajectory.csv")
    assert {"model", "time_s", "x_m", "y_m", "z_m", "x_yd", "y_yd", "z_yd"}.issubset(
        trajectory.columns
    )
    assert {"constant_lift", "spin_factor_lift"}.issubset(set(trajectory["model"]))


def test_task5_validation_metadata_and_docs_are_synced() -> None:
    validation = require_csv(TABLES / "q3_validation_checks.csv")
    required = {
        "task5_manifest_uses_final_q2_dependencies",
        "task5_q2_dependencies_verified",
        "task5_fixed_split_reused",
        "task5_lateral_model_selected_by_cv_rmse",
        "task5_support_threshold_train_only",
        "task5_sampling_baseline_size",
        "task5_differential_evolution_five_seeds",
        "task5_nominal_and_robust_optima_reported",
        "task5_objective_recomputes",
        "task5_robust_metrics_recomputable",
        "task5_model_crosscheck_complete",
        "task5_target_distance_sensitivity_complete",
        "task5_ode_crosscheck_successful",
        "task5_figures_have_data_and_metadata",
        "task5_metadata_paths_posix",
        "task5_status_files_synced",
    }
    assert required.issubset(set(validation["check"]))
    assert validation[validation["check"].isin(required)]["passed"].astype(bool).all()

    metadata = json.loads((Q3 / "artifacts" / "run_metadata.json").read_text(encoding="utf-8"))
    assert_posix_paths(metadata)
    assert metadata["q3_status"] == "done"
    assert metadata["q2_dependency_audit_passed"] is True
    assert metadata["q3_ode_verified"] is True

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    q3_readme = (Q3 / "README.md").read_text(encoding="utf-8")
    assert "q3 | done" in readme or "| q3 | done |" in readme
    assert "状态：`done`" in q3_readme

    evidence = (ROOT / "docs" / "evidence_chain.csv").read_text(encoding="utf-8")
    assert "Q3-C01" in evidence and "supported" in evidence
    assert "Q3-C02" in evidence and "supported" in evidence
