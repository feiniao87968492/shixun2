from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from dependencies import SUPPORT_FEATURES


@dataclass
class SupportModel:
    scaler: StandardScaler
    neighbors: NearestNeighbors
    threshold: float
    borderline_threshold: float
    k: int


def fit_support_model(train: pd.DataFrame, config: dict[str, Any]) -> tuple[SupportModel, pd.DataFrame, pd.DataFrame]:
    k = int(config["support"]["neighbors"])
    quantile = float(config["support"]["threshold_quantile"])
    matrix = train[SUPPORT_FEATURES].to_numpy(dtype=float)
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
    )
    training_support = train[["record_id", *SUPPORT_FEATURES]].copy()
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
                "source": "q2 fixed train split leave-one-out kNN distance",
            }
        ]
    )
    return model, threshold_table, training_support


def evaluate_support(model: SupportModel, candidates: pd.DataFrame) -> pd.DataFrame:
    matrix = candidates[SUPPORT_FEATURES].to_numpy(dtype=float)
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
