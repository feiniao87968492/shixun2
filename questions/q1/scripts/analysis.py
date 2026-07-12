#!/usr/bin/env python3
"""Q1 data audit, correlation analysis, ranking, and visualization helpers."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import RepeatedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.artifacts import save_figure_bundle, save_table  # noqa: E402

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
    return int(config.get("runtime", {}).get("random_seed", 2026))


def load_raw_golf_data(root: Path) -> pd.DataFrame:
    """Load the Excel attachment using the real header row."""
    path = root / RAW_RELATIVE_PATH
    if not path.exists():
        raise FileNotFoundError(f"Raw Excel attachment not found: {path}")
    return pd.read_excel(path, sheet_name=SHEET_NAME, header=2, na_values=[""])


def clean_golf_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Rename fields, coerce numerics, and keep raw values otherwise unchanged."""
    missing = [column for column in RAW_TO_CANONICAL if column not in raw.columns]
    if missing:
        raise ValueError(f"Missing expected raw columns: {missing}")

    clean = raw.rename(columns=RAW_TO_CANONICAL)[list(RAW_TO_CANONICAL.values())].copy()
    for column in clean.columns:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    clean = clean.dropna(subset=["record_id"]).copy()
    clean["record_id"] = clean["record_id"].astype(int)
    clean = clean.sort_values("record_id").reset_index(drop=True)
    if clean["record_id"].duplicated().any():
        duplicates = clean.loc[clean["record_id"].duplicated(), "record_id"].tolist()
        raise ValueError(f"Duplicate record_id values: {duplicates[:10]}")
    return clean


def with_missing_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for source, indicator in [
        ("club_speed_mph", "club_speed_missing"),
        ("attack_angle_deg", "attack_angle_missing"),
    ]:
        out[indicator] = out[source].isna().astype(int)
        median = out[source].median(skipna=True)
        out[source] = out[source].fillna(median)
    return out


def build_sample_views(clean: pd.DataFrame) -> dict[str, SampleView]:
    """Create S1/S2/S3 and spin-component sensitivity modeling views."""
    s1 = clean.dropna(subset=CORE_FEATURES + [TARGET]).copy()
    s2 = clean.dropna(subset=PRIMARY_FEATURES + [TARGET]).copy()
    s3 = with_missing_indicators(clean)
    s3 = s3.dropna(subset=PRIMARY_FEATURES + MISSING_INDICATORS + [TARGET]).copy()

    s3_spin_components = with_missing_indicators(clean)
    s3_spin_components = s3_spin_components.dropna(
        subset=SPIN_COMPONENT_FEATURES + MISSING_INDICATORS + [TARGET]
    ).copy()

    return {
        "S1_core": SampleView(
            "S1_core",
            s1,
            CORE_FEATURES,
            "Core sample: no club speed or attack angle, spin represented by rate and axis.",
        ),
        "S2_complete": SampleView(
            "S2_complete",
            s2,
            PRIMARY_FEATURES,
            "Complete-case sample: all primary features observed.",
        ),
        "S3_imputed": SampleView(
            "S3_imputed",
            s3,
            PRIMARY_FEATURES + MISSING_INDICATORS,
            "Primary full-variable sample with median imputation and missing indicators.",
        ),
        "S3_spin_components": SampleView(
            "S3_spin_components",
            s3_spin_components,
            SPIN_COMPONENT_FEATURES + MISSING_INDICATORS,
            "Sensitivity sample using backspin and sidespin instead of spin rate and axis.",
        ),
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


def _ridge_coefficients(view: SampleView) -> pd.DataFrame:
    X = view.frame[view.features]
    y = view.frame[TARGET]
    alphas = np.logspace(-3, 3, 25)
    model = make_pipeline(StandardScaler(), RidgeCV(alphas=alphas))
    model.fit(X, y)
    ridge = model.named_steps["ridgecv"]
    scaler = model.named_steps["standardscaler"]
    coefficients = ridge.coef_ / scaler.scale_
    standardized_coefficients = ridge.coef_
    return pd.DataFrame(
        {
            "feature": view.features,
            "ridge_coef": standardized_coefficients,
            "ridge_coef_original_scale": coefficients,
            "ridge_alpha": float(ridge.alpha_),
            "sample_view": view.name,
        }
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
    scores = []

    for fold_id, (train_idx, valid_idx) in enumerate(cv.split(X), start=1):
        model = ExtraTreesRegressor(
            n_estimators=160,
            min_samples_leaf=3,
            random_state=seed + fold_id,
            n_jobs=-1,
        )
        model.fit(X[train_idx], y[train_idx])
        original_pred = model.predict(X[valid_idx])
        original_rmse = math.sqrt(mean_squared_error(y[valid_idx], original_pred))
        scores.append({"sample_view": view.name, "fold": fold_id, "rmse": original_rmse})
        for feature_idx, feature in enumerate(view.features):
            deltas = []
            for _ in range(permutation_repeats):
                X_perm = X[valid_idx].copy()
                X_perm[:, feature_idx] = rng.permutation(X_perm[:, feature_idx])
                rmse = math.sqrt(mean_squared_error(y[valid_idx], model.predict(X_perm)))
                deltas.append(rmse - original_rmse)
            importance[feature].append(float(np.mean(deltas)))

    rows = []
    for feature, values in importance.items():
        rows.append(
            {
                "feature": feature,
                "sample_view": view.name,
                "permutation_importance": float(np.mean(values)),
                "permutation_importance_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
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
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute ridge and nonlinear permutation importance without duplicating spin encodings."""
    detail_frames = []
    score_frames = []
    for key in ["S3_imputed", "S3_spin_components"]:
        view = views[key]
        ridge = _ridge_coefficients(view)
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
    return summary, pd.concat(score_frames, ignore_index=True)


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
                "rank_median": float(np.median(arr)),
                "rank_ci_low": int(np.quantile(arr, 0.025, method="nearest")),
                "rank_ci_high": int(np.quantile(arr, 0.975, method="nearest")),
                "rank_interval": f"{int(np.quantile(arr, 0.025, method='nearest'))}-{int(np.quantile(arr, 0.975, method='nearest'))}",
                "top3_frequency": float(np.mean(arr <= 3)),
                "top5_frequency": float(np.mean(arr <= 5)),
                "iterations": iterations,
            }
        )
    return pd.DataFrame(rows).sort_values(["rank_median", "feature"]).reset_index(drop=True)


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
        stability = stability.copy()
        if "top5_frequency" not in stability.columns:
            stability["top5_frequency"] = np.nan
        ranking = ranking.merge(
            stability[["feature", "rank_interval", "top3_frequency", "top5_frequency"]],
            on="feature",
            how="left",
        )
    else:
        ranking["rank_interval"] = ""
        ranking["top3_frequency"] = np.nan
        ranking["top5_frequency"] = np.nan

    def direction(row: pd.Series) -> str:
        value = row["pearson"] if abs(row["pearson"]) >= abs(row["spearman"]) else row["spearman"]
        if abs(value) < 0.1:
            return "weak"
        return "positive" if value > 0 else "negative"

    def stability_label(row: pd.Series) -> str:
        interval = str(row.get("rank_interval", ""))
        width = 99
        if "-" in interval:
            low, high = interval.split("-", 1)
            width = int(high) - int(low)
        top3 = row.get("top3_frequency", 0.0)
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
        "rank_interval",
        "top3_frequency",
        "top5_frequency",
        "direction",
        "stability",
    ]
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


def sensitivity_comparison(clean: pd.DataFrame, main_ranking: pd.DataFrame) -> pd.DataFrame:
    scenarios: list[tuple[str, pd.DataFrame, list[str], str]] = []
    views = build_sample_views(clean)
    scenarios.append(("S1_core", views["S1_core"].frame, views["S1_core"].features, "No club speed or attack angle."))
    scenarios.append(("S2_complete", views["S2_complete"].frame, views["S2_complete"].features, "Complete-case primary variables."))
    scenarios.append(("S3_imputed", views["S3_imputed"].frame, PRIMARY_FEATURES, "Median imputation plus missing indicators."))
    scenarios.append(
        (
            "S3_spin_components",
            views["S3_spin_components"].frame,
            SPIN_COMPONENT_FEATURES,
            "Backspin and sidespin representation.",
        )
    )

    continuous = INPUT_FEATURES + OUTPUT_COLUMNS
    low = clean[continuous].quantile(0.01)
    high = clean[continuous].quantile(0.99)
    mask = clean[continuous].ge(low).all(axis=1) & clean[continuous].le(high).all(axis=1)
    scenarios.append(("trim_1pct", clean[mask].copy(), PRIMARY_FEATURES, "Rows outside 1%-99% range removed."))

    winsorized = clean.copy()
    for column in continuous:
        winsorized[column] = winsorized[column].clip(low[column], high[column])
    scenarios.append(("winsorized_1pct", winsorized, PRIMARY_FEATURES, "Continuous variables clipped to 1%-99%."))

    main_order = main_ranking.set_index("feature")["final_rank"]
    rows = []
    for name, frame, features, notes in scenarios:
        available = [feature for feature in features if feature in frame.columns]
        ranked = _rank_by_marginal(frame.dropna(subset=[*available, TARGET]), available)
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
                "feature_count": int(len(available)),
                "top3": ";".join(top3),
                "top5": ";".join(top5),
                "spearman_with_main_rank": rho,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def group_importance(clean: pd.DataFrame, *, seed: int) -> pd.DataFrame:
    views = build_sample_views(clean)
    rows = []
    group_specs = [
        ("speed_group", "S3_imputed", ["ball_speed_mph", "club_speed_mph"]),
        ("launch_attitude_group", "S3_imputed", ["launch_angle_deg", "attack_angle_deg"]),
        ("horizontal_direction_group", "S3_imputed", ["launch_direction_deg"]),
        ("spin_state_group_A", "S3_imputed", ["spin_rate_rpm", "spin_axis_deg"]),
        ("spin_state_group_B", "S3_spin_components", ["backspin_rpm", "sidespin_rpm"]),
    ]
    rng = np.random.default_rng(seed)
    for group, view_name, features in group_specs:
        view = views[view_name]
        X = view.frame[view.features].to_numpy(dtype=float)
        y = view.frame[TARGET].to_numpy(dtype=float)
        train_idx, valid_idx = train_test_split(
            np.arange(len(view.frame)), test_size=0.30, random_state=seed
        )
        model = ExtraTreesRegressor(n_estimators=200, min_samples_leaf=3, random_state=seed, n_jobs=-1)
        model.fit(X[train_idx], y[train_idx])
        original_rmse = math.sqrt(mean_squared_error(y[valid_idx], model.predict(X[valid_idx])))
        X_perm = X[valid_idx].copy()
        feature_indexes = [view.features.index(feature) for feature in features]
        for feature_idx in feature_indexes:
            X_perm[:, feature_idx] = rng.permutation(X_perm[:, feature_idx])
        permuted_rmse = math.sqrt(mean_squared_error(y[valid_idx], model.predict(X_perm)))
        rows.append(
            {
                "group": group,
                "sample_view": view_name,
                "features": ";".join(features),
                "original_rmse": original_rmse,
                "permuted_rmse": permuted_rmse,
                "group_importance": permuted_rmse - original_rmse,
            }
        )
    result = pd.DataFrame(rows)
    result["rank"] = _rank_desc(result["group_importance"].clip(lower=0))
    return result.sort_values("rank").reset_index(drop=True)


def save_processed_data(clean: pd.DataFrame, root: Path) -> Path:
    path = root / "data" / "processed" / "golf_shots_clean.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(path, index=False)
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

    ranking = tables["q1_feature_ranking"]
    top_features = ranking.head(4)["feature"].tolist()
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

    importance = ranking.head(9).melt(
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
            importance[importance["method"] == method]
            .set_index("feature_label")
            .loc[x_labels, "score"]
            .to_numpy()
        )
        ax.bar(x + (offset - 1.5) * width, values, width=width, label=method.replace("_score", ""))
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=35, ha="right")
    ax.set_ylabel("Rank-normalized score")
    ax.set_title("Method importance comparison")
    ax.legend()
    fig.tight_layout()
    outputs["q1_importance_comparison"] = save_figure_bundle(
        fig=fig,
        data=importance,
        stem="q1_importance_comparison",
        question_dir=question_dir,
        title="Method importance comparison",
        source_script="questions/q1/scripts/visualize.py",
        notes="Scores are rank-normalized per method.",
        dpi=dpi,
    )
    plt.close(fig)

    stability = tables["q1_rank_stability"].merge(
        ranking[["feature", "feature_label", "final_rank"]], on="feature", how="left"
    )
    stability = stability.sort_values("final_rank")
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(stability))
    ax.errorbar(
        stability["rank_median"],
        y,
        xerr=[
            stability["rank_median"] - stability["rank_ci_low"],
            stability["rank_ci_high"] - stability["rank_median"],
        ],
        fmt="o",
        capsize=3,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(stability["feature_label"])
    ax.invert_yaxis()
    ax.set_xlabel("Bootstrap rank interval")
    ax.set_title("Rank stability")
    fig.tight_layout()
    outputs["q1_rank_stability"] = save_figure_bundle(
        fig=fig,
        data=stability,
        stem="q1_rank_stability",
        question_dir=question_dir,
        title="Bootstrap rank stability",
        source_script="questions/q1/scripts/visualize.py",
        notes="Intervals use marginal Pearson/Spearman bootstrap ranking.",
        dpi=dpi,
    )
    plt.close(fig)
    return outputs


def run_analysis(
    *,
    root: Path,
    config_path: str | Path = "configs/default.yaml",
    bootstrap_iterations: int = 500,
    cv_splits: int = 5,
    cv_repeats: int = 5,
    permutation_repeats: int = 5,
    create_figures: bool = True,
) -> dict[str, Any]:
    config = load_config(root, config_path)
    seed = random_seed(config)
    question_dir = root / "questions" / "q1"
    raw = load_raw_golf_data(root)
    clean = clean_golf_data(raw)
    save_processed_data(clean, root)
    views = build_sample_views(clean)
    correlations = compute_correlations(clean, INPUT_FEATURES, OUTPUT_COLUMNS)
    model_summary, cv_scores = model_importance_tables(
        views,
        seed=seed,
        cv_splits=cv_splits,
        cv_repeats=cv_repeats,
        permutation_repeats=permutation_repeats,
    )
    method_table = method_importance_table(correlations, model_summary)
    correlation_ci = bootstrap_correlation_intervals(clean, seed=seed, iterations=bootstrap_iterations)
    rank_stability = bootstrap_rank_stability(clean, seed=seed, iterations=bootstrap_iterations)
    feature_ranking = aggregate_rankings(method_table, rank_stability)
    sensitivity = sensitivity_comparison(clean, feature_ranking)
    group_table = group_importance(clean, seed=seed)
    outliers = outlier_flags(clean)

    tables = {
        "q1_data_audit": data_audit_table(clean),
        "q1_missing_audit": missing_audit_table(clean),
        "q1_outlier_flags": outliers,
        "q1_pearson_correlation": correlations["pearson"],
        "q1_spearman_correlation": correlations["spearman"],
        "q1_kendall_correlation": correlations["kendall"],
        "q1_correlation_matrix": pd.concat(
            [correlations["pearson"].assign(method="pearson"), correlations["spearman"].assign(method="spearman")],
            ignore_index=True,
        ),
        "q1_correlation_confidence_intervals": correlation_ci,
        "q1_model_cv_scores": cv_scores,
        "q1_method_importance": method_table,
        "q1_feature_ranking": feature_ranking,
        "q1_feature_importance": feature_ranking,
        "q1_group_importance": group_table,
        "q1_sensitivity_comparison": sensitivity,
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
        "top_features": feature_ranking.head(5)["feature"].tolist(),
        "tables": {key: str(path.relative_to(root)) for key, path in table_outputs.items()},
        "figures": {
            key: {subkey: str(path.relative_to(root)) for subkey, path in paths.items()}
            for key, paths in figure_outputs.items()
        },
    }
    summary_path = question_dir / "artifacts" / "tables" / "q1_run_summary.json"
    summary_path.write_text(json.dumps(run_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"clean": clean, "tables": tables, "table_outputs": table_outputs, "figure_outputs": figure_outputs}


def validate_outputs(root: Path) -> pd.DataFrame:
    question_dir = root / "questions" / "q1"
    required_tables = [
        "q1_data_audit.csv",
        "q1_missing_audit.csv",
        "q1_outlier_flags.csv",
        "q1_pearson_correlation.csv",
        "q1_spearman_correlation.csv",
        "q1_correlation_confidence_intervals.csv",
        "q1_method_importance.csv",
        "q1_feature_ranking.csv",
        "q1_group_importance.csv",
        "q1_sensitivity_comparison.csv",
        "q1_rank_stability.csv",
    ]
    required_figures = [
        "q1_pearson_heatmap",
        "q1_spearman_heatmap",
        "q1_top_feature_relationships",
        "q1_importance_comparison",
        "q1_rank_stability",
    ]
    rows = []
    for filename in required_tables:
        path = question_dir / "artifacts" / "tables" / filename
        rows.append(
            {
                "check": filename,
                "kind": "table",
                "path": str(path.relative_to(root)),
                "passed": path.exists() and path.stat().st_size > 0,
            }
        )
    for stem in required_figures:
        for suffix, kind in [(".png", "figure"), (".csv", "figure_data"), (".meta.json", "figure_metadata")]:
            base_dir = "figures" if suffix == ".png" else "figure_data"
            path = question_dir / "artifacts" / base_dir / f"{stem}{suffix}"
            rows.append(
                {
                    "check": f"{stem}{suffix}",
                    "kind": kind,
                    "path": str(path.relative_to(root)),
                    "passed": path.exists() and path.stat().st_size > 0,
                }
            )
    return pd.DataFrame(rows)
