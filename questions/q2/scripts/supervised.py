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
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(actual, predicted)))


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = np.abs(actual) > 1e-12
    return float(np.mean(np.abs((predicted[mask] - actual[mask]) / actual[mask])) * 100.0)


def _mdape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = np.abs(actual) > 1e-12
    return float(np.median(np.abs((predicted[mask] - actual[mask]) / actual[mask])) * 100.0)


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "rmse": _rmse(actual, predicted),
        "mape": _mape(actual, predicted),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
        "mdape": _mdape(actual, predicted),
    }


def make_model(name: str, *, seed: int):
    imputer = SimpleImputer(strategy="median", add_indicator=True)
    if name == "dummy":
        return make_pipeline(imputer, DummyRegressor(strategy="mean"))
    if name == "linear":
        return make_pipeline(imputer, StandardScaler(), LinearRegression())
    if name == "ridge":
        return make_pipeline(
            imputer,
            StandardScaler(),
            RidgeCV(alphas=np.logspace(-3, 3, 25)),
        )
    if name == "extra_trees":
        return make_pipeline(
            imputer,
            ExtraTreesRegressor(
                n_estimators=120,
                min_samples_leaf=3,
                random_state=seed,
                n_jobs=-1,
            ),
        )
    if name == "hist_gradient_boosting":
        return make_pipeline(
            imputer,
            HistGradientBoostingRegressor(
                max_iter=160,
                learning_rate=0.05,
                l2_regularization=0.05,
                random_state=seed,
            ),
        )
    raise ValueError(f"Unsupported q2 supervised model: {name}")


def _cross_validate_model(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    folds: int,
    seed: int,
) -> dict[str, float]:
    cv = KFold(n_splits=folds, shuffle=True, random_state=seed)
    rows = []
    for train_idx, valid_idx in cv.split(X):
        fold_model = clone(model)
        fold_model.fit(X.iloc[train_idx], y.iloc[train_idx])
        pred = fold_model.predict(X.iloc[valid_idx])
        metrics = regression_metrics(y.iloc[valid_idx].to_numpy(dtype=float), pred)
        rows.append(metrics)
    frame = pd.DataFrame(rows)
    return {
        "cv_rmse": float(frame["rmse"].mean()),
        "cv_rmse_std": float(frame["rmse"].std(ddof=1)),
        "cv_mae": float(frame["mae"].mean()),
        "cv_r2": float(frame["r2"].mean()),
    }


def bootstrap_metric_ci(
    actual: np.ndarray,
    predicted: np.ndarray,
    *,
    seed: int,
    iterations: int,
    confidence_level: float,
) -> list[dict[str, float | str]]:
    rng = np.random.default_rng(seed)
    n = len(actual)
    alpha = (1.0 - confidence_level) / 2.0
    values: dict[str, list[float]] = {"rmse": [], "mape": [], "mae": []}
    for _ in range(iterations):
        idx = rng.integers(0, n, n)
        metrics = regression_metrics(actual[idx], predicted[idx])
        for metric in values:
            values[metric].append(metrics[metric])
    rows = []
    for metric, samples in values.items():
        arr = np.asarray(samples, dtype=float)
        rows.append(
            {
                "metric": metric,
                "ci_low": float(np.quantile(arr, alpha)),
                "ci_high": float(np.quantile(arr, 1.0 - alpha)),
                "iterations": int(iterations),
                "confidence_level": float(confidence_level),
            }
        )
    return rows


def run_supervised_models(
    train: pd.DataFrame,
    test: pd.DataFrame,
    config: dict[str, Any],
    *,
    model_dir: Path,
) -> dict[str, pd.DataFrame]:
    seed = int(config["random_seed"])
    folds = int(config["cross_validation"]["folds"])
    feature_sets = {
        "launch_state_model": list(config["features"]["launch_state"]),
        "full_shot_model": list(config["features"]["full_shot"]),
    }
    model_names = list(config["supervised"]["models"])
    targets = list(config["targets"])
    bootstrap_config = config["bootstrap"]
    model_dir.mkdir(parents=True, exist_ok=True)

    metric_rows = []
    prediction_rows = []
    ci_rows = []
    fitted_models: dict[tuple[str, str, str], Any] = {}

    for target in targets:
        for feature_set_name, features in feature_sets.items():
            X_train = train[features]
            y_train = train[target]
            X_test = test[features]
            y_test = test[target].to_numpy(dtype=float)
            for model_index, model_name in enumerate(model_names):
                model = make_model(model_name, seed=seed + model_index)
                cv_metrics = _cross_validate_model(model, X_train, y_train, folds=folds, seed=seed)
                model.fit(X_train, y_train)
                pred = model.predict(X_test)
                test_metrics = regression_metrics(y_test, pred)
                row = {
                    "target": target,
                    "feature_set": feature_set_name,
                    "features": ";".join(features),
                    "model": model_name,
                    **cv_metrics,
                    **test_metrics,
                    "selected": False,
                    "selection_rule": "lowest training CV RMSE within target",
                    "test_n": int(len(test)),
                }
                metric_rows.append(row)
                fitted_models[(target, feature_set_name, model_name)] = model

                for record_id, actual, predicted in zip(test["record_id"], y_test, pred, strict=True):
                    prediction_rows.append(
                        {
                            "record_id": int(record_id),
                            "target": target,
                            "feature_set": feature_set_name,
                            "model": model_name,
                            "actual": float(actual),
                            "predicted": float(predicted),
                            "residual": float(predicted - actual),
                            "absolute_error": float(abs(predicted - actual)),
                            "absolute_percentage_error": float(abs((predicted - actual) / actual) * 100.0)
                            if abs(actual) > 1e-12
                            else np.nan,
                        }
                    )
                for ci in bootstrap_metric_ci(
                    y_test,
                    pred,
                    seed=seed + model_index,
                    iterations=int(bootstrap_config["iterations"]),
                    confidence_level=float(bootstrap_config["confidence_level"]),
                ):
                    ci_rows.append(
                        {
                            "target": target,
                            "feature_set": feature_set_name,
                            "model": model_name,
                            **ci,
                        }
                    )

    metrics = pd.DataFrame(metric_rows)
    selected_index = metrics.groupby("target")["cv_rmse"].idxmin()
    metrics.loc[selected_index, "selected"] = True
    predictions = pd.DataFrame(prediction_rows)
    ci_frame = pd.DataFrame(ci_rows)

    selected_rows = metrics.loc[selected_index]
    for _, row in selected_rows.iterrows():
        key = (row["target"], row["feature_set"], row["model"])
        filename = "q2_carry_model.joblib" if row["target"] == "carry_distance_yd" else "q2_apex_model.joblib"
        joblib.dump(fitted_models[key], model_dir / filename)

    return {
        "metrics": metrics.sort_values(["target", "feature_set", "cv_rmse"]).reset_index(drop=True),
        "predictions": predictions.sort_values(["target", "feature_set", "model", "record_id"]).reset_index(drop=True),
        "bootstrap_ci": ci_frame.sort_values(["target", "feature_set", "model", "metric"]).reset_index(drop=True),
        "error_groups": supervised_error_groups(test, predictions, metrics),
    }


def supervised_error_groups(test: pd.DataFrame, predictions: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    selected = metrics[metrics["selected"].astype(bool)][["target", "feature_set", "model"]]
    rows = []
    group_features = ["ball_speed_mph", "launch_angle_deg", "spin_rate_rpm"]
    merged_base = test[["record_id", *group_features]].copy()
    selected_predictions = predictions.merge(selected, on=["target", "feature_set", "model"], how="inner")
    selected_predictions = selected_predictions.merge(merged_base, on="record_id", how="left")
    for target, target_frame in selected_predictions.groupby("target"):
        for group_feature in group_features:
            bins = pd.qcut(target_frame[group_feature], q=4, duplicates="drop")
            for bin_label, subset in target_frame.groupby(bins, observed=True):
                actual = subset["actual"].to_numpy(dtype=float)
                predicted = subset["predicted"].to_numpy(dtype=float)
                metrics_row = regression_metrics(actual, predicted)
                rows.append(
                    {
                        "target": target,
                        "group_feature": group_feature,
                        "bin": str(bin_label),
                        "count": int(len(subset)),
                        "rmse": metrics_row["rmse"],
                        "mae": metrics_row["mae"],
                        "mape": metrics_row["mape"],
                    }
                )
    return pd.DataFrame(rows)


def run_repeated_split_stability(clean: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Run repeated 70/30 splits for stability diagnostics only."""
    seed = int(config["random_seed"])
    runs = int(config["repeated_split"]["runs"])
    test_size = float(config["split"]["test_size"])
    features = list(config["features"]["launch_state"])
    targets = list(config["targets"])
    model_names = list(config["supervised"]["models"])
    records = []

    for run_index in range(runs):
        run_seed = seed + run_index + 1
        train_idx, test_idx = train_test_split(
            clean.index.to_numpy(),
            test_size=test_size,
            random_state=run_seed,
            shuffle=True,
        )
        train = clean.iloc[train_idx].reset_index(drop=True)
        test = clean.iloc[test_idx].reset_index(drop=True)
        for target in targets:
            y_test = test[target].to_numpy(dtype=float)
            run_rows = []
            for model_index, model_name in enumerate(model_names):
                model = make_model(model_name, seed=run_seed + model_index)
                model.fit(train[features], train[target])
                pred = model.predict(test[features])
                metrics = regression_metrics(y_test, pred)
                run_rows.append({"model": model_name, **metrics})
            best_model = min(run_rows, key=lambda row: row["rmse"])["model"]
            for row in run_rows:
                records.append(
                    {
                        "run": run_index + 1,
                        "random_seed": run_seed,
                        "target": target,
                        "model": row["model"],
                        "rmse": row["rmse"],
                        "mape": row["mape"],
                        "is_winner": row["model"] == best_model,
                    }
                )

    details = pd.DataFrame(records)
    summary_rows = []
    for (target, model), subset in details.groupby(["target", "model"]):
        for metric in ["rmse", "mape"]:
            summary_rows.append(
                {
                    "target": target,
                    "model": model,
                    "metric": metric,
                    "mean": float(subset[metric].mean()),
                    "std": float(subset[metric].std(ddof=1)),
                    "runs": int(runs),
                    "model_win_frequency": float(subset["is_winner"].mean()),
                    "split_comparison_win_frequency": float(subset["is_winner"].mean()),
                }
            )
    return pd.DataFrame(summary_rows).sort_values(["target", "metric", "mean"]).reset_index(drop=True)
