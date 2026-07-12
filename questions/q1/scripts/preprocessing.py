#!/usr/bin/env python3
"""Q1 data loading, schema validation, zero correction, and sample definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RAW_RELATIVE_PATH = Path("data/raw/problem/附件（实训题2）.xlsx")
SHEET_NAME = "高尔夫球实测数据"

RAW_TO_CANONICAL = {
    "序号": "record_id",
    "球速(mph)": "ball_speed_mph",
    "发射角(度)": "launch_angle_deg",
    "发射方向(度)": "launch_direction_deg",
    "自旋速率(rpm)": "spin_rate_rpm",
    "自旋轴偏角(度)": "spin_axis_deg",
    "后旋(rpm)": "backspin_rpm",
    "侧旋(rpm)": "sidespin_rpm",
    "杆头速度(mph)": "club_speed_mph",
    "攻击角(度)": "attack_angle_deg",
    "飞行距离(yd)": "carry_distance_yd",
    "最高点高度(yd)": "max_height_yd",
    "总距离(yd)": "total_distance_yd",
    "横向偏移(yd)": "lateral_offset_yd",
}

INPUT_FEATURES = [
    "ball_speed_mph",
    "launch_angle_deg",
    "launch_direction_deg",
    "spin_rate_rpm",
    "spin_axis_deg",
    "backspin_rpm",
    "sidespin_rpm",
    "club_speed_mph",
    "attack_angle_deg",
]
PRIMARY_FEATURES = [
    "ball_speed_mph",
    "launch_angle_deg",
    "launch_direction_deg",
    "spin_rate_rpm",
    "spin_axis_deg",
    "club_speed_mph",
    "attack_angle_deg",
]
SPIN_COMPONENT_FEATURES = [
    "ball_speed_mph",
    "launch_angle_deg",
    "launch_direction_deg",
    "backspin_rpm",
    "sidespin_rpm",
    "club_speed_mph",
    "attack_angle_deg",
]
CORE_FEATURES = [
    "ball_speed_mph",
    "launch_angle_deg",
    "launch_direction_deg",
    "spin_rate_rpm",
    "spin_axis_deg",
]
OUTPUT_COLUMNS = [
    "carry_distance_yd",
    "max_height_yd",
    "total_distance_yd",
    "lateral_offset_yd",
]
TARGET = "carry_distance_yd"
MISSING_INDICATORS = ["club_speed_missing", "attack_angle_missing"]
INVALID_ZERO_RULES = {
    "club_speed_mph": "club_speed_invalid_zero",
    "attack_angle_deg": "attack_angle_invalid_zero",
}


class AnalysisDataset:
    def __init__(self, name: str, frame: pd.DataFrame, features: list[str], description: str):
        self.name = name
        self.frame = frame
        self.features = features
        self.description = description


def canonicalize_golf_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Rename raw Chinese fields, coerce numerics, sort by sample id, and validate ids."""
    missing = [column for column in RAW_TO_CANONICAL if column not in raw.columns]
    if missing:
        raise ValueError(f"Missing expected raw columns: {missing}")

    clean = raw.rename(columns=RAW_TO_CANONICAL)[list(RAW_TO_CANONICAL.values())].copy()
    for column in clean.columns:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    clean = clean.dropna(subset=["record_id"]).copy()
    clean["record_id"] = clean["record_id"].astype(int)
    clean = clean.sort_values("record_id").reset_index(drop=True)
    validate_schema(clean)
    return clean


def load_data(root: str | Path, config: dict[str, Any] | None = None) -> pd.DataFrame:
    """Load the raw Excel attachment and return canonical columns before zero correction."""
    del config
    path = Path(root) / RAW_RELATIVE_PATH
    if not path.exists():
        raise FileNotFoundError(f"Raw Excel attachment not found: {path}")
    raw = pd.read_excel(path, sheet_name=SHEET_NAME, header=2, na_values=[""])
    return canonicalize_golf_data(raw)


def validate_schema(frame: pd.DataFrame) -> None:
    required = ["record_id", *INPUT_FEATURES, *OUTPUT_COLUMNS]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing canonical columns: {missing}")
    if frame["record_id"].duplicated().any():
        duplicates = frame.loc[frame["record_id"].duplicated(), "record_id"].tolist()
        raise ValueError(f"Duplicate record_id values: {duplicates[:10]}")
    numeric = frame[required].drop(columns=["record_id"])
    if np.isinf(numeric.to_numpy(dtype=float)).any():
        raise ValueError("Infinite values found in q1 numeric fields")


def replace_invalid_zero_values(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Treat confirmed impossible zero club speed and attack angle values as missing."""
    clean = frame.copy()
    validate_schema(clean)
    masks = {column: clean[column].eq(0).fillna(False) for column in INVALID_ZERO_RULES}
    any_mask = pd.concat(masks.values(), axis=1).any(axis=1)
    audit_cols = [
        "record_id",
        "ball_speed_mph",
        "carry_distance_yd",
        "club_speed_mph",
        "attack_angle_deg",
    ]
    records = clean.loc[any_mask, audit_cols].copy()
    for column, flag_name in INVALID_ZERO_RULES.items():
        records[flag_name] = masks[column].loc[any_mask].astype(int).to_numpy()
        clean.loc[masks[column], column] = np.nan
    records["correction"] = "zero_to_nan"
    return clean, records.sort_values("record_id").reset_index(drop=True)


def add_missing_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["club_speed_missing"] = out["club_speed_mph"].isna().astype(int)
    out["attack_angle_missing"] = out["attack_angle_deg"].isna().astype(int)
    return out


def build_analysis_datasets(clean: pd.DataFrame) -> dict[str, AnalysisDataset]:
    """Build S1/S2/S3 and spin-representation datasets without global imputation."""
    validate_schema(clean)
    s1 = clean.dropna(subset=CORE_FEATURES + [TARGET]).copy()
    s2 = clean.dropna(subset=PRIMARY_FEATURES + [TARGET]).copy()
    s3 = add_missing_indicators(clean).dropna(subset=CORE_FEATURES + [TARGET]).copy()
    s3_spin_components = add_missing_indicators(clean).dropna(
        subset=[
            "ball_speed_mph",
            "launch_angle_deg",
            "launch_direction_deg",
            "backspin_rpm",
            "sidespin_rpm",
            TARGET,
        ]
    ).copy()
    return {
        "S1_core": AnalysisDataset(
            "S1_core",
            s1,
            CORE_FEATURES,
            "Core sample without club speed or attack angle.",
        ),
        "S2_complete": AnalysisDataset(
            "S2_complete",
            s2,
            PRIMARY_FEATURES,
            "Complete-case sample after invalid zero correction.",
        ),
        "S3_imputed": AnalysisDataset(
            "S3_imputed",
            s3,
            PRIMARY_FEATURES + MISSING_INDICATORS,
            "Full sample with fold-local median imputation and missing indicators.",
        ),
        "S3_spin_components": AnalysisDataset(
            "S3_spin_components",
            s3_spin_components,
            SPIN_COMPONENT_FEATURES + MISSING_INDICATORS,
            "Sensitivity sample using backspin and sidespin instead of spin rate and axis.",
        ),
    }


def generate_data_audit(
    raw_canonical: pd.DataFrame,
    clean: pd.DataFrame,
    invalid_zero_records: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize raw missingness, invalid zero corrections, and corrected missingness."""
    rows = []
    for column in ["record_id", *INPUT_FEATURES, *OUTPUT_COLUMNS]:
        raw_series = raw_canonical[column]
        clean_series = clean[column]
        rows.append(
            {
                "column": column,
                "raw_missing_count": int(raw_series.isna().sum()),
                "invalid_zero_count": int(
                    invalid_zero_records.get(INVALID_ZERO_RULES.get(column, ""), pd.Series(dtype=int)).sum()
                )
                if column in INVALID_ZERO_RULES
                else 0,
                "corrected_missing_count": int(clean_series.isna().sum()),
                "non_missing": int(clean_series.notna().sum()),
                "missing_rate": float(clean_series.isna().mean()),
                "min": float(clean_series.min(skipna=True)) if clean_series.notna().any() else np.nan,
                "median": float(clean_series.median(skipna=True)) if clean_series.notna().any() else np.nan,
                "max": float(clean_series.max(skipna=True)) if clean_series.notna().any() else np.nan,
            }
        )
    return pd.DataFrame(rows)
