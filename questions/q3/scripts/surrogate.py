from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from dependencies import LAUNCH_FEATURES


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(actual, predicted)))


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "rmse": rmse(actual, predicted),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
        "bias": float(np.mean(predicted - actual)),
    }


def make_model(name: str, *, seed: int):
    imputer = SimpleImputer(strategy="median", add_indicator=True)
    if name == "dummy":
        return make_pipeline(imputer, DummyRegressor(strategy="mean"))
    if name == "linear":
        return make_pipeline(imputer, StandardScaler(), LinearRegression())
    if name == "ridge":
        return make_pipeline(imputer, StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 25)))
    if name == "extra_trees":
        return make_pipeline(
            imputer,
            ExtraTreesRegressor(
                n_estimators=140,
                min_samples_leaf=3,
                random_state=int(seed),
                n_jobs=1,
            ),
        )
    if name == "hist_gradient_boosting":
        return make_pipeline(
            imputer,
            HistGradientBoostingRegressor(
                max_iter=180,
                learning_rate=0.05,
                l2_regularization=0.05,
                random_state=int(seed),
            ),
        )
    raise ValueError(f"Unsupported q3 surrogate model: {name}")


def cross_validate_model(model: Any, X: pd.DataFrame, y: pd.Series, *, folds: int, seed: int) -> dict[str, float]:
    cv = KFold(n_splits=int(folds), shuffle=True, random_state=int(seed))
    rows = []
    for train_idx, valid_idx in cv.split(X):
        fold_model = clone(model)
        fold_model.fit(X.iloc[train_idx], y.iloc[train_idx])
        pred = fold_model.predict(X.iloc[valid_idx])
        rows.append(regression_metrics(y.iloc[valid_idx].to_numpy(dtype=float), pred))
    frame = pd.DataFrame(rows)
    return {
        "cv_rmse": float(frame["rmse"].mean()),
        "cv_rmse_std": float(frame["rmse"].std(ddof=1)),
        "cv_mae": float(frame["mae"].mean()),
        "cv_r2": float(frame["r2"].mean()),
    }


def fit_lateral_model(
    train: pd.DataFrame,
    test: pd.DataFrame,
    config: dict[str, Any],
    *,
    model_dir: Path,
    git_commit: str,
    train_data_sha256: str,
) -> tuple[Any, pd.DataFrame, pd.DataFrame]:
    seed = int(config["random_seed"])
    folds = int(config["cross_validation"]["folds"])
    model_names = list(config["lateral"]["models"])
    X_train = train[LAUNCH_FEATURES]
    y_train = train["lateral_offset_yd"]
    X_test = test[LAUNCH_FEATURES]
    y_test = test["lateral_offset_yd"].to_numpy(dtype=float)

    metric_rows = []
    fitted: dict[str, Any] = {}
    for index, model_name in enumerate(model_names):
        model = make_model(model_name, seed=seed + index)
        cv_metrics = cross_validate_model(model, X_train, y_train, folds=folds, seed=seed)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        test_metrics = regression_metrics(y_test, pred)
        metric_rows.append(
            {
                "target": "lateral_offset_yd",
                "features": ";".join(LAUNCH_FEATURES),
                "model": model_name,
                **cv_metrics,
                "test_rmse": test_metrics["rmse"],
                "test_mae": test_metrics["mae"],
                "test_r2": test_metrics["r2"],
                "test_bias": test_metrics["bias"],
                "selected": False,
                "selection_metric": "cv_rmse",
                "test_n": int(len(test)),
            }
        )
        fitted[model_name] = model

    metrics = pd.DataFrame(metric_rows).sort_values(["cv_rmse", "model"]).reset_index(drop=True)
    metrics.loc[0, "selected"] = True
    selected_name = str(metrics.loc[0, "model"])
    selected_model = fitted[selected_name]
    selected_pred = selected_model.predict(X_test)
    predictions = pd.DataFrame(
        {
            "record_id": test["record_id"].astype(int).to_numpy(),
            "actual_lateral_yd": y_test,
            "predicted_lateral_yd": selected_pred,
            "residual_yd": selected_pred - y_test,
            "absolute_error_yd": np.abs(selected_pred - y_test),
            "model": selected_name,
        }
    ).sort_values("record_id")

    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": selected_model,
            "features": LAUNCH_FEATURES,
            "target": "lateral_offset_yd",
            "model_name": selected_name,
            "train_record_ids": train["record_id"].astype(int).tolist(),
            "train_data_sha256": train_data_sha256,
            "git_commit": git_commit,
            "random_seed": seed,
            "selection_metric": "cv_rmse",
        },
        model_dir / "q3_lateral_model.joblib",
    )
    return selected_model, metrics, predictions.reset_index(drop=True)


def fit_surrogate_ensembles(
    train: pd.DataFrame,
    test: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[list[Any], list[Any], pd.DataFrame]:
    seed = int(config["random_seed"])
    members = int(config["uncertainty"]["ensemble_members"])
    X_train = train[LAUNCH_FEATURES]
    X_test = test[LAUNCH_FEATURES]
    rows = []
    carry_models: list[Any] = []
    lateral_models: list[Any] = []
    model_cycle = ["hist_gradient_boosting", "extra_trees"]

    for member in range(members):
        rng = np.random.default_rng(seed + 100 + member)
        sample_idx = rng.integers(0, len(train), len(train))
        member_train = train.iloc[sample_idx].reset_index(drop=True)
        for target, container in [("carry_distance_yd", carry_models), ("lateral_offset_yd", lateral_models)]:
            model_name = model_cycle[member % len(model_cycle)]
            model = make_model(model_name, seed=seed + 200 + member)
            model.fit(member_train[LAUNCH_FEATURES], member_train[target])
            pred = model.predict(X_test)
            actual = test[target].to_numpy(dtype=float)
            metrics = regression_metrics(actual, pred)
            rows.append(
                {
                    "target": target,
                    "ensemble_member": member + 1,
                    "model": model_name,
                    "bootstrap_seed": seed + 100 + member,
                    "test_rmse": metrics["rmse"],
                    "test_mae": metrics["mae"],
                    "test_r2": metrics["r2"],
                    "test_bias": metrics["bias"],
                    "features": ";".join(LAUNCH_FEATURES),
                }
            )
            container.append(model)
    return carry_models, lateral_models, pd.DataFrame(rows).sort_values(["target", "ensemble_member"])
