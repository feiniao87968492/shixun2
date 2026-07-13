from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
Q3 = ROOT / "questions" / "q3"
TABLES = Q3 / "artifacts" / "tables"
SCRIPT_DIR = Q3 / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def require_csv(path: Path) -> pd.DataFrame:
    assert path.exists(), f"missing q3 task6 artifact: {path.relative_to(ROOT)}"
    assert path.stat().st_size > 0, f"empty q3 task6 artifact: {path.relative_to(ROOT)}"
    return pd.read_csv(path)


def read_q3_config() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))["q3"]


def test_task6_config_candidate_frame_and_de_success_semantics() -> None:
    from objective import candidate_frame

    config = read_q3_config()
    scenarios = config["perturbation"]["launch_direction_scenarios"]
    assert scenarios["ideal"]["sd_deg"] == pytest.approx(0.0)
    assert scenarios["stable_player"]["sd_deg"] == pytest.approx(0.5)
    assert scenarios["ordinary_player"]["sd_deg"] == pytest.approx(1.0)

    designs = candidate_frame(
        np.array(
            [
                [120.0, 19.0, 2400.0, 0.1],
                [121.0, 20.0, 2500.0, -0.2],
            ]
        ),
        launch_direction_deg=[0.0, 0.5],
    )
    assert designs["launch_direction_deg"].tolist() == pytest.approx([0.0, 0.5])

    runs = require_csv(TABLES / "q3_optimization_runs.csv")
    for column in ["scipy_success", "objective_finite", "accepted"]:
        assert column in runs.columns
    assert runs["scipy_success"].astype(bool).all()
    assert runs["objective_finite"].astype(bool).all()
    assert runs["accepted"].astype(bool).all()
    assert not runs["message"].astype(str).str.contains("fail|abnormal|maxiter|maxfev", case=False).any()


def test_task6_robust_candidate_pool_uses_full_supported_near_optimal_set() -> None:
    config = read_q3_config()
    top = require_csv(TABLES / "q3_top_candidates.csv")
    pool = require_csv(TABLES / "q3_robust_candidate_pool.csv")
    selected = pool[pool["selected_for_robustness"].astype(bool)]

    required_columns = {
        "candidate_id",
        "nominal_rank",
        "objective_yd",
        "support_category",
        "selection_method",
        "cluster_id",
        "selected_for_robustness",
    }
    assert required_columns.issubset(pool.columns)
    assert len(selected) != 12
    assert selected["support_category"].eq("supported").all()

    nominal = top.sort_values(["objective_yd", "support_knn_distance"]).iloc[0]
    tolerance = float(config["near_optimal_tolerance_yd"])
    supported_near = top[
        (top["support_category"] == "supported")
        & (top["objective_yd"] <= float(nominal["objective_yd"]) + tolerance)
    ]
    assert str(nominal["candidate_id"]) in set(selected["candidate_id"].astype(str))
    if len(supported_near) <= 500:
        assert set(selected["candidate_id"].astype(str)) == set(supported_near["candidate_id"].astype(str))
        assert selected["selection_method"].eq("all_supported_near_optimal").all()
    else:
        assert 50 <= len(selected) <= 100
        assert {"nominal", "diverse_sample"}.issubset(set(selected["selection_method"]))

    detail = require_csv(TABLES / "q3_parameter_robustness.csv")
    for column in [
        "parameter_scenario",
        "launch_direction_sd_deg",
        "common_noise_draw_id",
        "p90_ci_low",
        "p90_ci_high",
        "robustness_statistical_tie",
    ]:
        assert column in detail.columns
    assert {"ideal", "stable_player", "ordinary_player"}.issubset(set(detail["parameter_scenario"]))


def test_task6_joint_model_parameter_robustness_drives_final_recommendation() -> None:
    summary = require_csv(TABLES / "q3_joint_robustness_summary.csv")
    detail = require_csv(TABLES / "q3_joint_robustness_detail.csv")
    optimal = require_csv(TABLES / "q3_optimal_parameters.csv")

    required_summary_columns = {
        "candidate_id",
        "parameter_scenario",
        "model_member_count",
        "simulation_count",
        "mean_miss_distance_yd",
        "median_miss_distance_yd",
        "p90_miss_distance_yd",
        "p95_miss_distance_yd",
        "worst_model_mean_miss_yd",
        "probability_within_3yd",
        "probability_within_5yd",
        "objective_prediction_std",
        "support_category",
        "objective_yd",
        "support_knn_distance",
        "out_of_support_fraction",
    }
    assert required_summary_columns.issubset(summary.columns)
    assert required_summary_columns.intersection(detail.columns)
    assert "stable_player" in set(summary["parameter_scenario"])
    assert summary["model_member_count"].astype(int).ge(5).all()
    assert summary["simulation_count"].astype(int).gt(0).all()

    required_optima = {
        "nominal_optimum",
        "single_surrogate_robust_optimum",
        "joint_robust_recommended_optimum",
    }
    assert required_optima.issubset(set(optimal["candidate_type"]))

    rec = optimal.set_index("candidate_type").loc["joint_robust_recommended_optimum"]
    stable = summary[summary["parameter_scenario"] == "stable_player"].copy()
    best_nominal = float(stable["objective_yd"].min())
    eligible = stable[
        (stable["support_category"] == "supported")
        & (stable["objective_yd"] <= best_nominal + 0.5 + 1e-12)
        & (stable["out_of_support_fraction"] <= 0.05 + 1e-12)
    ].copy()
    assert not eligible.empty
    expected = eligible.sort_values(["p90_miss_distance_yd", "support_knn_distance", "candidate_id"]).iloc[0]
    assert str(rec["candidate_id"]) == str(expected["candidate_id"])
    assert float(rec["joint_p90_miss_distance_yd"]) == pytest.approx(
        float(expected["p90_miss_distance_yd"]), abs=1e-9
    )


def test_task6_target_distances_are_independently_reoptimized() -> None:
    runs = require_csv(TABLES / "q3_target_optimization_runs.csv")
    optimal = require_csv(TABLES / "q3_target_optimal_parameters.csv")
    original_pool = require_csv(TABLES / "q3_top_candidates.csv")

    targets = {195.0, 200.0, 205.0}
    assert targets.issubset(set(runs["target_distance_yd"].astype(float)))
    assert targets.issubset(set(optimal["target_distance_yd"].astype(float)))

    original_ids = set(original_pool["candidate_id"].astype(str))
    assert not set(optimal["candidate_id"].astype(str)).issubset(original_ids)

    for target in sorted(targets):
        target_runs = runs[runs["target_distance_yd"].astype(float) == target]
        assert target_runs["run_stage"].eq("lhs_baseline").any()
        assert target_runs.loc[target_runs["run_stage"].eq("differential_evolution"), "seed"].nunique() >= 3
        assert target_runs["run_stage"].eq("local_refinement").any()

        target_optimal = optimal[optimal["target_distance_yd"].astype(float) == target]
        assert target_optimal["support_category"].eq("supported").any()
        lhs_best = target_runs.loc[target_runs["run_stage"].eq("lhs_baseline"), "objective_yd"].min()
        best_supported = target_optimal[target_optimal["support_category"] == "supported"]["objective_yd"].min()
        assert float(best_supported) <= float(lhs_best) + 1e-9


def test_task6_near_optimal_ranges_support_and_validation_are_complete() -> None:
    ranges = require_csv(TABLES / "q3_near_optimal_parameter_ranges.csv")
    support = require_csv(TABLES / "q3_support_comparison.csv")
    validation = require_csv(TABLES / "q3_validation_checks.csv")

    assert {
        "variable",
        "min",
        "q10",
        "median",
        "q90",
        "max",
        "distinct_parameter_count",
        "distinct_prediction_pair_count",
        "largest_prediction_plateau_size",
        "solution_non_unique_under_surrogate",
    }.issubset(ranges.columns)
    assert {
        "ball_speed_mph",
        "launch_angle_deg",
        "spin_rate_rpm",
        "spin_axis_deg",
    }.issubset(set(ranges["variable"]))
    assert ranges["distinct_parameter_count"].astype(int).max() > 1

    assert {
        "candidate_id",
        "decision_space_support",
        "full_model_input_support",
        "supported_fraction",
        "borderline_fraction",
        "out_of_support_fraction",
    }.issubset(support.columns)
    assert (support["out_of_support_fraction"].between(0.0, 1.0)).all()

    optimal = require_csv(TABLES / "q3_optimal_parameters.csv")
    rec = optimal.set_index("candidate_type").loc["joint_robust_recommended_optimum"]
    rec_support = support[support["candidate_id"].astype(str) == str(rec["candidate_id"])]
    assert not rec_support.empty
    assert rec_support["decision_space_support"].iloc[0] != "out_of_support"
    assert rec_support["full_model_input_support"].iloc[0] != "out_of_support"
    assert float(rec_support["out_of_support_fraction"].max()) <= 0.05

    required_checks = {
        "all_supported_near_candidates_accounted_for",
        "robust_candidate_pool_not_hardcoded_to_12",
        "common_random_numbers_used",
        "launch_direction_perturbation_present",
        "joint_model_parameter_robustness_complete",
        "robust_recommendation_matches_joint_p90_minimum",
        "target_195_independently_optimized",
        "target_200_independently_optimized",
        "target_205_independently_optimized",
        "target_specific_solution_beats_target_lhs",
        "full_input_support_checked",
        "perturbation_out_of_support_fraction_reported",
        "scipy_success_all_true",
        "near_optimal_parameter_ranges_generated",
        "solution_non_uniqueness_reported",
    }
    assert required_checks.issubset(set(validation["check"]))
    assert validation[validation["check"].isin(required_checks)]["passed"].astype(bool).all()

    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    q3_readme = (Q3 / "README.md").read_text(encoding="utf-8")
    manifest = yaml.safe_load((Q3 / "manifest.yaml").read_text(encoding="utf-8"))
    assert "| q3 | done |" in root_readme or "q3 | done" in root_readme
    assert "状态：`done`" in q3_readme
    assert manifest["status"] == "done"
    forbidden = "距洞 0.010 yd 的最优击球策略"
    assert forbidden not in root_readme
    assert forbidden not in q3_readme
