from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split


TARGETS = ["carry_distance_yd", "apex_height_yd"]
ODE_REQUIRED_FEATURES = [
    "ball_speed_mph",
    "launch_angle_deg",
    "launch_direction_deg",
    "spin_rate_rpm",
    "spin_axis_deg",
]


def mph_to_mps(value: float) -> float:
    return float(value) * 0.44704


def rpm_to_rad_s(value: float) -> float:
    return float(value) * 2.0 * math.pi / 60.0


def yd_to_m(value: float) -> float:
    return float(value) * 0.9144


def m_to_yd(value: float) -> float:
    return float(value) / 0.9144


def load_project_config(root: Path, config_path: str | Path) -> dict[str, Any]:
    path = root / config_path
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if "q2" not in config:
        raise KeyError("configs/default.yaml must define q2")
    return config["q2"]


def load_clean_data(root: Path, config: dict[str, Any]) -> pd.DataFrame:
    path = root / config["input_path"]
    if not path.exists():
        raise FileNotFoundError(f"q2 input data missing: {path}")
    data = pd.read_csv(path)
    if "apex_height_yd" not in data.columns and "max_height_yd" in data.columns:
        data["apex_height_yd"] = data["max_height_yd"]
    required = {"record_id", *TARGETS, *ODE_REQUIRED_FEATURES}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"q2 input data missing columns: {sorted(missing)}")
    return data


def fixed_train_test_split(clean: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    seed = int(config["random_seed"])
    test_size = float(config["split"]["test_size"])
    train_ids, test_ids = train_test_split(
        clean["record_id"].astype(int).to_numpy(),
        test_size=test_size,
        random_state=seed,
        shuffle=True,
    )
    rows = [
        {"record_id": int(record_id), "split": "train", "random_seed": seed}
        for record_id in train_ids
    ]
    rows.extend(
        {"record_id": int(record_id), "split": "test", "random_seed": seed}
        for record_id in test_ids
    )
    return pd.DataFrame(rows).sort_values("record_id").reset_index(drop=True)


def split_frames(clean: pd.DataFrame, split: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_ids = set(split.loc[split["split"] == "train", "record_id"].astype(int))
    test_ids = set(split.loc[split["split"] == "test", "record_id"].astype(int))
    if train_ids & test_ids:
        raise ValueError("train/test split contains overlapping record_id values")
    train = clean[clean["record_id"].astype(int).isin(train_ids)].copy()
    test = clean[clean["record_id"].astype(int).isin(test_ids)].copy()
    return train.reset_index(drop=True), test.reset_index(drop=True)


def spin_geometry_check(clean: pd.DataFrame) -> pd.DataFrame:
    frame = clean.dropna(subset=["spin_rate_rpm", "spin_axis_deg", "backspin_rpm", "sidespin_rpm"])
    angle = np.deg2rad(frame["spin_axis_deg"].to_numpy(dtype=float))
    spin_rate = frame["spin_rate_rpm"].to_numpy(dtype=float)
    observed_backspin = frame["backspin_rpm"].to_numpy(dtype=float)
    observed_sidespin = frame["sidespin_rpm"].to_numpy(dtype=float)
    predicted_backspin = spin_rate * np.cos(angle)
    predicted_sidespin_positive = spin_rate * np.sin(angle)
    predicted_sidespin_negative = -spin_rate * np.sin(angle)

    def mean_abs_error(predicted: np.ndarray, observed: np.ndarray) -> float:
        return float(np.mean(np.abs(predicted - observed)))

    positive_mae = mean_abs_error(predicted_sidespin_positive, observed_sidespin)
    negative_mae = mean_abs_error(predicted_sidespin_negative, observed_sidespin)
    selected_sign = 1 if positive_mae <= negative_mae else -1
    return pd.DataFrame(
        [
            {
                "relationship": "backspin = spin_rate * cos(spin_axis)",
                "selected_sign": "",
                "mean_absolute_error_rpm": mean_abs_error(predicted_backspin, observed_backspin),
                "n": int(len(frame)),
                "notes": "Backspin geometry check.",
            },
            {
                "relationship": "sidespin = + spin_rate * sin(spin_axis)",
                "selected_sign": 1,
                "mean_absolute_error_rpm": positive_mae,
                "n": int(len(frame)),
                "notes": "Candidate side-spin sign.",
            },
            {
                "relationship": "sidespin = - spin_rate * sin(spin_axis)",
                "selected_sign": -1,
                "mean_absolute_error_rpm": negative_mae,
                "n": int(len(frame)),
                "notes": "Candidate side-spin sign.",
            },
            {
                "relationship": "selected_sidespin_sign",
                "selected_sign": selected_sign,
                "mean_absolute_error_rpm": min(positive_mae, negative_mae),
                "n": int(len(frame)),
                "notes": "Sign with lower observed sidespin reconstruction error.",
            },
        ]
    )


def select_drag_calibration_records(
    train: pd.DataFrame,
    *,
    required_features: list[str],
    representative_count: int,
) -> pd.DataFrame:
    frame = train.dropna(subset=[*required_features, *TARGETS]).sort_values("carry_distance_yd")
    if len(frame) <= representative_count:
        selected = frame
    else:
        positions = np.linspace(0, len(frame) - 1, representative_count).round().astype(int)
        selected = frame.iloc[np.unique(positions)]
    return selected[["record_id", "carry_distance_yd", "apex_height_yd", *required_features]].reset_index(drop=True)
