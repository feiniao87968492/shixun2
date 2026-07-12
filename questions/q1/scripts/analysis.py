#!/usr/bin/env python3
"""Q1 data audit, correlation analysis, ranking, and visualization helpers."""

from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RepeatedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) in sys.path:
        continue
    sys.path.insert(0, str(path))

from modeling_common.artifacts import CSV_FLOAT_FORMAT, CSV_LINE_TERMINATOR, save_figure_bundle, save_table  # noqa: E402
from preprocessing import (  # noqa: E402
    CORE_FEATURES,
    INPUT_FEATURES,
    MISSING_INDICATORS,
    OUTPUT_COLUMNS,
    PRIMARY_FEATURES,
    RAW_RELATIVE_PATH,
    RAW_TO_CANONICAL,
    SHEET_NAME,
    SPIN_COMPONENT_FEATURES,
    TARGET,
    add_missing_indicators,
    build_analysis_datasets,
    canonicalize_golf_data,
    generate_data_audit,
    load_data,
    replace_invalid_zero_values,
)

FEATURE_LABELS = {
    "ball_speed_mph": "Ball speed",
    "launch_angle_deg": "Launch angle",
    "launch_direction_deg": "Launch direction",
    "spin_rate_rpm": "Spin rate",
    "spin_axis_deg": "Spin axis",
    "backspin_rpm": "Backspin",
    "sidespin_rpm": "Sidespin",
    "club_speed_mph": "Club speed",
    "attack_angle_deg": "Attack angle",
}

OUTPUT_LABELS = {
    "carry_distance_yd": "Carry distance",
    "max_height_yd": "Max height",
    "total_distance_yd": "Total distance",
    "lateral_offset_yd": "Lateral offset",
}

INPUT_FEATURES = list(FEATURE_LABELS)
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
OUTPUT_COLUMNS = list(OUTPUT_LABELS)
TARGET = "carry_distance_yd"
MISSING_INDICATORS = ["club_speed_missing", "attack_angle_missing"]


class SampleView:
    """A reproducible modeling view with a defined sample口径 and feature set."""

    def __init__(self, name: str, frame: pd.DataFrame, features: list[str], description: str):
        self.name = name
        self.frame = frame
        self.features = features
        self.description = description


def load_config(root: Path, config_path: str | Path) -> dict[str, Any]:
    path = root / config_path
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def random_seed(config: dict[str, Any]) -> int:
    return int(config.get("q1", {}).get("random_seed", config.get("runtime", {}).get("random_seed", 2026)))


def q1_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("q1", {})


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def package_versions() -> dict[str, str]:
    import matplotlib
    import sklearn
    import scipy

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "matplotlib": matplotlib.__version__,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2))


def load_raw_golf_data(root: Path) -> pd.DataFrame:
    """Load the Excel attachment using the real header row."""
    path = root / RAW_RELATIVE_PATH
    if not path.exists():
        raise FileNotFoundError(f"Raw Excel attachment not found: {path}")
    return pd.read_excel(path, sheet_name=SHEET_NAME, header=2, na_values=[""])


def clean_golf_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize fields and treat confirmed impossible zero measurements as missing."""
    canonical = canonicalize_golf_data(raw)
    clean, _ = replace_invalid_zero_values(canonical)
    return clean


def with_missing_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    return add_missing_indicators(frame)


def build_sample_views(clean: pd.DataFrame) -> dict[str, SampleView]:
    """Create S1/S2/S3 and spin-component sensitivity modeling views."""
    datasets = build_analysis_datasets(clean)
    return {
        name: SampleView(dataset.name, dataset.frame, dataset.features, dataset.description)
        for name, dataset in datasets.items()
    }


def compute_correlations(
    frame: pd.DataFrame, features: list[str], outputs: list[str]
) -> dict[str, pd.DataFrame]:
    """Return Pearson, Spearman, and Kendall input-output correlations in long form."""
    tables: dict[str, list[dict[str, Any]]] = {"pearson": [], "spearman": [], "kendall": []}
    for feature in features:
        for output in outputs:
            pair = frame[[feature, output]].dropna()
            if len(pair) < 3:
                values = {"pearson": np.nan, "spearman": np.nan, "kendall": np.nan}
            else:
                values = {
                    "pearson": float(pair[feature].corr(pair[output], method="pearson")),
                    "spearman": float(pair[feature].corr(pair[output], method="spearman")),
                    "kendall": float(pair[feature].corr(pair[output], method="kendall")),
                }
            for method, value in values.items():
                tables[method].append(
                    {
                        "feature": feature,
                        "feature_label": FEATURE_LABELS.get(feature, feature),
                        "output": output,
                        "output_label": OUTPUT_LABELS.get(output, output),
                        "correlation": value,
                        "abs_correlation": abs(value) if pd.notna(value) else np.nan,
                        "n": int(len(pair)),
                    }
                )
    return {method: pd.DataFrame(rows) for method, rows in tables.items()}


def data_audit_table(clean: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in ["record_id", *INPUT_FEATURES, *OUTPUT_COLUMNS]:
        series = clean[column]
        numeric = series.dropna()
        role = "id" if column == "record_id" else "input" if column in INPUT_FEATURES else "output"
        rows.append(
            {
                "column": column,
                "label": FEATURE_LABELS.get(column, OUTPUT_LABELS.get(column, column)),
                "role": role,
                "dtype": str(series.dtype),
                "non_missing": int(series.notna().sum()),
                "missing_count": int(series.isna().sum()),
                "missing_rate": float(series.isna().mean()),
                "min": float(numeric.min()) if not numeric.empty else np.nan,
                "q1": float(numeric.quantile(0.25)) if not numeric.empty else np.nan,
                "median": float(numeric.median()) if not numeric.empty else np.nan,
                "q3": float(numeric.quantile(0.75)) if not numeric.empty else np.nan,
                "max": float(numeric.max()) if not numeric.empty else np.nan,
                "mean": float(numeric.mean()) if not numeric.empty else np.nan,
                "std": float(numeric.std(ddof=1)) if len(numeric) > 1 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def missing_audit_table(clean: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in ["record_id", *INPUT_FEATURES, *OUTPUT_COLUMNS]:
        if column in ["club_speed_mph", "attack_angle_deg"]:
            handling = "median imputation with missing indicator; complete-case sensitivity"
        elif column == "record_id":
            handling = "sample id, excluded from models"
        else:
            handling = "required field; no imputation planned if complete"
        rows.append(
            {
                "column": column,
                "role": "input" if column in INPUT_FEATURES else "output" if column in OUTPUT_COLUMNS else "id",
                "missing_count": int(clean[column].isna().sum()),
                "missing_rate": float(clean[column].isna().mean()),
                "handling": handling,
            }
        )
    return pd.DataFrame(rows)


def outlier_flags(clean: pd.DataFrame) -> pd.DataFrame:
    flags = clean[["record_id"]].copy()
    numeric_columns = INPUT_FEATURES + OUTPUT_COLUMNS
    extreme = pd.Series(False, index=clean.index)
    for column in numeric_columns:
        values = clean[column].dropna()
        low = values.quantile(0.01)
        high = values.quantile(0.99)
        flag = clean[column].lt(low) | clean[column].gt(high)
        flags[f"{column}_outside_1pct"] = flag.fillna(False).astype(int)
        extreme = extreme | flag.fillna(False)

    spin_norm = np.sqrt(clean["backspin_rpm"] ** 2 + clean["sidespin_rpm"] ** 2)
    relative_spin_error = (spin_norm - clean["spin_rate_rpm"]).abs() / clean["spin_rate_rpm"].replace(0, np.nan)
    flags["spin_geometry_error_gt_5pct"] = relative_spin_error.gt(0.05).fillna(False).astype(int)
    flags["club_speed_zero"] = clean["club_speed_mph"].eq(0).fillna(False).astype(int)
    smash_factor = clean["ball_speed_mph"] / clean["club_speed_mph"].replace(0, np.nan)
    flags["ball_club_speed_ratio_flag"] = (
        smash_factor.lt(0.8) | smash_factor.gt(2.0)
    ).fillna(False).astype(int)
    flags["any_continuous_outside_1pct"] = extreme.astype(int)
    quality_cols = [col for col in flags.columns if col != "record_id"]
    flags["quality_flag_count"] = flags[quality_cols].sum(axis=1)
    return flags


def _rank_desc(series: pd.Series) -> pd.Series:
    filled = series.fillna(series.min(skipna=True) if series.notna().any() else 0.0)
    return filled.rank(ascending=False, method="min").astype(int)


def _ridge_coefficients(
    view: SampleView,
    *,
    seed: int,
    cv_splits: int,
    cv_repeats: int,
) -> pd.DataFrame:
    X = view.frame[view.features].to_numpy(dtype=float)
    y = view.frame[TARGET].to_numpy(dtype=float)
    alphas = np.logspace(-3, 3, 25)
    cv = RepeatedKFold(n_splits=cv_splits, n_repeats=cv_repeats, random_state=seed)
    rows = []
    for fold_id, (train_idx, _) in enumerate(cv.split(X), start=1):
        model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), RidgeCV(alphas=alphas))
        model.fit(X[train_idx], y[train_idx])
        ridge = model.named_steps["ridgecv"]
        for feature, coefficient in zip(view.features, ridge.coef_, strict=True):
            rows.append(
                {
                    "sample_view": view.name,
                    "fold": fold_id,
                    "feature": feature,
                    "ridge_coef": float(coefficient),
                    "ridge_alpha": float(ridge.alpha_),
                }
            )
    fold_coefficients = pd.DataFrame(rows)
    return (
        fold_coefficients.groupby(["sample_view", "feature"], as_index=False)
        .agg(
            ridge_coef_mean=("ridge_coef", "mean"),
            ridge_coef_std=("ridge_coef", lambda s: float(s.std(ddof=1)) if len(s) > 1 else 0.0),
            ridge_alpha=("ridge_alpha", "median"),
            ridge_positive_frequency=("ridge_coef", lambda s: float((s > 0).mean())),
            ridge_negative_frequency=("ridge_coef", lambda s: float((s < 0).mean())),
            ridge_fold_count=("fold", "nunique"),
        )
    )


def _permutation_importance(
    view: SampleView,
    *,
    seed: int,
    cv_splits: int,
    cv_repeats: int,
    permutation_repeats: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    X = view.frame[view.features].to_numpy(dtype=float)
    y = view.frame[TARGET].to_numpy(dtype=float)
    cv = RepeatedKFold(n_splits=cv_splits, n_repeats=cv_repeats, random_state=seed)
    rng = np.random.default_rng(seed)
    importance = {feature: [] for feature in view.features}
    fold_positive = {feature: [] for feature in view.features}
    scores = []

    for fold_id, (train_idx, valid_idx) in enumerate(cv.split(X), start=1):
        model = make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesRegressor(
                n_estimators=120,
                min_samples_leaf=3,
                random_state=seed + fold_id,
                n_jobs=-1,
            ),
        )
        model.fit(X[train_idx], y[train_idx])
        original_pred = model.predict(X[valid_idx])
        original_rmse = math.sqrt(mean_squared_error(y[valid_idx], original_pred))
        scores.append(
            {
                "sample_view": view.name,
                "model": "ExtraTreesRegressor",
                "fold": fold_id,
                "rmse": original_rmse,
                "mae": float(mean_absolute_error(y[valid_idx], original_pred)),
                "r2": float(r2_score(y[valid_idx], original_pred)),
            }
        )
        for feature_idx, feature in enumerate(view.features):
            deltas = []
            for _ in range(permutation_repeats):
                X_perm = X[valid_idx].copy()
                X_perm[:, feature_idx] = rng.permutation(X_perm[:, feature_idx])
                rmse = math.sqrt(mean_squared_error(y[valid_idx], model.predict(X_perm)))
                deltas.append(rmse - original_rmse)
            fold_delta = float(np.mean(deltas))
            importance[feature].append(fold_delta)
            fold_positive[feature].append(float(fold_delta > 0))

    rows = []
    for feature, values in importance.items():
        rows.append(
            {
                "feature": feature,
                "sample_view": view.name,
                "permutation_importance": float(np.mean(values)),
                "permutation_importance_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "positive_frequency": float(np.mean(fold_positive[feature])),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(scores)


def model_importance_tables(
    views: dict[str, SampleView],
    *,
    seed: int,
    cv_splits: int = 5,
    cv_repeats: int = 5,
    permutation_repeats: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute ridge and nonlinear permutation importance without duplicating spin encodings."""
    detail_frames = []
    score_frames = []
    for key in ["S3_imputed", "S3_spin_components"]:
        view = views[key]
        ridge = _ridge_coefficients(
            view,
            seed=seed,
            cv_splits=cv_splits,
            cv_repeats=cv_repeats,
        )
        permutation, scores = _permutation_importance(
            view,
            seed=seed,
            cv_splits=cv_splits,
            cv_repeats=cv_repeats,
            permutation_repeats=permutation_repeats,
        )
        merged = ridge.merge(permutation, on=["feature", "sample_view"], how="outer")
        detail_frames.append(merged)
        score_frames.append(scores)

    details = pd.concat(detail_frames, ignore_index=True)
    details = details[~details["feature"].isin(MISSING_INDICATORS)].copy()
    details["ridge_coef"] = details["ridge_coef_mean"]
    details["direction"] = np.where(
        details["ridge_coef_mean"].abs().lt(1e-12),
        "weak",
        np.where(details["ridge_coef_mean"].gt(0), "positive", "negative"),
    )
    details["ridge_abs_rank"] = details.groupby("sample_view")["ridge_coef_mean"].transform(
        lambda s: _rank_desc(s.abs())
    )
    details["permutation_rank"] = details.groupby("sample_view")["permutation_importance"].transform(
        lambda s: _rank_desc(s.clip(lower=0))
    )
    ridge_details = details[
        [
            "sample_view",
            "feature",
            "ridge_coef_mean",
            "ridge_coef_std",
            "ridge_abs_rank",
            "direction",
            "ridge_alpha",
            "ridge_fold_count",
            "ridge_positive_frequency",
            "ridge_negative_frequency",
        ]
    ].rename(
        columns={
            "ridge_positive_frequency": "positive_frequency",
            "ridge_negative_frequency": "negative_frequency",
        }
    ).copy()
    permutation_details = details[
        [
            "sample_view",
            "feature",
            "permutation_importance",
            "permutation_importance_std",
            "permutation_rank",
            "positive_frequency",
        ]
    ].copy()
    summary = (
        details.groupby("feature", as_index=False)
        .agg(
            ridge_coef=("ridge_coef", "median"),
            ridge_coef_abs=("ridge_coef", lambda s: float(np.median(np.abs(s)))),
            ridge_alpha=("ridge_alpha", "median"),
            permutation_importance=("permutation_importance", "median"),
            permutation_importance_std=("permutation_importance_std", "median"),
            sample_views=("sample_view", lambda s: ";".join(sorted(set(map(str, s))))),
        )
    )
    return summary, pd.concat(score_frames, ignore_index=True), ridge_details, permutation_details


def method_importance_table(correlations: dict[str, pd.DataFrame], model_summary: pd.DataFrame) -> pd.DataFrame:
    pearson = correlations["pearson"]
    spearman = correlations["spearman"]
    pearson_carry = pearson[pearson["output"] == TARGET][["feature", "correlation"]].rename(
        columns={"correlation": "pearson"}
    )
    spearman_carry = spearman[spearman["output"] == TARGET][["feature", "correlation"]].rename(
        columns={"correlation": "spearman"}
    )
    table = pd.DataFrame({"feature": INPUT_FEATURES})
    table["feature_label"] = table["feature"].map(FEATURE_LABELS)
    table = table.merge(pearson_carry, on="feature", how="left")
    table = table.merge(spearman_carry, on="feature", how="left")
    table = table.merge(model_summary, on="feature", how="left")
    return table


def bootstrap_correlation_intervals(
    frame: pd.DataFrame,
    *,
    seed: int,
    iterations: int = 500,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for feature in INPUT_FEATURES:
        for output in OUTPUT_COLUMNS:
            pair = frame[[feature, output]].dropna().reset_index(drop=True)
            if len(pair) < 5:
                continue
            values = {"pearson": [], "spearman": []}
            for _ in range(iterations):
                idx = rng.integers(0, len(pair), len(pair))
                sample = pair.iloc[idx]
                values["pearson"].append(sample[feature].corr(sample[output], method="pearson"))
                values["spearman"].append(sample[feature].corr(sample[output], method="spearman"))
            for method, estimates in values.items():
                estimates = np.asarray(estimates, dtype=float)
                estimates = estimates[np.isfinite(estimates)]
                rows.append(
                    {
                        "feature": feature,
                        "output": output,
                        "method": method,
                        "estimate": float(pair[feature].corr(pair[output], method=method)),
                        "ci_low": float(np.quantile(estimates, 0.025)),
                        "ci_high": float(np.quantile(estimates, 0.975)),
                        "iterations": iterations,
                    }
                )
    return pd.DataFrame(rows)


def bootstrap_rank_stability(
    frame: pd.DataFrame,
    *,
    seed: int,
    iterations: int = 500,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ranks: dict[str, list[int]] = {feature: [] for feature in INPUT_FEATURES}
    for _ in range(iterations):
        idx = rng.integers(0, len(frame), len(frame))
        sample = frame.iloc[idx].reset_index(drop=True)
        correlations = compute_correlations(sample, INPUT_FEATURES, [TARGET])
        method = method_importance_table(
            correlations,
            pd.DataFrame(
                {
                    "feature": INPUT_FEATURES,
                    "ridge_coef": np.nan,
                    "ridge_coef_abs": np.nan,
                    "permutation_importance": np.nan,
                }
            ),
        )
        method["marginal_score"] = method[["pearson", "spearman"]].abs().median(axis=1)
        method["rank"] = _rank_desc(method["marginal_score"])
        for _, row in method.iterrows():
            ranks[row["feature"]].append(int(row["rank"]))

    rows = []
    for feature, values in ranks.items():
        arr = np.asarray(values)
        rows.append(
            {
                "feature": feature,
                "marginal_rank_median": float(np.median(arr)),
                "marginal_rank_ci_low": int(np.quantile(arr, 0.025, method="nearest")),
                "marginal_rank_ci_high": int(np.quantile(arr, 0.975, method="nearest")),
                "marginal_rank_interval": f"{int(np.quantile(arr, 0.025, method='nearest'))}-{int(np.quantile(arr, 0.975, method='nearest'))}",
                "marginal_top3_frequency": float(np.mean(arr <= 3)),
                "marginal_top5_frequency": float(np.mean(arr <= 5)),
                "stability_scope": "marginal_correlation_bootstrap",
                "iterations": iterations,
            }
        )
    return pd.DataFrame(rows).sort_values(["marginal_rank_median", "feature"]).reset_index(drop=True)


def _normalize_stability_columns(stability: pd.DataFrame) -> pd.DataFrame:
    stability = stability.copy()
    rename_map = {
        "rank_median": "marginal_rank_median",
        "rank_ci_low": "marginal_rank_ci_low",
        "rank_ci_high": "marginal_rank_ci_high",
        "rank_interval": "marginal_rank_interval",
        "top3_frequency": "marginal_top3_frequency",
        "top5_frequency": "marginal_top5_frequency",
    }
    for old, new in rename_map.items():
        if old in stability.columns and new not in stability.columns:
            stability[new] = stability[old]
    if "marginal_top5_frequency" not in stability.columns:
        stability["marginal_top5_frequency"] = np.nan
    if "stability_scope" not in stability.columns:
        stability["stability_scope"] = "marginal_correlation_bootstrap"
    return stability


def aggregate_rankings(method_table: pd.DataFrame, stability: pd.DataFrame | None = None) -> pd.DataFrame:
    ranking = method_table.copy()
    if "feature_label" not in ranking.columns:
        ranking["feature_label"] = ranking["feature"].map(FEATURE_LABELS).fillna(ranking["feature"])
    ranking["pearson_rank"] = _rank_desc(ranking["pearson"].abs())
    ranking["spearman_rank"] = _rank_desc(ranking["spearman"].abs())
    ranking["ridge_rank"] = _rank_desc(ranking["ridge_coef"].abs())
    ranking["permutation_rank"] = _rank_desc(ranking["permutation_importance"].clip(lower=0))

    p = len(ranking)
    for rank_col in ["pearson_rank", "spearman_rank", "ridge_rank", "permutation_rank"]:
        score_col = rank_col.replace("_rank", "_score")
        ranking[score_col] = (p - ranking[rank_col]) / max(p - 1, 1)
    score_cols = ["pearson_score", "spearman_score", "ridge_score", "permutation_score"]
    ranking["aggregate_score"] = ranking[score_cols].median(axis=1)
    ranking["final_rank"] = _rank_desc(ranking["aggregate_score"])

    if stability is not None:
        stability = _normalize_stability_columns(stability)
        ranking = ranking.merge(
            stability[
                [
                    "feature",
                    "marginal_rank_interval",
                    "marginal_top3_frequency",
                    "marginal_top5_frequency",
                    "stability_scope",
                ]
            ],
            on="feature",
            how="left",
        )
    else:
        ranking["marginal_rank_interval"] = ""
        ranking["marginal_top3_frequency"] = np.nan
        ranking["marginal_top5_frequency"] = np.nan
        ranking["stability_scope"] = "marginal_correlation_bootstrap"

    def direction(row: pd.Series) -> str:
        value = row["pearson"] if abs(row["pearson"]) >= abs(row["spearman"]) else row["spearman"]
        if abs(value) < 0.1:
            return "weak"
        return "positive" if value > 0 else "negative"

    def stability_label(row: pd.Series) -> str:
        interval = str(row.get("marginal_rank_interval", ""))
        width = 99
        if "-" in interval:
            low, high = interval.split("-", 1)
            width = int(high) - int(low)
        top3 = row.get("marginal_top3_frequency", 0.0)
        if row["final_rank"] <= 3 and top3 >= 0.6 and width <= 4:
            return "stable_key"
        if row["final_rank"] <= 6 and width <= 6:
            return "secondary"
        if width > 6 or 0.2 <= top3 < 0.6:
            return "unstable"
        return "weak"

    ranking["direction"] = ranking.apply(direction, axis=1)
    ranking["stability"] = ranking.apply(stability_label, axis=1)
    ordered_cols = [
        "feature",
        "feature_label",
        "pearson",
        "spearman",
        "ridge_coef",
        "permutation_importance",
        "pearson_rank",
        "spearman_rank",
        "ridge_rank",
        "permutation_rank",
        "pearson_score",
        "spearman_score",
        "ridge_score",
        "permutation_score",
        "aggregate_score",
        "final_rank",
        "marginal_rank_interval",
        "marginal_top3_frequency",
        "marginal_top5_frequency",
        "stability_scope",
        "direction",
        "stability",
    ]
    ranking["deprecated"] = True
    ranking["not_for_final_conclusion"] = True
    ordered_cols.extend(["deprecated", "not_for_final_conclusion"])
    return ranking.sort_values(["final_rank", "feature"])[ordered_cols].reset_index(drop=True)


def _rank_by_marginal(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    correlations = compute_correlations(frame, features, [TARGET])
    table = method_importance_table(
        correlations,
        pd.DataFrame(
            {
                "feature": features,
                "ridge_coef": np.nan,
                "ridge_coef_abs": np.nan,
                "permutation_importance": np.nan,
            }
        ),
    )
    table["score"] = table[["pearson", "spearman"]].abs().median(axis=1)
    table["rank"] = _rank_desc(table["score"])
    return table.sort_values("rank").reset_index(drop=True)


def _descriptive_imputed_frame(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    imputed = frame.copy()
    for feature in features:
        if feature in imputed.columns and imputed[feature].isna().any():
            imputed[feature] = imputed[feature].fillna(imputed[feature].median())
    return imputed


def sensitivity_comparison(clean: pd.DataFrame, main_ranking: pd.DataFrame) -> pd.DataFrame:
    scenarios: list[tuple[str, pd.DataFrame, list[str], str, str]] = []
    views = build_sample_views(clean)
    scenarios.append(
        ("S1_core", views["S1_core"].frame, views["S1_core"].features, "No club speed or attack angle.", "observed_marginal")
    )
    scenarios.append(
        ("S2_complete", views["S2_complete"].frame, views["S2_complete"].features, "Complete-case primary variables.", "observed_marginal")
    )
    scenarios.append(
        (
            "S3_imputed",
            _descriptive_imputed_frame(views["S3_imputed"].frame, PRIMARY_FEATURES),
            PRIMARY_FEATURES,
            "Descriptive median-imputed marginal ranking; model CV uses fold-local imputation.",
            "descriptive_imputed_marginal",
        )
    )
    scenarios.append(
        (
            "S3_spin_components",
            views["S3_spin_components"].frame,
            SPIN_COMPONENT_FEATURES,
            "Backspin and sidespin representation.",
            "observed_marginal",
        )
    )

    continuous = INPUT_FEATURES + OUTPUT_COLUMNS
    low = clean[continuous].quantile(0.01)
    high = clean[continuous].quantile(0.99)
    mask = clean[continuous].ge(low).all(axis=1) & clean[continuous].le(high).all(axis=1)
    scenarios.append(("trim_1pct", clean[mask].copy(), PRIMARY_FEATURES, "Rows outside 1%-99% range removed.", "joint_trim_marginal"))

    winsorized = clean.copy()
    for column in continuous:
        winsorized[column] = winsorized[column].clip(low[column], high[column])
    scenarios.append(("winsorized_1pct", winsorized, PRIMARY_FEATURES, "Continuous variables clipped to 1%-99%.", "winsorized_marginal"))

    rank_column = "final_rank" if "final_rank" in main_ranking.columns else "marginal_rank"
    main_order = main_ranking.set_index("feature")[rank_column]
    rows = []
    for name, frame, features, notes, analysis_type in scenarios:
        available = [feature for feature in features if feature in frame.columns]
        ranked_frame = frame.dropna(subset=[*available, TARGET])
        ranked = _rank_by_marginal(ranked_frame, available)
        top3 = ranked.head(3)["feature"].tolist()
        top5 = ranked.head(5)["feature"].tolist()
        common = [feature for feature in ranked["feature"] if feature in main_order.index]
        if len(common) >= 3:
            rho = float(
                spearmanr(
                    ranked.set_index("feature").loc[common, "rank"],
                    main_order.loc[common],
                ).statistic
            )
        else:
            rho = np.nan
        rows.append(
            {
                "scenario": name,
                "n": int(len(frame)),
                "ranked_n": int(len(ranked_frame)),
                "feature_count": int(len(available)),
                "top3": ";".join(top3),
                "top5": ";".join(top5),
                "spearman_with_main_rank": rho,
                "analysis_type": analysis_type,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def group_importance(
    clean: pd.DataFrame,
    *,
    seed: int,
    cv_splits: int,
    cv_repeats: int,
    permutation_repeats: int,
) -> pd.DataFrame:
    views = build_sample_views(clean)
    group_specs = [
        ("speed_group", "S3_imputed", ["ball_speed_mph", "club_speed_mph"]),
        ("launch_attitude_group", "S3_imputed", ["launch_angle_deg", "attack_angle_deg"]),
        ("horizontal_direction_group", "S3_imputed", ["launch_direction_deg"]),
        ("spin_state_group_A", "S3_imputed", ["spin_rate_rpm", "spin_axis_deg"]),
        ("spin_state_group_B", "S3_spin_components", ["backspin_rpm", "sidespin_rpm"]),
    ]
    rng = np.random.default_rng(seed)
    grouped_specs: dict[str, list[tuple[str, list[str]]]] = {}
    for group, view_name, features in group_specs:
        grouped_specs.setdefault(view_name, []).append((group, features))

    deltas: dict[str, list[float]] = {group: [] for group, _, _ in group_specs}
    baseline_rmses: dict[str, list[float]] = {group: [] for group, _, _ in group_specs}
    permuted_rmses: dict[str, list[float]] = {group: [] for group, _, _ in group_specs}
    positives: dict[str, list[float]] = {group: [] for group, _, _ in group_specs}

    for view_name, specs in grouped_specs.items():
        view = views[view_name]
        X = view.frame[view.features].to_numpy(dtype=float)
        y = view.frame[TARGET].to_numpy(dtype=float)
        cv = RepeatedKFold(n_splits=cv_splits, n_repeats=cv_repeats, random_state=seed)
        for fold_id, (train_idx, valid_idx) in enumerate(cv.split(X), start=1):
            model = make_pipeline(
                SimpleImputer(strategy="median"),
                ExtraTreesRegressor(n_estimators=120, min_samples_leaf=3, random_state=seed + fold_id, n_jobs=-1),
            )
            model.fit(X[train_idx], y[train_idx])
            X_valid = X[valid_idx].copy()
            y_valid = y[valid_idx]
            original_rmse = math.sqrt(mean_squared_error(y_valid, model.predict(X_valid)))
            for group, features in specs:
                feature_indexes = [view.features.index(feature) for feature in features]
                for _ in range(permutation_repeats):
                    X_perm = X_valid.copy()
                    row_permutation = rng.permutation(len(X_valid))
                    X_perm[:, feature_indexes] = X_valid[row_permutation][:, feature_indexes]
                    permuted_rmse = math.sqrt(mean_squared_error(y_valid, model.predict(X_perm)))
                    delta = permuted_rmse - original_rmse
                    deltas[group].append(delta)
                    baseline_rmses[group].append(original_rmse)
                    permuted_rmses[group].append(permuted_rmse)
                    positives[group].append(float(delta > 0))

    rows = []
    for group, view_name, features in group_specs:
        values = np.asarray(deltas[group], dtype=float)
        rows.append(
            {
                "group": group,
                "sample_view": view_name,
                "features": ";".join(features),
                "original_rmse": float(np.mean(baseline_rmses[group])),
                "permuted_rmse": float(np.mean(permuted_rmses[group])),
                "importance_mean": float(np.mean(values)),
                "importance_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "positive_frequency": float(np.mean(positives[group])),
                "fold_count": int(cv_splits * cv_repeats),
                "permutation_repeats": int(permutation_repeats),
                "block_permutation": True,
            }
        )
    result = pd.DataFrame(rows)
    result["rank"] = _rank_desc(result["importance_mean"].clip(lower=0))
    return result.sort_values("rank").reset_index(drop=True)


def sample_definition_comparison(clean: pd.DataFrame) -> pd.DataFrame:
    views = build_sample_views(clean)
    rows = []
    for name, view in views.items():
        rows.append(
            {
                "sample_view": name,
                "n": int(len(view.frame)),
                "feature_count": int(len(view.features)),
                "features": ";".join(view.features),
                "missing_in_model_features": int(view.frame[view.features].isna().sum().sum()),
                "description": view.description,
            }
        )
    return pd.DataFrame(rows)


def spin_representation_comparison(cv_scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    labels = {
        "S3_imputed": "A: spin_rate + spin_axis",
        "S3_spin_components": "B: backspin + sidespin",
    }
    for sample_view, label in labels.items():
        subset = cv_scores[cv_scores["sample_view"] == sample_view]
        rows.append(
            {
                "sample_view": sample_view,
                "spin_representation": label,
                "rmse_mean": float(subset["rmse"].mean()),
                "rmse_std": float(subset["rmse"].std(ddof=1)),
                "mae_mean": float(subset["mae"].mean()),
                "mae_std": float(subset["mae"].std(ddof=1)),
                "r2_mean": float(subset["r2"].mean()),
                "r2_std": float(subset["r2"].std(ddof=1)),
                "selected_as_main": bool(sample_view == "S3_imputed"),
            }
        )
    result = pd.DataFrame(rows)
    result["rmse_rank"] = result["rmse_mean"].rank(ascending=True, method="min").astype(int)
    return result.sort_values(["rmse_rank", "sample_view"]).reset_index(drop=True)


def outlier_audit(clean: pd.DataFrame) -> pd.DataFrame:
    continuous = INPUT_FEATURES + OUTPUT_COLUMNS
    low = clean[continuous].quantile(0.01)
    high = clean[continuous].quantile(0.99)
    non_missing_mask = clean[continuous].notna().all(axis=1)
    outside_observed = clean[continuous].lt(low) | clean[continuous].gt(high)
    outside_any = outside_observed.any(axis=1)
    joint_mask = non_missing_mask & ~outside_any
    missing_only = (~non_missing_mask) & ~outside_any
    quantile_only = non_missing_mask & outside_any
    both_missing_and_quantile = (~non_missing_mask) & outside_any
    target_mask = clean[TARGET].ge(low[TARGET]) & clean[TARGET].le(high[TARGET])
    rows = [
        {
            "scenario": "A_original_corrected",
            "original_n": int(len(clean)),
            "processed_n": int(len(clean)),
            "removed_n": 0,
            "removed_rate": 0.0,
            "missing_removed_n": 0,
            "quantile_removed_n": 0,
            "both_removed_n": 0,
            "rule": "No deletion after confirmed invalid zero correction.",
        },
        {
            "scenario": "B_winsorize_1pct",
            "original_n": int(len(clean)),
            "processed_n": int(len(clean)),
            "removed_n": 0,
            "removed_rate": 0.0,
            "missing_removed_n": 0,
            "quantile_removed_n": 0,
            "both_removed_n": 0,
            "rule": "Clip continuous variables to 1%-99% quantiles.",
        },
        {
            "scenario": "C_target_trim_1pct",
            "original_n": int(len(clean)),
            "processed_n": int(target_mask.sum()),
            "removed_n": int((~target_mask).sum()),
            "removed_rate": float((~target_mask).mean()),
            "missing_removed_n": 0,
            "quantile_removed_n": int((~target_mask).sum()),
            "both_removed_n": 0,
            "rule": "Remove only carry-distance extremes outside 1%-99%.",
        },
        {
            "scenario": "D_joint_trim_1pct",
            "original_n": int(len(clean)),
            "processed_n": int(joint_mask.sum()),
            "removed_n": int((~joint_mask).sum()),
            "removed_rate": float((~joint_mask).mean()),
            "missing_removed_n": int(missing_only.sum()),
            "quantile_removed_n": int(quantile_only.sum()),
            "both_removed_n": int(both_missing_and_quantile.sum()),
            "rule": "Retain rows inside 1%-99% for every continuous input/output.",
        },
    ]
    return pd.DataFrame(rows)


def feature_summary_table(method_table: pd.DataFrame, stability: pd.DataFrame) -> pd.DataFrame:
    summary = method_table.copy()
    summary["feature_label"] = summary["feature"].map(FEATURE_LABELS).fillna(summary["feature"])
    summary["marginal_score"] = summary[["pearson", "spearman"]].abs().median(axis=1)
    summary["marginal_rank"] = _rank_desc(summary["marginal_score"])
    summary["ridge_abs_rank"] = _rank_desc(summary["ridge_coef"].abs())
    summary["permutation_rank"] = _rank_desc(summary["permutation_importance"].clip(lower=0))
    stability = _normalize_stability_columns(stability)
    summary = summary.merge(
        stability[
            [
                "feature",
                "marginal_rank_interval",
                "marginal_top3_frequency",
                "marginal_top5_frequency",
                "stability_scope",
            ]
        ],
        on="feature",
        how="left",
    )

    def category(row: pd.Series) -> str:
        if row["feature"] == "attack_angle_deg":
            return "unstable"
        strong_count = int(row["marginal_rank"] <= 3) + int(row["ridge_abs_rank"] <= 3) + int(row["permutation_rank"] <= 3)
        if strong_count >= 3 and row.get("marginal_top3_frequency", 0.0) >= 0.6:
            return "stable_key"
        if row["permutation_rank"] <= 3 and row["marginal_rank"] > 5:
            return "structural_nonlinear"
        if strong_count >= 2:
            return "secondary"
        interval = str(row.get("marginal_rank_interval", ""))
        if "-" in interval:
            low_s, high_s = interval.split("-", 1)
            if int(high_s) - int(low_s) >= 5:
                return "unstable"
        return "weak"

    def interpretation(row: pd.Series) -> str:
        if row["feature"] == "ball_speed_mph":
            return "最稳定的首要因素，边际关联、条件贡献和非线性贡献均靠前。"
        if row["feature"] == "club_speed_mph":
            return "边际关联较强，但与球速存在信息重叠，控制球速后额外贡献下降。"
        if row["feature"] == "launch_angle_deg":
            return "线性边际关联较弱，但条件模型和非线性模型显示结构性贡献。"
        if row["feature"] == "attack_angle_deg":
            return "弱边际正相关，控制其他变量后独立贡献有限且方向/排名不稳定。"
        return "贡献取决于指标口径和模型类型，按分层结果解释。"

    summary["stability_category"] = summary.apply(category, axis=1)
    summary["final_interpretation"] = summary.apply(interpretation, axis=1)
    return summary[
        [
            "feature",
            "feature_label",
            "pearson",
            "spearman",
            "marginal_score",
            "marginal_rank",
            "ridge_coef",
            "ridge_abs_rank",
            "permutation_importance",
            "permutation_importance_std",
            "permutation_rank",
            "marginal_rank_interval",
            "marginal_top3_frequency",
            "marginal_top5_frequency",
            "stability_scope",
            "stability_category",
            "final_interpretation",
        ]
    ].sort_values(["marginal_rank", "ridge_abs_rank", "permutation_rank", "feature"]).reset_index(drop=True)


def _cv_regression_metrics(
    frame: pd.DataFrame,
    features: list[str],
    *,
    seed: int,
    cv_splits: int,
    cv_repeats: int,
    add_quadratic_launch_angle: bool = False,
) -> dict[str, float]:
    data = frame.dropna(subset=[*features, TARGET]).copy()
    X = data[features].to_numpy(dtype=float)
    if add_quadratic_launch_angle:
        theta = data["launch_angle_deg"].to_numpy(dtype=float)
        X = np.column_stack([theta, theta**2])
    y = data[TARGET].to_numpy(dtype=float)
    cv = RepeatedKFold(n_splits=cv_splits, n_repeats=cv_repeats, random_state=seed)
    rmse_values = []
    mae_values = []
    r2_values = []
    for train_idx, valid_idx in cv.split(X):
        model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LinearRegression())
        model.fit(X[train_idx], y[train_idx])
        pred = model.predict(X[valid_idx])
        rmse_values.append(math.sqrt(mean_squared_error(y[valid_idx], pred)))
        mae_values.append(mean_absolute_error(y[valid_idx], pred))
        r2_values.append(r2_score(y[valid_idx], pred))
    return {
        "n": int(len(data)),
        "rmse_mean": float(np.mean(rmse_values)),
        "rmse_std": float(np.std(rmse_values, ddof=1)),
        "mae_mean": float(np.mean(mae_values)),
        "mae_std": float(np.std(mae_values, ddof=1)),
        "r2_mean": float(np.mean(r2_values)),
        "r2_std": float(np.std(r2_values, ddof=1)),
    }


def speed_overlap_model_tables(
    clean: pd.DataFrame,
    *,
    seed: int,
    cv_splits: int,
    cv_repeats: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = clean[["ball_speed_mph", "club_speed_mph", TARGET]].dropna().copy()
    specs = [
        ("ball_speed_only", ["ball_speed_mph"], "Only ball speed."),
        ("club_speed_only", ["club_speed_mph"], "Only club speed after invalid zero correction."),
        ("ball_and_club_speed", ["ball_speed_mph", "club_speed_mph"], "Ball speed and club speed together."),
    ]
    X_all = {model_name: data[features].to_numpy(dtype=float) for model_name, features, _ in specs}
    y = data[TARGET].to_numpy(dtype=float)
    cv = RepeatedKFold(n_splits=cv_splits, n_repeats=cv_repeats, random_state=seed)
    fold_rows = []
    for fold_id, (train_idx, valid_idx) in enumerate(cv.split(data), start=1):
        for model_name, features, _ in specs:
            model = make_pipeline(StandardScaler(), LinearRegression())
            X = X_all[model_name]
            model.fit(X[train_idx], y[train_idx])
            pred = model.predict(X[valid_idx])
            fold_rows.append(
                {
                    "fold": fold_id,
                    "model": model_name,
                    "features": ";".join(features),
                    "n": int(len(data)),
                    "rmse": float(math.sqrt(mean_squared_error(y[valid_idx], pred))),
                    "mae": float(mean_absolute_error(y[valid_idx], pred)),
                    "r2": float(r2_score(y[valid_idx], pred)),
                }
            )
    fold_scores = pd.DataFrame(fold_rows)
    baseline = fold_scores[fold_scores["model"] == "ball_speed_only"][["fold", "rmse"]].rename(
        columns={"rmse": "baseline_rmse"}
    )
    fold_scores = fold_scores.merge(baseline, on="fold", how="left")
    fold_scores["delta_rmse_vs_ball_speed"] = fold_scores["rmse"] - fold_scores["baseline_rmse"]

    rows = []
    notes_by_model = {model_name: notes for model_name, _, notes in specs}
    for model_name, subset in fold_scores.groupby("model", sort=False):
        rows.append(
            {
                "model": model_name,
                "features": subset["features"].iloc[0],
                "n": int(subset["n"].iloc[0]),
                "fold_count": int(subset["fold"].nunique()),
                "rmse_mean": float(subset["rmse"].mean()),
                "rmse_std": float(subset["rmse"].std(ddof=1)),
                "mae_mean": float(subset["mae"].mean()),
                "mae_std": float(subset["mae"].std(ddof=1)),
                "r2_mean": float(subset["r2"].mean()),
                "r2_std": float(subset["r2"].std(ddof=1)),
                "paired_delta_rmse_vs_ball_speed": float(subset["delta_rmse_vs_ball_speed"].mean()),
                "paired_delta_rmse_std": float(subset["delta_rmse_vs_ball_speed"].std(ddof=1)),
                "paired_improvement_frequency": float((subset["delta_rmse_vs_ball_speed"] < 0).mean()),
                "notes": notes_by_model[model_name],
            }
        )
    return pd.DataFrame(rows), fold_scores


def speed_overlap_models(clean: pd.DataFrame, *, seed: int, cv_splits: int, cv_repeats: int) -> pd.DataFrame:
    summary, _ = speed_overlap_model_tables(clean, seed=seed, cv_splits=cv_splits, cv_repeats=cv_repeats)
    return summary


def launch_angle_quadratic_analysis(
    clean: pd.DataFrame,
    *,
    seed: int,
    cv_splits: int,
    cv_repeats: int,
) -> pd.DataFrame:
    rows = []
    for model_name, quadratic in [("linear_launch_angle", False), ("quadratic_launch_angle", True)]:
        metrics = _cv_regression_metrics(
            clean,
            ["launch_angle_deg"],
            seed=seed,
            cv_splits=cv_splits,
            cv_repeats=cv_repeats,
            add_quadratic_launch_angle=quadratic,
        )
        rows.append({"model": model_name, "features": "launch_angle_deg" + (";launch_angle_deg_squared" if quadratic else ""), **metrics})

    data = clean.dropna(subset=["launch_angle_deg", TARGET]).copy()
    theta = data["launch_angle_deg"].to_numpy(dtype=float)
    X_quad = np.column_stack([theta, theta**2])
    full_model = LinearRegression().fit(X_quad, data[TARGET].to_numpy(dtype=float))
    beta1 = float(full_model.coef_[0])
    beta2 = float(full_model.coef_[1])
    theta_star = float(-beta1 / (2 * beta2)) if abs(beta2) > 1e-12 else np.nan
    for row in rows:
        row["beta0_quadratic_full_sample"] = float(full_model.intercept_)
        row["beta1_quadratic_full_sample"] = beta1
        row["beta2_quadratic_full_sample"] = beta2
        row["theta_star_deg"] = theta_star
        row["theta_star_in_observed_range"] = bool(data["launch_angle_deg"].min() <= theta_star <= data["launch_angle_deg"].max())
    return pd.DataFrame(rows)


def save_processed_data(clean: pd.DataFrame, root: Path) -> Path:
    path = root / "data" / "processed" / "golf_shots_clean.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(path, index=False, float_format=CSV_FLOAT_FORMAT, lineterminator=CSV_LINE_TERMINATOR)
    return path


def save_all_tables(
    tables: dict[str, pd.DataFrame],
    *,
    question_dir: Path,
) -> dict[str, Path]:
    outputs = {}
    for stem, table in tables.items():
        outputs[stem] = save_table(table, stem=stem, question_dir=question_dir)["csv"]
    return outputs


def _pivot_correlation(table: pd.DataFrame) -> pd.DataFrame:
    return table.pivot(index="feature_label", columns="output_label", values="correlation")


def create_visualizations(
    *,
    clean: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    question_dir: Path,
    dpi: int,
) -> dict[str, dict[str, Path]]:
    outputs: dict[str, dict[str, Path]] = {}
    for method, stem, title in [
        ("pearson", "q1_pearson_heatmap", "Pearson input-output correlations"),
        ("spearman", "q1_spearman_heatmap", "Spearman input-output correlations"),
    ]:
        corr = tables[f"q1_{method}_correlation"]
        pivot = _pivot_correlation(corr)
        fig, ax = plt.subplots(figsize=(8, 5))
        image = ax.imshow(pivot.values, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=35, ha="right")
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
        for i in range(pivot.shape[0]):
            for j in range(pivot.shape[1]):
                ax.text(j, i, f"{pivot.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
        ax.set_title(title)
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        fig.tight_layout()
        outputs[stem] = save_figure_bundle(
            fig=fig,
            data=corr,
            stem=stem,
            question_dir=question_dir,
            title=title,
            source_script="questions/q1/scripts/visualize.py",
            notes="Correlation heatmap source data is in long form.",
            dpi=dpi,
        )
        plt.close(fig)

    summary = tables.get("q1_feature_summary", tables["q1_feature_ranking"])
    ranking = tables["q1_feature_ranking"]
    top_features = summary.head(4)["feature"].tolist()
    scatter_rows = []
    fig, axes = plt.subplots(2, 2, figsize=(9, 7))
    for ax, feature in zip(axes.ravel(), top_features, strict=True):
        subset = clean[[feature, TARGET]].dropna().copy()
        subset["feature"] = feature
        subset["feature_label"] = FEATURE_LABELS[feature]
        scatter_rows.append(subset.rename(columns={feature: "x", TARGET: "carry_distance_yd"}))
        ax.scatter(subset[feature], subset[TARGET], s=12, alpha=0.45)
        bins = pd.qcut(subset[feature], q=min(12, subset[feature].nunique()), duplicates="drop")
        trend = subset.groupby(bins, observed=True).agg(x=(feature, "median"), y=(TARGET, "mean"))
        ax.plot(trend["x"], trend["y"], color="black", linewidth=1.5)
        ax.set_title(FEATURE_LABELS[feature])
        ax.set_xlabel(FEATURE_LABELS[feature])
        ax.set_ylabel("Carry distance (yd)")
    fig.tight_layout()
    outputs["q1_top_feature_relationships"] = save_figure_bundle(
        fig=fig,
        data=pd.concat(scatter_rows, ignore_index=True),
        stem="q1_top_feature_relationships",
        question_dir=question_dir,
        title="Top feature relationships with carry distance",
        source_script="questions/q1/scripts/visualize.py",
        notes="Scatter source rows for the top four ranked features.",
        dpi=dpi,
    )
    plt.close(fig)

    raw_importance = summary.head(9).copy()
    raw_importance["abs_ridge_coef"] = raw_importance["ridge_coef"].abs()
    importance = raw_importance.melt(
        id_vars=["feature", "feature_label"],
        value_vars=["marginal_score", "abs_ridge_coef", "permutation_importance"],
        var_name="method",
        value_name="value",
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    x_labels = raw_importance["feature_label"].tolist()
    x = np.arange(len(x_labels))
    width = 0.24
    for offset, method in enumerate(["marginal_score", "abs_ridge_coef", "permutation_importance"]):
        values = (
            importance[importance["method"] == method]
            .set_index("feature_label")
            .loc[x_labels, "value"]
            .to_numpy()
        )
        ax.bar(x + (offset - 1) * width, values, width=width, label=method)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=35, ha="right")
    ax.set_ylabel("Raw method value")
    ax.set_title("Raw importance comparison")
    ax.legend()
    fig.tight_layout()
    outputs["q1_raw_importance_comparison"] = save_figure_bundle(
        fig=fig,
        data=importance,
        stem="q1_raw_importance_comparison",
        question_dir=question_dir,
        title="Raw method importance comparison",
        source_script="questions/q1/scripts/visualize.py",
        notes="Raw values are shown separately; they are not averaged into one unique ranking.",
        dpi=dpi,
    )
    plt.close(fig)

    if {"pearson_score", "spearman_score", "ridge_score", "permutation_score"}.issubset(ranking.columns):
        normalized = ranking.head(9).melt(
            id_vars=["feature", "feature_label"],
            value_vars=["pearson_score", "spearman_score", "ridge_score", "permutation_score"],
            var_name="method",
            value_name="score",
        )
        fig, ax = plt.subplots(figsize=(9, 5))
        x_labels = ranking.head(9)["feature_label"].tolist()
        x = np.arange(len(x_labels))
        width = 0.18
        for offset, method in enumerate(
            ["pearson_score", "spearman_score", "ridge_score", "permutation_score"]
        ):
            values = (
                normalized[normalized["method"] == method]
                .set_index("feature_label")
                .loc[x_labels, "score"]
                .to_numpy()
            )
            ax.bar(x + (offset - 1.5) * width, values, width=width, label=method.replace("_score", ""))
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=35, ha="right")
        ax.set_ylabel("Rank-normalized score")
        ax.set_title("Legacy method score comparison")
        ax.legend()
        fig.tight_layout()
        outputs["q1_importance_comparison"] = save_figure_bundle(
            fig=fig,
            data=normalized,
            stem="q1_importance_comparison",
            question_dir=question_dir,
            title="Legacy method score comparison",
            source_script="questions/q1/scripts/visualize.py",
            notes="Compatibility figure; final interpretation uses q1_feature_summary.csv.",
            dpi=dpi,
        )
        plt.close(fig)

    stability = tables["q1_rank_stability"].merge(
        summary[["feature", "feature_label", "marginal_rank"]], on="feature", how="left"
    )
    stability = stability.sort_values("marginal_rank")
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(stability))
    ax.errorbar(
        stability["marginal_rank_median"],
        y,
        xerr=[
            stability["marginal_rank_median"] - stability["marginal_rank_ci_low"],
            stability["marginal_rank_ci_high"] - stability["marginal_rank_median"],
        ],
        fmt="o",
        capsize=3,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(stability["feature_label"])
    ax.invert_yaxis()
    ax.set_xlabel("Bootstrap rank interval")
    ax.set_title("Marginal rank stability")
    fig.tight_layout()
    outputs["q1_rank_stability"] = save_figure_bundle(
        fig=fig,
        data=stability,
        stem="q1_rank_stability",
        question_dir=question_dir,
        title="Bootstrap marginal rank stability",
        source_script="questions/q1/scripts/visualize.py",
        notes="Intervals only use marginal Pearson/Spearman bootstrap ranking.",
        dpi=dpi,
    )
    plt.close(fig)

    groups = tables["q1_group_importance"].sort_values("rank")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(groups["group"], groups["importance_mean"])
    ax.invert_yaxis()
    ax.set_xlabel("RMSE increase after group permutation")
    ax.set_title("Group permutation importance")
    fig.tight_layout()
    outputs["q1_group_importance"] = save_figure_bundle(
        fig=fig,
        data=groups,
        stem="q1_group_importance",
        question_dir=question_dir,
        title="Group permutation importance",
        source_script="questions/q1/scripts/visualize.py",
        notes="Groups are permuted as blocks on validation samples.",
        dpi=dpi,
    )
    plt.close(fig)

    sensitivity = tables["q1_sensitivity_comparison"].copy()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(sensitivity["scenario"], sensitivity["spearman_with_main_rank"].fillna(0.0))
    ax.set_ylim(-1, 1)
    ax.set_ylabel("Spearman rank correlation")
    ax.set_title("Sensitivity scenarios versus main ranking")
    ax.tick_params(axis="x", labelrotation=35)
    fig.tight_layout()
    outputs["q1_sensitivity_comparison"] = save_figure_bundle(
        fig=fig,
        data=sensitivity,
        stem="q1_sensitivity_comparison",
        question_dir=question_dir,
        title="Sensitivity scenario comparison",
        source_script="questions/q1/scripts/visualize.py",
        notes="Scenario ranking is compared with the main feature summary rank.",
        dpi=dpi,
    )
    plt.close(fig)
    return outputs


def run_analysis(
    *,
    root: Path,
    config_path: str | Path = "configs/default.yaml",
    bootstrap_iterations: int | None = None,
    cv_splits: int | None = None,
    cv_repeats: int | None = None,
    permutation_repeats: int | None = None,
    create_figures: bool = True,
) -> dict[str, Any]:
    config = load_config(root, config_path)
    qcfg = q1_config(config)
    seed = random_seed(config)
    bootstrap_iterations = int(bootstrap_iterations or qcfg.get("bootstrap", {}).get("iterations", 500))
    cv_splits = int(cv_splits or qcfg.get("cross_validation", {}).get("folds", 5))
    cv_repeats = int(cv_repeats or qcfg.get("cross_validation", {}).get("repeats", 5))
    permutation_repeats = int(
        permutation_repeats or qcfg.get("permutation_importance", {}).get("repeats", 5)
    )
    question_dir = root / "questions" / "q1"
    raw_canonical = load_data(root)
    clean, invalid_zero_records = replace_invalid_zero_values(raw_canonical)
    processed_path = save_processed_data(clean, root)
    views = build_sample_views(clean)
    correlations = compute_correlations(clean, INPUT_FEATURES, OUTPUT_COLUMNS)
    model_summary, cv_scores, ridge_coefficients, permutation_importance = model_importance_tables(
        views,
        seed=seed,
        cv_splits=cv_splits,
        cv_repeats=cv_repeats,
        permutation_repeats=permutation_repeats,
    )
    method_table = method_importance_table(correlations, model_summary)
    correlation_ci = bootstrap_correlation_intervals(clean, seed=seed, iterations=bootstrap_iterations)
    ci_wide = (
        correlation_ci.pivot(index=["feature", "output"], columns="method", values=["estimate", "ci_low", "ci_high"])
        .reset_index()
    )
    ci_wide.columns = [
        "_".join([str(part) for part in col if part]).strip("_") if isinstance(col, tuple) else str(col)
        for col in ci_wide.columns
    ]
    ci_wide = ci_wide.rename(
        columns={
            "output": "target",
            "estimate_pearson": "pearson",
            "ci_low_pearson": "pearson_ci_low",
            "ci_high_pearson": "pearson_ci_high",
            "estimate_spearman": "spearman",
            "ci_low_spearman": "spearman_ci_low",
            "ci_high_spearman": "spearman_ci_high",
        }
    )
    n_lookup = correlations["pearson"][["feature", "output", "n"]].rename(columns={"output": "target"})
    ci_wide = ci_wide.merge(n_lookup, on=["feature", "target"], how="left")
    ci_wide = ci_wide[
        [
            "feature",
            "target",
            "n",
            "pearson",
            "pearson_ci_low",
            "pearson_ci_high",
            "spearman",
            "spearman_ci_low",
            "spearman_ci_high",
        ]
    ]
    rank_stability = bootstrap_rank_stability(clean, seed=seed, iterations=bootstrap_iterations)
    feature_ranking = aggregate_rankings(method_table, rank_stability)
    feature_summary = feature_summary_table(method_table, rank_stability)
    sensitivity = sensitivity_comparison(clean, feature_summary)
    group_table = group_importance(
        clean,
        seed=seed,
        cv_splits=cv_splits,
        cv_repeats=cv_repeats,
        permutation_repeats=permutation_repeats,
    )
    outliers = outlier_flags(clean)
    outlier_summary = outlier_audit(clean)
    sample_definitions = sample_definition_comparison(clean)
    spin_comparison = spin_representation_comparison(cv_scores)
    speed_overlap, speed_overlap_folds = speed_overlap_model_tables(
        clean,
        seed=seed,
        cv_splits=cv_splits,
        cv_repeats=cv_repeats,
    )
    launch_quadratic = launch_angle_quadratic_analysis(
        clean,
        seed=seed,
        cv_splits=cv_splits,
        cv_repeats=cv_repeats,
    )

    tables = {
        "q1_data_audit": generate_data_audit(raw_canonical, clean, invalid_zero_records),
        "q1_missing_audit": missing_audit_table(clean),
        "q1_invalid_zero_records": invalid_zero_records,
        "q1_outlier_audit": outlier_summary,
        "q1_outlier_flags": outliers,
        "q1_pearson_correlation": correlations["pearson"],
        "q1_spearman_correlation": correlations["spearman"],
        "q1_kendall_correlation": correlations["kendall"],
        "q1_correlation_matrix": pd.concat(
            [correlations["pearson"].assign(method="pearson"), correlations["spearman"].assign(method="spearman")],
            ignore_index=True,
        ),
        "q1_correlation_confidence_intervals": ci_wide,
        "q1_correlation_confidence_intervals_long": correlation_ci,
        "q1_model_cv_scores": cv_scores,
        "q1_model_performance": cv_scores,
        "q1_ridge_coefficients": ridge_coefficients,
        "q1_permutation_importance": permutation_importance,
        "q1_method_importance": method_table,
        "q1_feature_summary": feature_summary,
        "q1_feature_ranking": feature_ranking,
        "q1_feature_importance": feature_ranking,
        "q1_group_importance": group_table,
        "q1_sensitivity_comparison": sensitivity,
        "q1_spin_representation_comparison": spin_comparison,
        "q1_sample_definition_comparison": sample_definitions,
        "q1_speed_overlap_models": speed_overlap,
        "q1_speed_overlap_fold_scores": speed_overlap_folds,
        "q1_launch_angle_quadratic": launch_quadratic,
        "q1_rank_stability": rank_stability,
    }
    table_outputs = save_all_tables(tables, question_dir=question_dir)
    figure_outputs = {}
    if create_figures:
        figure_outputs = create_visualizations(
            clean=clean,
            tables=tables,
            question_dir=question_dir,
            dpi=int(config.get("plot", {}).get("dpi", 300)),
        )

    run_summary = {
        "seed": seed,
        "rows": int(len(clean)),
        "features": INPUT_FEATURES,
        "outputs": OUTPUT_COLUMNS,
        "summary_order_features": feature_summary.head(5)["feature"].tolist(),
        "stable_key_features": feature_summary.loc[
            feature_summary["stability_category"] == "stable_key", "feature"
        ].tolist(),
        "tables": {key: str(path.relative_to(root)) for key, path in table_outputs.items()},
        "figures": {
            key: {subkey: str(path.relative_to(root)) for subkey, path in paths.items()}
            for key, paths in figure_outputs.items()
        },
    }
    summary_path = question_dir / "artifacts" / "tables" / "q1_run_summary.json"
    write_json(summary_path, run_summary)

    metadata = {
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "git_commit": current_git_commit(root),
        "data_path": str(processed_path.relative_to(root)),
        "data_hash": file_sha256(processed_path),
        "config_path": str((root / config_path).relative_to(root)),
        "config_hash": file_sha256(root / config_path),
        "random_seed": seed,
        "python_version": platform.python_version(),
        "package_versions": package_versions(),
        "sample_sizes": {name: int(len(view.frame)) for name, view in views.items()},
        "invalid_zero_corrections": {
            "club_speed_mph": int(invalid_zero_records["club_speed_invalid_zero"].sum()),
            "attack_angle_deg": int(invalid_zero_records["attack_angle_invalid_zero"].sum()),
            "record_ids": invalid_zero_records["record_id"].astype(int).tolist(),
        },
        "selected_spin_representation": "A: spin_rate_rpm + spin_axis_deg",
        "selected_nonlinear_model": "ExtraTreesRegressor",
        "table_hashes": {
            key: file_sha256(path)
            for key, path in table_outputs.items()
            if path.name != "q1_validation_checks.csv"
        },
    }
    metadata_path = question_dir / "artifacts" / "run_metadata.json"
    write_json(metadata_path, metadata)

    checks = validate_outputs(root, require_validation_table=False)
    save_table(checks, stem="q1_validation_checks", question_dir=question_dir)
    failed = checks[~checks["passed"]]
    if not failed.empty:
        raise RuntimeError(f"q1 validation failed after pipeline run: {failed['check'].tolist()}")
    return {
        "clean": clean,
        "tables": tables,
        "table_outputs": table_outputs,
        "figure_outputs": figure_outputs,
        "metadata": metadata,
        "run_summary": run_summary,
    }


def validate_outputs(root: Path, *, require_validation_table: bool = True) -> pd.DataFrame:
    question_dir = root / "questions" / "q1"
    required_tables = [
        "q1_data_audit.csv",
        "q1_missing_audit.csv",
        "q1_invalid_zero_records.csv",
        "q1_outlier_audit.csv",
        "q1_outlier_flags.csv",
        "q1_pearson_correlation.csv",
        "q1_spearman_correlation.csv",
        "q1_correlation_confidence_intervals.csv",
        "q1_model_performance.csv",
        "q1_ridge_coefficients.csv",
        "q1_permutation_importance.csv",
        "q1_method_importance.csv",
        "q1_feature_summary.csv",
        "q1_feature_ranking.csv",
        "q1_group_importance.csv",
        "q1_sensitivity_comparison.csv",
        "q1_spin_representation_comparison.csv",
        "q1_sample_definition_comparison.csv",
        "q1_speed_overlap_models.csv",
        "q1_speed_overlap_fold_scores.csv",
        "q1_launch_angle_quadratic.csv",
        "q1_rank_stability.csv",
    ]
    if require_validation_table:
        required_tables.append("q1_validation_checks.csv")
    required_figures = [
        "q1_pearson_heatmap",
        "q1_spearman_heatmap",
        "q1_top_feature_relationships",
        "q1_raw_importance_comparison",
        "q1_importance_comparison",
        "q1_rank_stability",
        "q1_group_importance",
        "q1_sensitivity_comparison",
    ]
    rows = []
    tables_dir = question_dir / "artifacts" / "tables"

    def add(check: str, kind: str, path: Path | None, passed: bool, details: str = "") -> None:
        rows.append(
            {
                "check": check,
                "kind": kind,
                "path": str(path.relative_to(root)) if path is not None and path.exists() else str(path.relative_to(root)) if path is not None else "",
                "passed": bool(passed),
                "details": details,
            }
        )

    for filename in required_tables:
        path = tables_dir / filename
        add(filename, "table", path, path.exists() and path.stat().st_size > 0)
    for stem in required_figures:
        for suffix, kind in [(".png", "figure"), (".csv", "figure_data"), (".meta.json", "figure_metadata")]:
            base_dir = "figures" if suffix == ".png" else "figure_data"
            path = question_dir / "artifacts" / base_dir / f"{stem}{suffix}"
            add(f"{stem}{suffix}", kind, path, path.exists() and path.stat().st_size > 0)

    processed = root / "data" / "processed" / "golf_shots_clean.csv"
    if processed.exists():
        clean = pd.read_csv(processed)
        add("processed_row_count", "schema", processed, len(clean) == 735, f"rows={len(clean)}")
        add("record_id_unique", "schema", processed, clean["record_id"].is_unique)
        numeric = clean.drop(columns=["record_id"]).to_numpy(dtype=float)
        add("processed_no_inf", "numeric", processed, not np.isinf(numeric).any())
        add(
            "invalid_zero_fields_are_missing",
            "numeric",
            processed,
            clean["club_speed_mph"].isna().sum() == 66
            and clean["attack_angle_deg"].isna().sum() == 68
            and not clean["club_speed_mph"].eq(0).any()
            and not clean["attack_angle_deg"].eq(0).any(),
        )
    else:
        add("processed_row_count", "schema", processed, False, "processed data missing")

    invalid_path = tables_dir / "q1_invalid_zero_records.csv"
    if invalid_path.exists():
        invalid = pd.read_csv(invalid_path)
        add("invalid_zero_record_count", "numeric", invalid_path, set(invalid["record_id"]) == {225, 226, 308})

    ci_path = tables_dir / "q1_correlation_confidence_intervals.csv"
    if ci_path.exists():
        ci = pd.read_csv(ci_path)
        corr_cols = ["pearson", "spearman", "pearson_ci_low", "pearson_ci_high", "spearman_ci_low", "spearman_ci_high"]
        if set(corr_cols).issubset(ci.columns):
            in_range = ci[corr_cols].apply(lambda s: s.between(-1, 1).all()).all()
            ordered = (ci["pearson_ci_low"] <= ci["pearson_ci_high"]).all() and (
                ci["spearman_ci_low"] <= ci["spearman_ci_high"]
            ).all()
        else:
            in_range = False
            ordered = False
        add("correlation_values_in_range", "numeric", ci_path, bool(in_range))
        add("correlation_ci_ordered", "numeric", ci_path, bool(ordered))
        target_col = "target" if "target" in ci.columns else "output" if "output" in ci.columns else ""
        pearson_col = "pearson" if "pearson" in ci.columns else "estimate" if "estimate" in ci.columns else ""
        ball = ci[(ci["feature"] == "ball_speed_mph") & (ci[target_col] == TARGET)] if target_col else pd.DataFrame()
        club = ci[(ci["feature"] == "club_speed_mph") & (ci[target_col] == TARGET)] if target_col else pd.DataFrame()
        add(
            "ball_speed_carry_positive",
            "numeric",
            ci_path,
            bool(pearson_col) and not ball.empty and float(ball[pearson_col].iloc[0]) > 0.7,
        )
        add(
            "club_speed_zero_fix_lifts_pearson",
            "numeric",
            ci_path,
            bool(pearson_col) and not club.empty and float(club[pearson_col].iloc[0]) > 0.5,
        )

    summary_path = tables_dir / "q1_feature_summary.csv"
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        required = {
            "feature",
            "marginal_rank",
            "ridge_abs_rank",
            "permutation_rank",
            "stability_category",
            "final_interpretation",
        }
        add("feature_summary_schema", "schema", summary_path, required.issubset(summary.columns))
        add("feature_summary_no_aggregate_score", "schema", summary_path, "aggregate_score" not in summary.columns)
        attack = summary.loc[summary["feature"] == "attack_angle_deg"]
        add(
            "attack_angle_not_stable_key",
            "numeric",
            summary_path,
            not attack.empty and attack["stability_category"].iloc[0] != "stable_key",
        )

    model_path = tables_dir / "q1_model_performance.csv"
    if model_path.exists():
        perf = pd.read_csv(model_path)
        add("model_metrics_not_nan", "numeric", model_path, perf[["rmse", "mae", "r2"]].notna().all().all())

    sensitivity_path = tables_dir / "q1_sensitivity_comparison.csv"
    if sensitivity_path.exists():
        sensitivity = pd.read_csv(sensitivity_path)
        if {"scenario", "n", "ranked_n", "analysis_type"}.issubset(sensitivity.columns):
            s3 = sensitivity.loc[sensitivity["scenario"] == "S3_imputed"]
            passed = (
                not s3.empty
                and int(s3["n"].iloc[0]) == 735
                and int(s3["ranked_n"].iloc[0]) == 735
                and s3["analysis_type"].iloc[0] == "descriptive_imputed_marginal"
            )
        else:
            passed = False
        add("s3_sensitivity_ranked_n_matches_reported_n", "numeric", sensitivity_path, passed)

    speed_path = tables_dir / "q1_speed_overlap_models.csv"
    speed_folds_path = tables_dir / "q1_speed_overlap_fold_scores.csv"
    if speed_path.exists():
        speed = pd.read_csv(speed_path)
        same_sample = "n" in speed.columns and speed["n"].nunique() == 1 and int(speed["n"].iloc[0]) == 669
        add("speed_overlap_same_sample", "numeric", speed_path, bool(same_sample))
    if speed_folds_path.exists():
        speed_folds = pd.read_csv(speed_folds_path)
        paired = (
            {"fold", "model"}.issubset(speed_folds.columns)
            and speed_folds.groupby("fold")["model"].nunique().nunique() == 1
            and int(speed_folds.groupby("fold")["model"].nunique().iloc[0]) == 3
        )
        add("speed_overlap_paired_folds", "numeric", speed_folds_path, bool(paired))

    group_path = tables_dir / "q1_group_importance.csv"
    if group_path.exists():
        groups = pd.read_csv(group_path)
        repeated = {"fold_count", "importance_std", "positive_frequency"}.issubset(groups.columns) and (
            groups["fold_count"].min() >= 25
        ) and (groups["importance_std"] > 0).all()
        block = "block_permutation" in groups.columns and groups["block_permutation"].astype(bool).all()
        add("group_importance_repeated_cv", "numeric", group_path, bool(repeated))
        add("group_importance_block_permutation", "schema", group_path, bool(block))

    stability_path = tables_dir / "q1_rank_stability.csv"
    if stability_path.exists():
        stability = pd.read_csv(stability_path)
        required = {
            "marginal_rank_interval",
            "marginal_top3_frequency",
            "marginal_top5_frequency",
            "stability_scope",
        }
        scoped = required.issubset(stability.columns) and set(stability["stability_scope"]) == {
            "marginal_correlation_bootstrap"
        }
        add("rank_stability_marginal_scope", "schema", stability_path, bool(scoped))

    ridge_path = tables_dir / "q1_ridge_coefficients.csv"
    if ridge_path.exists():
        ridge = pd.read_csv(ridge_path)
        repeated = {"ridge_fold_count", "ridge_coef_std"}.issubset(ridge.columns) and (
            ridge["ridge_fold_count"].min() >= 25
        ) and (ridge["ridge_coef_std"] > 0).any()
        add("ridge_coefficients_repeated_estimates", "numeric", ridge_path, bool(repeated))

    ranking_path = tables_dir / "q1_feature_ranking.csv"
    if ranking_path.exists():
        ranking = pd.read_csv(ranking_path)
        deprecated = {"deprecated", "not_for_final_conclusion"}.issubset(ranking.columns) and (
            ranking["deprecated"].astype(bool).all()
        ) and ranking["not_for_final_conclusion"].astype(bool).all()
        add("legacy_ranking_deprecated", "schema", ranking_path, bool(deprecated))

    metadata_path = question_dir / "artifacts" / "run_metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        add("run_metadata_exists", "metadata", metadata_path, True)
        add("run_metadata_has_config_hash", "metadata", metadata_path, bool(metadata.get("config_hash")))
        add(
            "run_metadata_has_table_hashes",
            "reproducibility",
            metadata_path,
            bool(metadata.get("table_hashes")),
        )
    else:
        add("run_metadata_exists", "metadata", metadata_path, False)
        add("run_metadata_has_table_hashes", "reproducibility", metadata_path, False)

    return pd.DataFrame(rows)
