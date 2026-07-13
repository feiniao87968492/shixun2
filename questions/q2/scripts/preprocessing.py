from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


TARGETS = ["carry_distance_yd", "apex_height_yd"]
ODE_REQUIRED_FEATURES = [
    "ball_speed_mph",
    "launch_angle_deg",
    "launch_direction_deg",
    "spin_rate_rpm",
    "spin_axis_deg",
]
CALIBRATION_COVERAGE_FEATURES = [
    "ball_speed_mph",
    "launch_angle_deg",
    "spin_rate_rpm",
    "carry_distance_yd",
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


def select_calibration_records(
    train: pd.DataFrame,
    *,
    required_features: list[str],
    representative_count: int,
    calibration_type: str,
    random_seed: int,
) -> pd.DataFrame:
    frame = train.dropna(subset=[*required_features, *TARGETS]).copy()
    frame = frame.sort_values("record_id").reset_index(drop=True)
    if frame.empty:
        raise ValueError(f"No complete records are available for {calibration_type} calibration")

    coverage_features = [feature for feature in CALIBRATION_COVERAGE_FEATURES if feature in frame.columns]
    if len(frame) <= int(representative_count):
        selected = frame.copy()
        selected["cluster_or_stratum"] = [f"all_{index:03d}" for index in range(len(selected))]
    else:
        matrix = StandardScaler().fit_transform(frame[coverage_features].to_numpy(dtype=float))
        cluster_count = min(int(representative_count), len(frame))
        kmeans = KMeans(n_clusters=cluster_count, random_state=int(random_seed), n_init=20)
        labels = kmeans.fit_predict(matrix)
        selected_positions: list[int] = []
        selected_position_set: set[int] = set()
        cluster_labels: dict[int, str] = {}
        for cluster_id in range(cluster_count):
            member_positions = np.flatnonzero(labels == cluster_id)
            if len(member_positions) == 0:
                continue
            distances = np.linalg.norm(matrix[member_positions] - kmeans.cluster_centers_[cluster_id], axis=1)
            member_frame = pd.DataFrame(
                {
                    "position": member_positions,
                    "distance": distances,
                    "record_id": frame.iloc[member_positions]["record_id"].to_numpy(dtype=int),
                }
            ).sort_values(["distance", "record_id"])
            for candidate_position in member_frame["position"].astype(int):
                if candidate_position not in selected_position_set:
                    selected_positions.append(candidate_position)
                    selected_position_set.add(candidate_position)
                    cluster_labels[int(candidate_position)] = f"cluster_{cluster_id:03d}"
                    break

        if len(selected_positions) < int(representative_count):
            center_distances = np.min(
                np.linalg.norm(matrix[:, None, :] - kmeans.cluster_centers_[None, :, :], axis=2),
                axis=1,
            )
            fallback = pd.DataFrame(
                {
                    "position": np.arange(len(frame)),
                    "distance": center_distances,
                    "record_id": frame["record_id"].to_numpy(dtype=int),
                }
            ).sort_values(["distance", "record_id"])
            for candidate_position in fallback["position"].astype(int):
                if len(selected_positions) >= int(representative_count):
                    break
                if candidate_position not in selected_position_set:
                    selected_positions.append(candidate_position)
                    selected_position_set.add(candidate_position)
                    cluster_labels[int(candidate_position)] = f"fallback_{len(selected_positions) - 1:03d}"

        selected = frame.iloc[selected_positions].copy()
        selected["cluster_or_stratum"] = [
            cluster_labels[int(position)] for position in selected_positions
        ]

    selected.insert(1, "calibration_type", calibration_type)
    columns = [
        "record_id",
        "calibration_type",
        "cluster_or_stratum",
        "ball_speed_mph",
        "launch_angle_deg",
        "spin_rate_rpm",
        "spin_axis_deg",
        "carry_distance_yd",
        "apex_height_yd",
        *[feature for feature in required_features if feature not in {
            "ball_speed_mph",
            "launch_angle_deg",
            "spin_rate_rpm",
            "spin_axis_deg",
        }],
    ]
    if "lateral_offset_yd" in selected.columns:
        columns.append("lateral_offset_yd")
    return selected[columns].sort_values("record_id").reset_index(drop=True)


def select_drag_calibration_records(
    train: pd.DataFrame,
    *,
    required_features: list[str],
    representative_count: int,
) -> pd.DataFrame:
    return select_calibration_records(
        train,
        required_features=required_features,
        representative_count=representative_count,
        calibration_type="drag",
        random_seed=2026,
    )


def select_typical_records(
    test: pd.DataFrame,
    *,
    required_features: list[str],
    target_distances_yd: list[int] | None = None,
) -> pd.DataFrame:
    """Select deterministic typical records from the fixed test split only."""
    if target_distances_yd is None:
        target_distances_yd = [100, 150, 200]
    frame = test.dropna(
        subset=[*required_features, "carry_distance_yd", "apex_height_yd", "lateral_offset_yd"]
    ).copy()
    if frame.empty:
        raise ValueError("No complete test records are available for q2 typical trajectory selection")

    rows = []
    used_ids: set[int] = set()
    for target in target_distances_yd:
        candidates = frame.copy()
        candidates["distance_to_target_yd"] = (candidates["carry_distance_yd"] - float(target)).abs()
        candidates = candidates.sort_values(["distance_to_target_yd", "record_id"])
        selected = None
        for _, candidate in candidates.iterrows():
            candidate_id = int(candidate["record_id"])
            if candidate_id not in used_ids:
                selected = candidate
                used_ids.add(candidate_id)
                break
        if selected is None:
            selected = candidates.iloc[0]
        rows.append(
            {
                "target_distance_yd": int(target),
                "target_group": f"{int(target)}yd",
                "sample_id": int(selected["record_id"]),
                "record_id": int(selected["record_id"]),
                "actual_carry_yd": float(selected["carry_distance_yd"]),
                "distance_to_target_yd": float(abs(selected["carry_distance_yd"] - float(target))),
                "ball_speed_mph": float(selected["ball_speed_mph"]),
                "launch_angle_deg": float(selected["launch_angle_deg"]),
                "launch_direction_deg": float(selected["launch_direction_deg"]),
                "spin_rate_rpm": float(selected["spin_rate_rpm"]),
                "spin_axis_deg": float(selected["spin_axis_deg"]),
            }
        )
    return pd.DataFrame(rows)
