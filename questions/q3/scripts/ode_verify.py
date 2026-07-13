from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
Q2_SCRIPT_DIR = ROOT / "questions" / "q2" / "scripts"
if str(Q2_SCRIPT_DIR) not in sys.path:
    sys.path.append(str(Q2_SCRIPT_DIR))

from ode_model import PhysicalConstants, simulate_shot  # type: ignore  # noqa: E402


def _candidate_series(row: pd.Series) -> pd.Series:
    return pd.Series(
        {
            "ball_speed_mph": float(row["ball_speed_mph"]),
            "launch_angle_deg": float(row["launch_angle_deg"]),
            "launch_direction_deg": float(row.get("launch_direction_deg", 0.0)),
            "spin_rate_rpm": float(row["spin_rate_rpm"]),
            "spin_axis_deg": float(row["spin_axis_deg"]),
        }
    )


def _params_for_model(q2_parameters: dict[str, Any], model: str) -> dict[str, float]:
    params = q2_parameters["model_parameters"][model]
    return {
        "cd": float(params.get("cd", 0.0)),
        "cl": float(params.get("cl", 0.0)),
        "lift_scale": float(params.get("lift_scale", 0.0)),
    }


def run_ode_crosscheck(
    candidates: pd.DataFrame,
    *,
    full_config: dict[str, Any],
    q2_parameters: dict[str, Any],
    q2_metadata: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    q2_config = full_config["q2"]
    q3_config = full_config["q3"]
    constants = PhysicalConstants.from_config(q2_config["physics"])
    solver = q2_config["ode"]["solver"]
    carry_definition = str(q2_parameters.get("carry_definition", q2_config["ode"]["carry_definition"]))
    side_sign = int(q2_parameters.get("side_spin_sign", q2_metadata.get("side_spin_sign", 1)))
    models = [model for model in q3_config["ode_verification"]["models"] if model in q2_parameters["model_parameters"]]

    rows = []
    trajectory_frames = []
    robust_id = candidates.loc[candidates["candidate_type"] == "robust_recommended_optimum", "candidate_id"].iloc[0]
    for _, candidate in candidates.iterrows():
        row = _candidate_series(candidate)
        for model in models:
            params = _params_for_model(q2_parameters, model)
            pred, trajectory = simulate_shot(
                row,
                model=model,
                constants=constants,
                solver=solver,
                carry_definition=carry_definition,
                cd=params["cd"],
                cl=params["cl"],
                lift_scale=params["lift_scale"],
                side_sign=side_sign,
                keep_trajectory=str(candidate["candidate_id"]) == str(robust_id),
            )
            rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_type": candidate["candidate_type"],
                    "model": model,
                    "predicted_x_carry_yd": pred["predicted_x_carry_yd"],
                    "predicted_radial_carry_yd": pred["predicted_radial_carry_yd"],
                    "predicted_lateral_yd": pred["predicted_lateral_yd"],
                    "predicted_apex_yd": pred["predicted_apex_yd"],
                    "flight_time_s": pred["flight_time_s"],
                    "integration_status": pred["integration_status"],
                    "supervised_carry_yd": candidate.get("predicted_carry_yd", float("nan")),
                    "supervised_lateral_yd": candidate.get("predicted_lateral_yd", float("nan")),
                    "delta_carry_sup_minus_ode_yd": candidate.get("predicted_carry_yd", float("nan"))
                    - pred["predicted_x_carry_yd"],
                    "delta_lateral_sup_minus_ode_yd": candidate.get("predicted_lateral_yd", float("nan"))
                    - pred["predicted_lateral_yd"],
                    "q2_parameter_git_commit": q2_metadata.get("git_commit", "unknown"),
                    "q2_carry_definition": carry_definition,
                    "provisional": False,
                    "verification_claim": "ODE crosscheck only; not real-shot experimental validation",
                }
            )
            if str(candidate["candidate_id"]) == str(robust_id):
                trajectory = trajectory.copy()
                trajectory.insert(0, "model", model)
                trajectory.insert(0, "candidate_id", candidate["candidate_id"])
                trajectory.insert(1, "candidate_type", candidate["candidate_type"])
                trajectory_frames.append(trajectory)
    trajectory_output = pd.concat(trajectory_frames, ignore_index=True) if trajectory_frames else pd.DataFrame()
    return pd.DataFrame(rows), trajectory_output
