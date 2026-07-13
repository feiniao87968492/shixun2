from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution
from scipy.stats import qmc

from objective import VARIABLES, candidate_frame, evaluate_candidates
from support import SupportModel


def bounds_from_config(config: dict[str, Any]) -> list[tuple[float, float]]:
    return [
        (float(config["variables"][name]["lower"]), float(config["variables"][name]["upper"]))
        for name in VARIABLES
    ]


def _lhs(bounds: list[tuple[float, float]], n: int, *, seed: int) -> pd.DataFrame:
    sampler = qmc.LatinHypercube(d=len(bounds), seed=int(seed))
    unit = sampler.random(n=int(n))
    lower = np.asarray([item[0] for item in bounds], dtype=float)
    upper = np.asarray([item[1] for item in bounds], dtype=float)
    values = lower + unit * (upper - lower)
    frame = pd.DataFrame(values, columns=VARIABLES)
    frame.insert(2, "launch_direction_deg", 0.0)
    return frame


def _target(config: dict[str, Any]) -> tuple[float, float]:
    return float(config["target"]["forward_distance_yd"]), float(config["target"]["lateral_yd"])


def best_observed_baseline(train: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    target_distance, target_lateral = _target(config)
    frame = train.copy()
    frame["observed_forward_error_yd"] = frame["carry_distance_yd"].astype(float) - target_distance
    frame["observed_lateral_error_yd"] = frame["lateral_offset_yd"].astype(float) - target_lateral
    frame["observed_objective_yd"] = np.sqrt(
        frame["observed_forward_error_yd"] ** 2 + frame["observed_lateral_error_yd"] ** 2
    )
    best = frame.sort_values(["observed_objective_yd", "record_id"]).iloc[0]
    return pd.DataFrame(
        [
            {
                "candidate_id": f"observed_{int(best['record_id'])}",
                "candidate_type": "best_observed_baseline",
                "record_id": int(best["record_id"]),
                "ball_speed_mph": float(best["ball_speed_mph"]),
                "launch_angle_deg": float(best["launch_angle_deg"]),
                "launch_direction_deg": float(best["launch_direction_deg"]),
                "spin_rate_rpm": float(best["spin_rate_rpm"]),
                "spin_axis_deg": float(best["spin_axis_deg"]),
                "observed_carry_yd": float(best["carry_distance_yd"]),
                "observed_lateral_yd": float(best["lateral_offset_yd"]),
                "observed_objective_yd": float(best["observed_objective_yd"]),
                "source": "q2 fixed train split actual record",
            }
        ]
    )


def evaluate_designs(
    designs: pd.DataFrame,
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: SupportModel,
    config: dict[str, Any],
) -> pd.DataFrame:
    target_distance, target_lateral = _target(config)
    return evaluate_candidates(
        designs,
        carry_model=carry_model,
        lateral_model=lateral_model,
        apex_model=apex_model,
        support_model=support_model,
        target_distance_yd=target_distance,
        target_lateral_yd=target_lateral,
    )


def sampling_baseline(
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: SupportModel,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sample_count = int(config["baseline"]["sample_count"])
    seed = int(config["random_seed"])
    candidates = _lhs(bounds_from_config(config), sample_count, seed=seed + 301)
    evaluated = evaluate_designs(
        candidates,
        carry_model=carry_model,
        lateral_model=lateral_model,
        apex_model=apex_model,
        support_model=support_model,
        config=config,
    )
    evaluated["source"] = str(config["baseline"].get("method", "lhs"))
    evaluated["sample_count"] = sample_count
    evaluated["candidate_id"] = [f"sampling_{idx:06d}" for idx in range(len(evaluated))]
    top = evaluated.sort_values(["objective_yd", "support_knn_distance"]).head(100).copy()
    top["rank"] = np.arange(1, len(top) + 1)
    return top.reset_index(drop=True), evaluated.reset_index(drop=True)


def differential_evolution_runs(
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: SupportModel,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bounds = bounds_from_config(config)
    de_config = config["differential_evolution"]
    run_rows = []
    candidate_rows = []

    def score(values: np.ndarray) -> float | np.ndarray:
        arr = np.asarray(values, dtype=float)
        if arr.ndim == 2:
            arr = arr.T
        else:
            arr = arr.reshape(1, -1)
        evaluated = evaluate_designs(
            candidate_frame(arr, launch_direction_deg=float(config["fixed_inputs"]["launch_direction_deg"])),
            carry_model=carry_model,
            lateral_model=lateral_model,
            apex_model=apex_model,
            support_model=support_model,
            config=config,
        )
        values_out = evaluated["objective_yd"].to_numpy(dtype=float)
        return float(values_out[0]) if len(values_out) == 1 else values_out

    for seed in de_config["seeds"]:
        result = differential_evolution(
            score,
            bounds=bounds,
            strategy=str(de_config["strategy"]),
            maxiter=int(de_config["max_iterations"]),
            popsize=int(de_config["population_size"]),
            tol=float(de_config["tolerance"]),
            seed=int(seed),
            workers=int(de_config.get("workers", 1)),
            polish=bool(de_config.get("polish", False)),
            updating="deferred",
            vectorized=True,
        )
        evaluated = evaluate_designs(
            candidate_frame(result.x, launch_direction_deg=float(config["fixed_inputs"]["launch_direction_deg"])),
            carry_model=carry_model,
            lateral_model=lateral_model,
            apex_model=apex_model,
            support_model=support_model,
            config=config,
        ).iloc[0]
        candidate_id = f"de_seed_{int(seed)}"
        candidate = evaluated.to_dict()
        candidate.update({"candidate_id": candidate_id, "source": "differential_evolution", "seed": int(seed)})
        candidate_rows.append(candidate)
        finite_objective = bool(np.isfinite(float(evaluated["objective_yd"])))
        run_rows.append(
            {
                "seed": int(seed),
                "success": finite_objective,
                "scipy_success": bool(result.success),
                "message": str(result.message),
                "objective_yd": float(evaluated["objective_yd"]),
                "ball_speed_mph": float(evaluated["ball_speed_mph"]),
                "launch_angle_deg": float(evaluated["launch_angle_deg"]),
                "launch_direction_deg": float(evaluated["launch_direction_deg"]),
                "spin_rate_rpm": float(evaluated["spin_rate_rpm"]),
                "spin_axis_deg": float(evaluated["spin_axis_deg"]),
                "predicted_carry_yd": float(evaluated["predicted_carry_yd"]),
                "predicted_lateral_yd": float(evaluated["predicted_lateral_yd"]),
                "support_category": str(evaluated["support_category"]),
                "support_knn_distance": float(evaluated["support_knn_distance"]),
                "iterations": int(getattr(result, "nit", 0)),
                "function_evaluations": int(getattr(result, "nfev", 0)),
                "candidate_id": candidate_id,
                "local_refinement_samples": int(config["local_refinement"]["sample_count"]),
            }
        )
    return pd.DataFrame(run_rows), pd.DataFrame(candidate_rows)


def local_refinement(
    runs: pd.DataFrame,
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: SupportModel,
    config: dict[str, Any],
) -> pd.DataFrame:
    sample_count = int(config["local_refinement"]["sample_count"])
    half_widths = {
        "ball_speed_mph": float(config["local_refinement"]["ball_speed_half_width_mph"]),
        "launch_angle_deg": float(config["local_refinement"]["launch_angle_half_width_deg"]),
        "spin_rate_rpm": float(config["local_refinement"]["spin_rate_half_width_rpm"]),
        "spin_axis_deg": float(config["local_refinement"]["spin_axis_half_width_deg"]),
    }
    global_bounds = dict(zip(VARIABLES, bounds_from_config(config), strict=True))
    frames = []
    for run in runs.itertuples(index=False):
        local_bounds = []
        for variable in VARIABLES:
            low, high = global_bounds[variable]
            center = float(getattr(run, variable))
            width = half_widths[variable]
            local_bounds.append((max(low, center - width), min(high, center + width)))
        designs = _lhs(local_bounds, sample_count, seed=int(run.seed) + 401)
        evaluated = evaluate_designs(
            designs,
            carry_model=carry_model,
            lateral_model=lateral_model,
            apex_model=apex_model,
            support_model=support_model,
            config=config,
        )
        evaluated["source"] = "local_refinement"
        evaluated["seed"] = int(run.seed)
        evaluated["candidate_id"] = [f"local_{int(run.seed)}_{idx:05d}" for idx in range(len(evaluated))]
        frames.append(evaluated)
    return pd.concat(frames, ignore_index=True)


def top_candidates(*frames: pd.DataFrame, limit: int = 500) -> pd.DataFrame:
    combined = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True, sort=False)
    combined = combined.sort_values(["objective_yd", "support_knn_distance"]).drop_duplicates(
        subset=["ball_speed_mph", "launch_angle_deg", "spin_rate_rpm", "spin_axis_deg"],
        keep="first",
    )
    top = combined.head(int(limit)).copy()
    top["rank"] = np.arange(1, len(top) + 1)
    return top.reset_index(drop=True)
