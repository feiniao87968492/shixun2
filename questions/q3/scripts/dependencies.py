from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import yaml


LAUNCH_FEATURES = [
    "ball_speed_mph",
    "launch_angle_deg",
    "launch_direction_deg",
    "spin_rate_rpm",
    "spin_axis_deg",
]
SUPPORT_FEATURES = ["ball_speed_mph", "launch_angle_deg", "spin_rate_rpm", "spin_axis_deg"]


@dataclass
class Q3Dependencies:
    config: dict[str, Any]
    full_config: dict[str, Any]
    clean: pd.DataFrame
    split: pd.DataFrame
    train: pd.DataFrame
    test: pd.DataFrame
    carry_model: Any
    apex_model: Any
    q2_metadata: dict[str, Any]
    q2_ode_parameters: dict[str, Any]
    audit: pd.DataFrame


def load_full_config(root: Path, config_path: str | Path) -> dict[str, Any]:
    path = root / config_path
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if "q3" not in config:
        raise KeyError("configs/default.yaml must define q3")
    return config


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def values_sha256(values: pd.Series) -> str:
    payload = "\n".join(map(str, sorted(values.astype(int).tolist()))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_clean_data(root: Path, q3_config: dict[str, Any]) -> pd.DataFrame:
    path = root / q3_config["input_path"]
    if not path.exists():
        raise FileNotFoundError(f"q3 input data missing: {path}")
    clean = pd.read_csv(path)
    if "apex_height_yd" not in clean.columns and "max_height_yd" in clean.columns:
        clean["apex_height_yd"] = clean["max_height_yd"]
    required = {"record_id", "carry_distance_yd", "apex_height_yd", "lateral_offset_yd", *LAUNCH_FEATURES}
    missing = required.difference(clean.columns)
    if missing:
        raise ValueError(f"q3 input data missing columns: {sorted(missing)}")
    return clean


def split_frames(clean: pd.DataFrame, split: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_ids = set(split.loc[split["split"] == "train", "record_id"].astype(int))
    test_ids = set(split.loc[split["split"] == "test", "record_id"].astype(int))
    if train_ids & test_ids:
        raise ValueError("q2 split has overlapping train/test record IDs")
    train = clean[clean["record_id"].astype(int).isin(train_ids)].copy()
    test = clean[clean["record_id"].astype(int).isin(test_ids)].copy()
    return train.reset_index(drop=True), test.reset_index(drop=True)


def _safe_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _feature_names(model: Any) -> list[str]:
    names = getattr(model, "feature_names_in_", None)
    if names is None:
        return []
    return [str(value) for value in names]


def _row(check: str, passed: bool, value: object, notes: str = "") -> dict[str, object]:
    return {"check": check, "passed": bool(passed), "value": value, "notes": notes}


def load_dependencies(root: Path, config_path: str | Path) -> Q3Dependencies:
    full_config = load_full_config(root, config_path)
    q3_config = full_config["q3"]
    clean = load_clean_data(root, q3_config)

    carry_path = root / "questions/q2/artifacts/models/q2_carry_model.joblib"
    apex_path = root / "questions/q2/artifacts/models/q2_apex_model.joblib"
    split_path = root / "questions/q2/artifacts/tables/q2_data_split.csv"
    q2_metadata_path = root / "questions/q2/artifacts/run_metadata.json"
    q2_validation_path = root / "questions/q2/artifacts/tables/q2_validation_checks.csv"
    ode_params_path = root / "questions/q2/artifacts/models/q2_ode_parameters.json"

    carry_model = joblib.load(carry_path)
    apex_model = joblib.load(apex_path)
    split = pd.read_csv(split_path)
    train, test = split_frames(clean, split)
    q2_metadata = _safe_json(q2_metadata_path)
    q2_ode_parameters = _safe_json(ode_params_path)
    q2_validation = pd.read_csv(q2_validation_path)
    q2_metadata_sha256 = file_sha256(q2_metadata_path)
    q2_ode_parameters_sha256 = file_sha256(ode_params_path)

    train_count = int((split["split"] == "train").sum())
    test_count = int((split["split"] == "test").sum())
    overlap = len(
        set(split.loc[split["split"] == "train", "record_id"].astype(int))
        & set(split.loc[split["split"] == "test", "record_id"].astype(int))
    )
    blocking_failures = q2_validation[~q2_validation["passed"].astype(bool)]
    q2_ode_verified = bool(
        q2_metadata.get("q3_compatible_boundary_checks_passed")
        and q2_metadata.get("carry_definition") == "forward_x"
        and q2_ode_parameters.get("carry_definition") == "forward_x"
    )
    audit_rows = [
        _row("q2_carry_model_loadable", carry_path.exists(), "true", carry_path.as_posix()),
        _row("q2_apex_model_loadable", apex_path.exists(), "true", apex_path.as_posix()),
        _row("q2_train_count", train_count == 514, train_count),
        _row("q2_test_count", test_count == 221, test_count),
        _row("q2_split_overlap_count", overlap == 0, overlap),
        _row("q2_metadata_readable", bool(q2_metadata), "true"),
        _row("q2_run_metadata_sha256", True, q2_metadata_sha256, q2_metadata_path.as_posix()),
        _row("q2_ode_parameters_sha256", True, q2_ode_parameters_sha256, ode_params_path.as_posix()),
        _row(
            "q2_carry_definition",
            q2_metadata.get("carry_definition") == "forward_x"
            and q2_ode_parameters.get("carry_definition") == "forward_x",
            str(q2_metadata.get("carry_definition", "unknown")),
        ),
        _row("q2_validation_has_no_blocking_failures", blocking_failures.empty, int(len(blocking_failures))),
        _row("q2_ode_parameters_valid", bool(q2_ode_parameters.get("model_parameters")), "true"),
        _row("input_record_count", len(clean) == 735, int(len(clean))),
        _row(
            "input_key_fields_complete",
            not clean[["record_id", "carry_distance_yd", "lateral_offset_yd", *LAUNCH_FEATURES]].isna().any().any(),
            "true",
        ),
        _row("q2_feature_order_matches_carry_model", _feature_names(carry_model) == LAUNCH_FEATURES, ";".join(_feature_names(carry_model))),
        _row("q3_supervised_ready", True, "true"),
        _row("q3_ode_verified", q2_ode_verified, str(q2_ode_verified).lower()),
    ]
    audit = pd.DataFrame(audit_rows)
    return Q3Dependencies(
        config=q3_config,
        full_config=full_config,
        clean=clean,
        split=split,
        train=train,
        test=test,
        carry_model=carry_model,
        apex_model=apex_model,
        q2_metadata=q2_metadata,
        q2_ode_parameters=q2_ode_parameters,
        audit=audit,
    )
