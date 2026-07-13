from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from dependencies import LAUNCH_FEATURES, SUPPORT_FEATURES


@dataclass
class SupportModel:
    scaler: StandardScaler
    neighbors: NearestNeighbors
    threshold: float
    borderline_threshold: float
    k: int
    features: list[str]


def _fit_support_model_for_features(
    train: pd.DataFrame,
    config: dict[str, Any],
    *,
    features: list[str],
    source_label: str,
) -> tuple[SupportModel, pd.DataFrame, pd.DataFrame]:
    k = int(config["support"]["neighbors"])
    quantile = float(config["support"]["threshold_quantile"])
    matrix = train[features].to_numpy(dtype=float)
    scaler = StandardScaler().fit(matrix)
    scaled = scaler.transform(matrix)
    loo_neighbors = NearestNeighbors(n_neighbors=k + 1)
    loo_neighbors.fit(scaled)
    distances, _indices = loo_neighbors.kneighbors(scaled)
    loo_distance = distances[:, 1 : k + 1].mean(axis=1)
    threshold = float(np.quantile(loo_distance, quantile))
    borderline_threshold = float(threshold * 1.25)

    all_neighbors = NearestNeighbors(n_neighbors=k)
    all_neighbors.fit(scaled)
    model = SupportModel(
        scaler=scaler,
        neighbors=all_neighbors,
        threshold=threshold,
        borderline_threshold=borderline_threshold,
        k=k,
        features=list(features),
    )
    training_support = train[["record_id", *features]].copy()
    training_support["loo_knn_distance"] = loo_distance
    training_support["support_threshold"] = threshold
    training_support["support_category"] = np.where(
        training_support["loo_knn_distance"] <= threshold,
        "supported",
        "borderline",
    )
    threshold_table = pd.DataFrame(
        [
            {
                "neighbors": k,
                "threshold_quantile": quantile,
                "support_threshold": threshold,
                "borderline_threshold": borderline_threshold,
                "training_n": int(len(train)),
                "features": ";".join(features),
                "source": source_label,
            }
        ]
    )
    return model, threshold_table, training_support


def fit_support_model(train: pd.DataFrame, config: dict[str, Any]) -> tuple[SupportModel, pd.DataFrame, pd.DataFrame]:
    return _fit_support_model_for_features(
        train,
        config,
        features=SUPPORT_FEATURES,
        source_label="q2 fixed train split leave-one-out kNN distance in decision space",
    )


def fit_full_input_support_model(
    train: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[SupportModel, pd.DataFrame, pd.DataFrame]:
    return _fit_support_model_for_features(
        train,
        config,
        features=LAUNCH_FEATURES,
        source_label="q2 fixed train split leave-one-out kNN distance in full launch-feature space",
    )


def evaluate_support(model: SupportModel, candidates: pd.DataFrame) -> pd.DataFrame:
    features = getattr(model, "features", SUPPORT_FEATURES)
    matrix = candidates[features].to_numpy(dtype=float)
    scaled = model.scaler.transform(matrix)
    distances, _indices = model.neighbors.kneighbors(scaled)
    mean_distance = distances.mean(axis=1)
    categories = np.where(
        mean_distance <= model.threshold,
        "supported",
        np.where(mean_distance <= model.borderline_threshold, "borderline", "out_of_support"),
    )
    output = candidates.copy()
    output["support_knn_distance"] = mean_distance
    output["support_threshold"] = model.threshold
    output["support_category"] = categories
    return output


def support_columns(model: SupportModel, candidates: pd.DataFrame, *, prefix: str) -> pd.DataFrame:
    supported = evaluate_support(model, candidates)
    return pd.DataFrame(
        {
            f"{prefix}_knn_distance": supported["support_knn_distance"].to_numpy(dtype=float),
            f"{prefix}_support_threshold": supported["support_threshold"].to_numpy(dtype=float),
            f"{prefix}_support_category": supported["support_category"].astype(str).to_numpy(),
        }
    )


def search_bounds(train: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for variable, bounds in config["variables"].items():
        series = train[variable]
        rows.append(
            {
                "variable": variable,
                "hard_lower": float(bounds["lower"]),
                "hard_upper": float(bounds["upper"]),
                "train_min": float(series.min()),
                "train_q05": float(series.quantile(0.05)),
                "train_q50": float(series.quantile(0.50)),
                "train_q95": float(series.quantile(0.95)),
                "train_max": float(series.max()),
                "source": "hard bounds from task5/problem statement; support statistics from q2 train split",
            }
        )
    return pd.DataFrame(rows)
