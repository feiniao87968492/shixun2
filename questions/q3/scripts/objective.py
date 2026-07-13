from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from dependencies import LAUNCH_FEATURES
from support import SupportModel, evaluate_support


VARIABLES = ["ball_speed_mph", "launch_angle_deg", "spin_rate_rpm", "spin_axis_deg"]


def _unwrap_model(model: Any) -> Any:
    if isinstance(model, dict) and "model" in model:
        return model["model"]
    return model


def candidate_frame(
    values: pd.DataFrame | np.ndarray | list[float],
    *,
    launch_direction_deg: float | list[float] | np.ndarray | pd.Series = 0.0,
) -> pd.DataFrame:
    """Return a launch-feature frame for one or more candidate rows.

    `values` may contain only the four decision variables or all five launch
    features. When only four variables are provided, `launch_direction_deg` may
    be a scalar or one value per candidate.
    """
    if isinstance(values, pd.DataFrame):
        frame = values.copy()
        if set(LAUNCH_FEATURES).issubset(frame.columns):
            return frame[LAUNCH_FEATURES].astype(float)
        missing = set(VARIABLES).difference(frame.columns)
        if missing:
            raise ValueError(f"Candidate frame missing decision variables: {sorted(missing)}")
        frame = frame[VARIABLES].astype(float).copy()
    else:
        arr = np.asarray(values, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.shape[1] == len(LAUNCH_FEATURES):
            return pd.DataFrame(arr, columns=LAUNCH_FEATURES)[LAUNCH_FEATURES]
        if arr.shape[1] != len(VARIABLES):
            raise ValueError(
                f"Candidate values must have {len(VARIABLES)} decision columns or {len(LAUNCH_FEATURES)} launch columns"
            )
        frame = pd.DataFrame(arr, columns=VARIABLES)

    direction = np.asarray(launch_direction_deg, dtype=float)
    if direction.ndim == 0:
        direction_values = np.full(len(frame), float(direction), dtype=float)
    else:
        direction_values = direction.reshape(-1)
        if len(direction_values) != len(frame):
            raise ValueError("launch_direction_deg must be scalar or match the number of candidate rows")
    frame.insert(2, "launch_direction_deg", direction_values)
    return frame[LAUNCH_FEATURES]


def predict_landing(
    candidates: pd.DataFrame,
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
) -> pd.DataFrame:
    frame = candidates.copy()
    features = frame[LAUNCH_FEATURES]
    frame["predicted_carry_yd"] = _unwrap_model(carry_model).predict(features)
    frame["predicted_lateral_yd"] = _unwrap_model(lateral_model).predict(features)
    frame["predicted_apex_yd"] = _unwrap_model(apex_model).predict(features)
    return frame


def add_objective_columns(
    frame: pd.DataFrame,
    *,
    target_distance_yd: float,
    target_lateral_yd: float,
) -> pd.DataFrame:
    output = frame.copy()
    output["target_distance_yd"] = float(target_distance_yd)
    output["target_lateral_yd"] = float(target_lateral_yd)
    output["forward_error_yd"] = output["predicted_carry_yd"].astype(float) - float(target_distance_yd)
    output["lateral_error_yd"] = output["predicted_lateral_yd"].astype(float) - float(target_lateral_yd)
    output["objective_yd"] = np.sqrt(output["forward_error_yd"] ** 2 + output["lateral_error_yd"] ** 2)
    return output


def evaluate_candidates(
    candidates: pd.DataFrame,
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: SupportModel,
    target_distance_yd: float,
    target_lateral_yd: float,
) -> pd.DataFrame:
    predicted = predict_landing(
        candidates,
        carry_model=carry_model,
        lateral_model=lateral_model,
        apex_model=apex_model,
    )
    with_objective = add_objective_columns(
        predicted,
        target_distance_yd=target_distance_yd,
        target_lateral_yd=target_lateral_yd,
    )
    return evaluate_support(support_model, with_objective)
