from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from objective import VARIABLES, add_objective_columns, candidate_frame, evaluate_candidates, predict_landing
from support import SupportModel


def near_optimal_candidates(candidates: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    nominal = candidates.sort_values(["objective_yd", "support_knn_distance"]).iloc[0]
    tolerance = float(config["near_optimal_tolerance_yd"])
    near = candidates[candidates["objective_yd"] <= float(nominal["objective_yd"]) + tolerance].copy()
    if near.empty:
        near = candidates.head(1).copy()
    supported = near[near["support_category"] == "supported"].copy()
    if supported.empty:
        supported = candidates[candidates["support_category"] == "supported"].head(1).copy()
    selected = pd.concat([near.head(1), supported.sort_values(["objective_yd", "support_knn_distance"]).head(12)])
    return selected.drop_duplicates("candidate_id").reset_index(drop=True)


def simulate_parameter_robustness(
    candidate_rows: pd.DataFrame,
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: SupportModel,
    config: dict[str, Any],
) -> pd.DataFrame:
    perturb = config["perturbation"]
    simulations = int(perturb["simulations"])
    rng = np.random.default_rng(int(config["random_seed"]) + 701)
    bounds = {name: config["variables"][name] for name in VARIABLES}
    rows = []
    for candidate in candidate_rows.itertuples(index=False):
        base = np.asarray([float(getattr(candidate, name)) for name in VARIABLES], dtype=float)
        noise = np.column_stack(
            [
                rng.normal(0.0, float(perturb["ball_speed_sd_mph"]), simulations),
                rng.normal(0.0, float(perturb["launch_angle_sd_deg"]), simulations),
                rng.normal(0.0, float(perturb["spin_rate_sd_rpm"]), simulations),
                rng.normal(0.0, float(perturb["spin_axis_sd_deg"]), simulations),
            ]
        )
        values = base + noise
        for index, variable in enumerate(VARIABLES):
            values[:, index] = np.clip(
                values[:, index],
                float(bounds[variable]["lower"]),
                float(bounds[variable]["upper"]),
            )
        designs = candidate_frame(values, launch_direction_deg=float(config["fixed_inputs"]["launch_direction_deg"]))
        evaluated = evaluate_candidates(
            designs,
            carry_model=carry_model,
            lateral_model=lateral_model,
            apex_model=apex_model,
            support_model=support_model,
            target_distance_yd=float(config["target"]["forward_distance_yd"]),
            target_lateral_yd=float(config["target"]["lateral_yd"]),
        )
        evaluated["candidate_id"] = str(candidate.candidate_id)
        evaluated["base_candidate_source"] = str(getattr(candidate, "source", ""))
        evaluated["simulation_index"] = np.arange(1, len(evaluated) + 1)
        evaluated["miss_distance_yd"] = evaluated["objective_yd"]
        rows.append(evaluated)
    return pd.concat(rows, ignore_index=True)


def robustness_summary(details: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for candidate_id, subset in details.groupby("candidate_id"):
        miss = subset["miss_distance_yd"].to_numpy(dtype=float)
        rows.append(
            {
                "candidate_id": candidate_id,
                "mean_miss_distance_yd": float(np.mean(miss)),
                "median_miss_distance_yd": float(np.median(miss)),
                "p90_miss_distance_yd": float(np.quantile(miss, 0.90)),
                "maximum_miss_distance_yd": float(np.max(miss)),
                "probability_within_3yd": float(np.mean(miss <= 3.0)),
                "probability_within_5yd": float(np.mean(miss <= 5.0)),
                "simulations": int(len(subset)),
            }
        )
    return pd.DataFrame(rows)


def optimal_parameter_rows(
    candidates: pd.DataFrame,
    robustness: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    nominal = candidates.sort_values(["objective_yd", "support_knn_distance"]).iloc[0].to_dict()
    tolerance = float(config["near_optimal_tolerance_yd"])
    near = candidates[candidates["objective_yd"] <= float(nominal["objective_yd"]) + tolerance].copy()
    robust_pool = near[near["support_category"] == "supported"].merge(robustness, on="candidate_id", how="inner")
    if robust_pool.empty:
        raise RuntimeError("No supported near-optimal q3 candidate is available for robust recommendation")
    robust = robust_pool.sort_values(["p90_miss_distance_yd", "objective_yd", "support_knn_distance"]).iloc[0].to_dict()

    rows = []
    for candidate_type, row in [("nominal_optimum", nominal), ("robust_recommended_optimum", robust)]:
        output = dict(row)
        output["candidate_type"] = candidate_type
        if candidate_type == "nominal_optimum":
            match = robustness[robustness["candidate_id"] == row["candidate_id"]]
            if not match.empty:
                output.update(match.iloc[0].to_dict())
        rows.append(output)
    return pd.DataFrame(rows)


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
            launch_direction_deg=float(config["fixed_inputs"]["launch_direction_deg"]),
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


def target_distance_sensitivity(candidates: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for target in config["target_distance_sensitivity_yd"]:
        frame = add_objective_columns(
            candidates,
            target_distance_yd=float(target),
            target_lateral_yd=float(config["target"]["lateral_yd"]),
        )
        for label, subset in [
            ("best_hard_bounds", frame),
            ("best_supported", frame[frame["support_category"] == "supported"]),
        ]:
            if subset.empty:
                continue
            row = subset.sort_values(["objective_yd", "support_knn_distance"]).iloc[0]
            rows.append(
                {
                    "target_distance_yd": float(target),
                    "solution_type": label,
                    "candidate_id": row["candidate_id"],
                    "ball_speed_mph": float(row["ball_speed_mph"]),
                    "launch_angle_deg": float(row["launch_angle_deg"]),
                    "spin_rate_rpm": float(row["spin_rate_rpm"]),
                    "spin_axis_deg": float(row["spin_axis_deg"]),
                    "predicted_carry_yd": float(row["predicted_carry_yd"]),
                    "predicted_lateral_yd": float(row["predicted_lateral_yd"]),
                    "objective_yd": float(row["objective_yd"]),
                    "support_category": row["support_category"],
                }
            )
    return pd.DataFrame(rows)
