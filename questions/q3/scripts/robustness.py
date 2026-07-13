from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from objective import VARIABLES, add_objective_columns, candidate_frame, evaluate_candidates, predict_landing
from support import SupportModel, support_columns


NOISE_COLUMNS = [
    "ball_speed_noise_mph",
    "launch_angle_noise_deg",
    "launch_direction_noise_deg",
    "spin_rate_noise_rpm",
    "spin_axis_noise_deg",
]


def robust_candidate_pool(candidates: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    nominal = candidates.sort_values(["objective_yd", "support_knn_distance"]).iloc[0]
    tolerance = float(config["near_optimal_tolerance_yd"])
    near = candidates[candidates["objective_yd"] <= float(nominal["objective_yd"]) + tolerance].copy()
    if near.empty:
        near = candidates.head(1).copy()
    supported = near[near["support_category"] == "supported"].copy()
    if supported.empty:
        raise RuntimeError("No supported near-optimal q3 candidates are available for task6 robustness")

    supported = supported.sort_values(["objective_yd", "support_knn_distance", "candidate_id"]).reset_index(drop=True)
    supported["nominal_rank"] = np.arange(1, len(supported) + 1)
    supported["selected_for_robustness"] = False
    supported["selection_method"] = "not_selected"
    supported["cluster_id"] = -1

    if len(supported) <= 500:
        supported["selected_for_robustness"] = True
        supported["selection_method"] = "all_supported_near_optimal"
        return supported.reset_index(drop=True)

    sample_size = int(config.get("robust_candidate_sample_size", 75))
    sample_size = max(50, min(100, sample_size, len(supported)))
    matrix = StandardScaler().fit_transform(supported[VARIABLES].to_numpy(dtype=float))
    cluster_count = min(sample_size, len(supported))
    labels = KMeans(n_clusters=cluster_count, n_init=10, random_state=int(config["random_seed"]) + 711).fit_predict(matrix)
    supported["cluster_id"] = labels.astype(int)
    selected_indices: list[int] = []
    for cluster_id in sorted(set(labels)):
        cluster_indices = np.flatnonzero(labels == cluster_id)
        centroid = matrix[cluster_indices].mean(axis=0)
        chosen = cluster_indices[np.argmin(np.linalg.norm(matrix[cluster_indices] - centroid, axis=1))]
        selected_indices.append(int(chosen))
    if str(nominal["candidate_id"]) in set(supported["candidate_id"].astype(str)):
        nominal_index = int(supported.index[supported["candidate_id"].astype(str) == str(nominal["candidate_id"])][0])
        selected_indices.append(nominal_index)
    selected_indices = sorted(set(selected_indices))[:sample_size]
    supported.loc[selected_indices, "selected_for_robustness"] = True
    supported.loc[selected_indices, "selection_method"] = "diverse_sample"
    supported.loc[supported["candidate_id"].astype(str) == str(nominal["candidate_id"]), "selection_method"] = "nominal"
    return supported.reset_index(drop=True)


def near_optimal_candidates(candidates: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    pool = robust_candidate_pool(candidates, config)
    return pool[pool["selected_for_robustness"].astype(bool)].reset_index(drop=True)


def _common_noise(config: dict[str, Any], scenario_name: str, scenario: dict[str, Any]) -> pd.DataFrame:
    perturb = config["perturbation"]
    simulations = int(perturb["simulations"])
    rng = np.random.default_rng(int(config["random_seed"]) + 701)
    standard = rng.normal(0.0, 1.0, size=(simulations, len(NOISE_COLUMNS)))
    scales = np.asarray(
        [
            float(perturb["ball_speed_sd_mph"]),
            float(perturb["launch_angle_sd_deg"]),
            float(scenario["sd_deg"]),
            float(perturb["spin_rate_sd_rpm"]),
            float(perturb["spin_axis_sd_deg"]),
        ],
        dtype=float,
    )
    noise = standard * scales
    output = pd.DataFrame(noise, columns=NOISE_COLUMNS)
    output.insert(0, "common_noise_draw_id", np.arange(1, simulations + 1))
    output["parameter_scenario"] = scenario_name
    output["launch_direction_sd_deg"] = float(scenario["sd_deg"])
    return output


def _perturbed_designs(candidate_rows: pd.DataFrame, noise: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    base = candidate_rows[VARIABLES].to_numpy(dtype=float)
    base_direction = candidate_rows.get(
        "launch_direction_deg",
        pd.Series(float(config["fixed_inputs"]["launch_direction_deg"]), index=candidate_rows.index),
    ).to_numpy(dtype=float)
    noise_values = noise[NOISE_COLUMNS].to_numpy(dtype=float)
    candidate_count = len(candidate_rows)
    simulations = len(noise)

    values = np.repeat(base, simulations, axis=0)
    values[:, 0] += np.tile(noise_values[:, 0], candidate_count)
    values[:, 1] += np.tile(noise_values[:, 1], candidate_count)
    values[:, 2] += np.tile(noise_values[:, 3], candidate_count)
    values[:, 3] += np.tile(noise_values[:, 4], candidate_count)
    for index, variable in enumerate(VARIABLES):
        bounds = config["variables"][variable]
        values[:, index] = np.clip(values[:, index], float(bounds["lower"]), float(bounds["upper"]))
    directions = np.repeat(base_direction, simulations) + np.tile(noise_values[:, 2], candidate_count)
    designs = candidate_frame(values, launch_direction_deg=directions)
    designs["candidate_id"] = np.repeat(candidate_rows["candidate_id"].astype(str).to_numpy(), simulations)
    designs["common_noise_draw_id"] = np.tile(noise["common_noise_draw_id"].to_numpy(dtype=int), candidate_count)
    designs["simulation_index"] = designs["common_noise_draw_id"].astype(int)
    designs["parameter_scenario"] = str(noise["parameter_scenario"].iloc[0])
    designs["launch_direction_sd_deg"] = float(noise["launch_direction_sd_deg"].iloc[0])
    return designs


def _bootstrap_p90_ci(values: np.ndarray, *, seed: int, iterations: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(int(iterations), len(values)))
    boot = np.quantile(values[indices], 0.90, axis=1)
    return float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))


def simulate_parameter_robustness(
    candidate_rows: pd.DataFrame,
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: SupportModel,
    full_support_model: SupportModel,
    config: dict[str, Any],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    scenarios = config["perturbation"]["launch_direction_scenarios"]
    for scenario_name, scenario in scenarios.items():
        noise = _common_noise(config, scenario_name, scenario)
        designs = _perturbed_designs(candidate_rows, noise, config)
        evaluated = evaluate_candidates(
            designs.drop(columns=["candidate_id", "common_noise_draw_id", "simulation_index", "parameter_scenario", "launch_direction_sd_deg"]),
            carry_model=carry_model,
            lateral_model=lateral_model,
            apex_model=apex_model,
            support_model=support_model,
            target_distance_yd=float(config["target"]["forward_distance_yd"]),
            target_lateral_yd=float(config["target"]["lateral_yd"]),
        )
        full_support = support_columns(full_support_model, evaluated, prefix="full_model_input")
        detail = pd.concat(
            [
                designs[["candidate_id", "parameter_scenario", "common_noise_draw_id", "simulation_index", "launch_direction_sd_deg"]].reset_index(drop=True),
                evaluated.reset_index(drop=True),
                full_support.reset_index(drop=True),
            ],
            axis=1,
        )
        detail["miss_distance_yd"] = detail["objective_yd"].astype(float)
        frames.append(detail)
    detail = pd.concat(frames, ignore_index=True, sort=False)
    summary = robustness_summary(detail, config=config)
    detail = detail.merge(
        summary[
            [
                "candidate_id",
                "parameter_scenario",
                "p90_ci_low",
                "p90_ci_high",
                "robustness_statistical_tie",
            ]
        ],
        on=["candidate_id", "parameter_scenario"],
        how="left",
    )
    return detail


def robustness_summary(details: pd.DataFrame, config: dict[str, Any] | None = None) -> pd.DataFrame:
    rows = []
    bootstrap_iterations = int((config or {}).get("perturbation", {}).get("bootstrap_iterations", 100))
    seed_base = int((config or {}).get("random_seed", 2026)) + 1701
    group_columns = ["candidate_id", "parameter_scenario"]
    for group_index, ((candidate_id, scenario), subset) in enumerate(details.groupby(group_columns), start=1):
        miss = subset["miss_distance_yd"].to_numpy(dtype=float)
        low, high = _bootstrap_p90_ci(miss, seed=seed_base + group_index, iterations=bootstrap_iterations)
        support_col = "full_model_input_support_category"
        rows.append(
            {
                "candidate_id": str(candidate_id),
                "parameter_scenario": str(scenario),
                "launch_direction_sd_deg": float(subset["launch_direction_sd_deg"].iloc[0]),
                "mean_miss_distance_yd": float(np.mean(miss)),
                "median_miss_distance_yd": float(np.median(miss)),
                "p90_miss_distance_yd": float(np.quantile(miss, 0.90)),
                "p95_miss_distance_yd": float(np.quantile(miss, 0.95)),
                "maximum_miss_distance_yd": float(np.max(miss)),
                "probability_within_3yd": float(np.mean(miss <= 3.0)),
                "probability_within_5yd": float(np.mean(miss <= 5.0)),
                "simulations": int(len(subset)),
                "supported_fraction": float(np.mean(subset[support_col] == "supported")),
                "borderline_fraction": float(np.mean(subset[support_col] == "borderline")),
                "out_of_support_fraction": float(np.mean(subset[support_col] == "out_of_support")),
                "p90_ci_low": low,
                "p90_ci_high": high,
            }
        )
    summary = pd.DataFrame(rows)
    summary["robustness_statistical_tie"] = False
    for scenario, subset in summary.groupby("parameter_scenario"):
        best = subset.sort_values(["p90_miss_distance_yd", "candidate_id"]).iloc[0]
        overlap = (subset["p90_ci_low"] <= float(best["p90_ci_high"])) & (
            subset["p90_ci_high"] >= float(best["p90_ci_low"])
        )
        summary.loc[subset.index, "robustness_statistical_tie"] = overlap.to_numpy()
    return summary


def all_scenario_robustness_summary(details: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for candidate_id, subset in details.groupby("candidate_id"):
        miss = subset["miss_distance_yd"].to_numpy(dtype=float)
        rows.append(
            {
                "candidate_id": str(candidate_id),
                "parameter_scenario": "all_scenarios",
                "mean_miss_distance_yd": float(np.mean(miss)),
                "median_miss_distance_yd": float(np.median(miss)),
                "p90_miss_distance_yd": float(np.quantile(miss, 0.90)),
                "p95_miss_distance_yd": float(np.quantile(miss, 0.95)),
                "maximum_miss_distance_yd": float(np.max(miss)),
                "probability_within_3yd": float(np.mean(miss <= 3.0)),
                "probability_within_5yd": float(np.mean(miss <= 5.0)),
                "simulations": int(len(subset)),
            }
        )
    return pd.DataFrame(rows)


def support_comparison(
    candidate_rows: pd.DataFrame,
    robustness_detail: pd.DataFrame,
    *,
    full_support_model: SupportModel,
) -> pd.DataFrame:
    full_base = support_columns(full_support_model, candidate_rows, prefix="full_model_input")
    base = candidate_rows[["candidate_id", "support_category", "support_knn_distance"]].copy().reset_index(drop=True)
    base = pd.concat([base, full_base.reset_index(drop=True)], axis=1)
    base = base.rename(
        columns={
            "support_category": "decision_space_support",
            "support_knn_distance": "decision_space_knn_distance",
            "full_model_input_support_category": "full_model_input_support",
        }
    )
    rows = []
    for (candidate_id, scenario), subset in robustness_detail.groupby(["candidate_id", "parameter_scenario"]):
        row = base[base["candidate_id"].astype(str) == str(candidate_id)].iloc[0].to_dict()
        row["parameter_scenario"] = str(scenario)
        row["supported_fraction"] = float(np.mean(subset["full_model_input_support_category"] == "supported"))
        row["borderline_fraction"] = float(np.mean(subset["full_model_input_support_category"] == "borderline"))
        row["out_of_support_fraction"] = float(np.mean(subset["full_model_input_support_category"] == "out_of_support"))
        rows.append(row)
    return pd.DataFrame(rows)


def joint_model_parameter_robustness(
    candidate_rows: pd.DataFrame,
    *,
    carry_models: list[Any],
    lateral_models: list[Any],
    apex_model: Any,
    support_comparison_table: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    member_count = min(len(carry_models), len(lateral_models))
    scenarios = config["perturbation"]["launch_direction_scenarios"]
    detail_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    target_distance = float(config["target"]["forward_distance_yd"])
    target_lateral = float(config["target"]["lateral_yd"])

    candidate_meta = candidate_rows.set_index("candidate_id", drop=False)
    for scenario_name, scenario in scenarios.items():
        noise = _common_noise(config, scenario_name, scenario)
        designs = _perturbed_designs(candidate_rows, noise, config)
        features = designs.drop(
            columns=["candidate_id", "common_noise_draw_id", "simulation_index", "parameter_scenario", "launch_direction_sd_deg"]
        )
        candidate_ids = candidate_rows["candidate_id"].astype(str).to_numpy()
        simulations = len(noise)
        member_miss: list[np.ndarray] = []
        for member_index, (carry_model, lateral_model) in enumerate(
            zip(carry_models[:member_count], lateral_models[:member_count], strict=True),
            start=1,
        ):
            pred = predict_landing(features, carry_model=carry_model, lateral_model=lateral_model, apex_model=apex_model)
            pred = add_objective_columns(
                pred,
                target_distance_yd=target_distance,
                target_lateral_yd=target_lateral,
            )
            miss = pred["objective_yd"].to_numpy(dtype=float).reshape(len(candidate_rows), simulations)
            member_miss.append(miss)
            for candidate_index, candidate_id in enumerate(candidate_ids):
                values = miss[candidate_index]
                detail_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "parameter_scenario": scenario_name,
                        "model_member": member_index,
                        "model_member_count": 1,
                        "model_combination_rule": "paired_5_carry_5_lateral_by_member_index",
                        "simulation_count": int(simulations),
                        "mean_miss_distance_yd": float(np.mean(values)),
                        "median_miss_distance_yd": float(np.median(values)),
                        "p90_miss_distance_yd": float(np.quantile(values, 0.90)),
                        "p95_miss_distance_yd": float(np.quantile(values, 0.95)),
                        "worst_model_mean_miss_yd": float(np.mean(values)),
                        "probability_within_3yd": float(np.mean(values <= 3.0)),
                        "probability_within_5yd": float(np.mean(values <= 5.0)),
                        "objective_prediction_std": 0.0,
                    }
                )

        stacked = np.stack(member_miss, axis=0)
        for candidate_index, candidate_id in enumerate(candidate_ids):
            values = stacked[:, candidate_index, :].reshape(-1)
            model_means = stacked[:, candidate_index, :].mean(axis=1)
            meta = candidate_meta.loc[candidate_id]
            support_row = support_comparison_table[
                (support_comparison_table["candidate_id"].astype(str) == candidate_id)
                & (support_comparison_table["parameter_scenario"] == scenario_name)
            ].iloc[0]
            summary_rows.append(
                {
                    "candidate_id": candidate_id,
                    "parameter_scenario": scenario_name,
                    "model_member_count": int(member_count),
                    "model_combination_rule": "paired_5_carry_5_lateral_by_member_index",
                    "simulation_count": int(values.size),
                    "mean_miss_distance_yd": float(np.mean(values)),
                    "median_miss_distance_yd": float(np.median(values)),
                    "p90_miss_distance_yd": float(np.quantile(values, 0.90)),
                    "p95_miss_distance_yd": float(np.quantile(values, 0.95)),
                    "worst_model_mean_miss_yd": float(np.max(model_means)),
                    "probability_within_3yd": float(np.mean(values <= 3.0)),
                    "probability_within_5yd": float(np.mean(values <= 5.0)),
                    "objective_prediction_std": float(np.std(model_means, ddof=1)),
                    "support_category": str(meta["support_category"]),
                    "objective_yd": float(meta["objective_yd"]),
                    "support_knn_distance": float(meta["support_knn_distance"]),
                    "decision_space_support": str(support_row["decision_space_support"]),
                    "full_model_input_support": str(support_row["full_model_input_support"]),
                    "out_of_support_fraction": float(support_row["out_of_support_fraction"]),
                }
            )
    return pd.DataFrame(detail_rows), pd.DataFrame(summary_rows)


def _candidate_with_metrics(base: pd.Series, metrics: pd.Series | dict[str, Any], *, candidate_type: str) -> dict[str, Any]:
    output = base.to_dict()
    for key, value in dict(metrics).items():
        if key not in output:
            output[key] = value
    output["candidate_type"] = candidate_type
    return output


def optimal_parameter_rows(
    candidates: pd.DataFrame,
    single_summary: pd.DataFrame,
    all_single_summary: pd.DataFrame,
    joint_summary: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    nominal = candidates.sort_values(["objective_yd", "support_knn_distance"]).iloc[0]
    tolerance = float(config["near_optimal_tolerance_yd"])

    stable_single = single_summary[single_summary["parameter_scenario"] == "stable_player"].copy()
    stable_single = stable_single.merge(
        candidates[["candidate_id", "objective_yd", "support_category", "support_knn_distance"]],
        on="candidate_id",
        how="left",
    )
    eligible_single = stable_single[
        (stable_single["support_category"] == "supported")
        & (stable_single["objective_yd"] <= float(nominal["objective_yd"]) + tolerance)
    ]
    if eligible_single.empty:
        raise RuntimeError("No eligible single-surrogate robust q3 candidate")
    single_metric = eligible_single.sort_values(["p90_miss_distance_yd", "objective_yd", "support_knn_distance"]).iloc[0]
    single_base = candidates[candidates["candidate_id"].astype(str) == str(single_metric["candidate_id"])].iloc[0]
    single_all = all_single_summary[all_single_summary["candidate_id"].astype(str) == str(single_metric["candidate_id"])].iloc[0]

    stable_joint = joint_summary[joint_summary["parameter_scenario"] == "stable_player"].copy()
    best_nominal = float(stable_joint["objective_yd"].min())
    eligible_joint = stable_joint[
        (stable_joint["support_category"] == "supported")
        & (stable_joint["objective_yd"] <= best_nominal + 0.5 + 1e-12)
        & (stable_joint["out_of_support_fraction"] <= 0.05 + 1e-12)
    ]
    if eligible_joint.empty:
        raise RuntimeError("No eligible joint robust q3 candidate")
    joint_metric = eligible_joint.sort_values(["p90_miss_distance_yd", "support_knn_distance", "candidate_id"]).iloc[0]
    joint_base = candidates[candidates["candidate_id"].astype(str) == str(joint_metric["candidate_id"])].iloc[0]

    nominal_metrics = all_single_summary[all_single_summary["candidate_id"].astype(str) == str(nominal["candidate_id"])]
    nominal_row = nominal.to_dict()
    nominal_row["candidate_type"] = "nominal_optimum"
    if not nominal_metrics.empty:
        nominal_row.update(nominal_metrics.iloc[0].to_dict())

    single_row = _candidate_with_metrics(
        single_base,
        {
            **single_metric.to_dict(),
            "single_surrogate_parameter_scenario": "stable_player",
            "single_surrogate_p90_miss_distance_yd": float(single_metric["p90_miss_distance_yd"]),
        },
        candidate_type="single_surrogate_robust_optimum",
    )
    legacy_row = _candidate_with_metrics(
        single_base,
        single_all.to_dict(),
        candidate_type="robust_recommended_optimum",
    )
    legacy_row["deprecated_by"] = "joint_robust_recommended_optimum"
    legacy_row["legacy_reason"] = "single_surrogate_parameter_robustness"

    joint_prefixed = {
        f"joint_{key}": value
        for key, value in joint_metric.to_dict().items()
        if key
        in {
            "mean_miss_distance_yd",
            "median_miss_distance_yd",
            "p90_miss_distance_yd",
            "p95_miss_distance_yd",
            "worst_model_mean_miss_yd",
            "probability_within_3yd",
            "probability_within_5yd",
            "objective_prediction_std",
            "simulation_count",
            "model_member_count",
        }
    }
    joint_row = _candidate_with_metrics(
        joint_base,
        {
            **joint_metric.to_dict(),
            **joint_prefixed,
            "joint_parameter_scenario": "stable_player",
            "joint_p90_miss_distance_yd": float(joint_metric["p90_miss_distance_yd"]),
        },
        candidate_type="joint_robust_recommended_optimum",
    )
    return pd.DataFrame([nominal_row, single_row, legacy_row, joint_row])


def model_crosscheck(
    candidates: pd.DataFrame,
    *,
    carry_models: list[Any],
    lateral_models: list[Any],
    apex_model: Any,
    config: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    base = candidates.drop_duplicates("candidate_id").copy()
    for candidate in base.itertuples(index=False):
        design = candidate_frame(
            [candidate.ball_speed_mph, candidate.launch_angle_deg, candidate.spin_rate_rpm, candidate.spin_axis_deg],
            launch_direction_deg=float(getattr(candidate, "launch_direction_deg", config["fixed_inputs"]["launch_direction_deg"])),
        )
        member_values = []
        for index, (carry_model, lateral_model) in enumerate(zip(carry_models, lateral_models, strict=True), start=1):
            pred = predict_landing(design, carry_model=carry_model, lateral_model=lateral_model, apex_model=apex_model)
            pred = add_objective_columns(
                pred,
                target_distance_yd=float(config["target"]["forward_distance_yd"]),
                target_lateral_yd=float(config["target"]["lateral_yd"]),
            ).iloc[0]
            member_values.append(pred)
            rows.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "candidate_type": getattr(candidate, "candidate_type", ""),
                    "carry_model_member": index,
                    "lateral_model_member": index,
                    "predicted_carry_yd": float(pred["predicted_carry_yd"]),
                    "predicted_lateral_yd": float(pred["predicted_lateral_yd"]),
                    "objective_yd": float(pred["objective_yd"]),
                }
            )
        carry_std = float(np.std([row["predicted_carry_yd"] for row in member_values], ddof=1))
        lateral_std = float(np.std([row["predicted_lateral_yd"] for row in member_values], ddof=1))
        objective_std = float(np.std([row["objective_yd"] for row in member_values], ddof=1))
        if objective_std <= float(config["uncertainty"]["stable_objective_std_yd"]):
            klass = "stable_across_models"
        elif objective_std <= float(config["uncertainty"]["moderate_objective_std_yd"]):
            klass = "moderately_model_sensitive"
        else:
            klass = "highly_model_sensitive"
        for row in rows[-len(member_values) :]:
            row["carry_prediction_std"] = carry_std
            row["lateral_prediction_std"] = lateral_std
            row["objective_prediction_std"] = objective_std
            row["model_sensitivity_class"] = klass
    return pd.DataFrame(rows)


def target_distance_sensitivity(target_optimal: pd.DataFrame) -> pd.DataFrame:
    return target_optimal.copy()


def near_optimal_parameter_ranges(
    candidates: pd.DataFrame,
    joint_summary: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    stable = joint_summary[joint_summary["parameter_scenario"] == "stable_player"].copy()
    if stable.empty:
        raise RuntimeError("Joint robustness summary lacks stable_player scenario")
    p90_cutoff = float(stable["p90_miss_distance_yd"].quantile(0.10))
    objective_cutoff = float(stable["objective_yd"].min()) + float(config["near_optimal_tolerance_yd"])
    selected_ids = set(
        stable[
            (stable["support_category"] == "supported")
            & ((stable["p90_miss_distance_yd"] <= p90_cutoff) | (stable["objective_yd"] <= objective_cutoff))
        ]["candidate_id"].astype(str)
    )
    subset = candidates[candidates["candidate_id"].astype(str).isin(selected_ids)].copy()
    if subset.empty:
        raise RuntimeError("No near-optimal supported candidates are available for parameter ranges")
    rounded_params = subset[VARIABLES].round(3)
    rounded_predictions = subset[["predicted_carry_yd", "predicted_lateral_yd"]].round(3)
    plateau_sizes = rounded_predictions.value_counts()
    diagnostics = {
        "distinct_parameter_count": int(len(rounded_params.drop_duplicates())),
        "distinct_prediction_pair_count": int(len(rounded_predictions.drop_duplicates())),
        "largest_prediction_plateau_size": int(plateau_sizes.max()),
    }
    diagnostics["solution_non_unique_under_surrogate"] = bool(
        diagnostics["distinct_parameter_count"] > diagnostics["distinct_prediction_pair_count"]
        or diagnostics["largest_prediction_plateau_size"] > 1
    )
    rows = []
    for variable in VARIABLES:
        series = subset[variable].astype(float)
        rows.append(
            {
                "variable": variable,
                "min": float(series.min()),
                "q10": float(series.quantile(0.10)),
                "median": float(series.median()),
                "q90": float(series.quantile(0.90)),
                "max": float(series.max()),
                **diagnostics,
            }
        )
    return pd.DataFrame(rows)
