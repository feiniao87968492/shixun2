#!/usr/bin/env python3
"""Validation and sensitivity checks for q3."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402


def _row(check: str, passed: bool, value: object, notes: str = "") -> dict[str, object]:
    return {"check": check, "passed": bool(passed), "value": value, "notes": notes}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _posix_paths(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_posix_paths(child) for child in value.values())
    if isinstance(value, list):
        return all(_posix_paths(child) for child in value)
    if isinstance(value, str) and (
        value.startswith("questions") or value.startswith("configs") or value.startswith("data")
    ):
        return "\\" not in value
    return True


def validate_outputs(
    root: Path,
    *,
    config_path: str = "configs/default.yaml",
    require_status_docs: bool = True,
) -> pd.DataFrame:
    config = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    q3_config = config["q3"]
    q3 = root / "questions" / "q3"
    tables = q3 / "artifacts" / "tables"
    figure_data = q3 / "artifacts" / "figure_data"
    figures = q3 / "artifacts" / "figures"
    rows: list[dict[str, object]] = []

    manifest = yaml.safe_load((q3 / "manifest.yaml").read_text(encoding="utf-8"))
    upstream = set(manifest["inputs"]["upstream_artifacts"])
    required_upstream = {
        "questions/q2/artifacts/models/q2_carry_model.joblib",
        "questions/q2/artifacts/models/q2_apex_model.joblib",
        "questions/q2/artifacts/models/q2_ode_parameters.json",
        "questions/q2/artifacts/run_metadata.json",
        "questions/q2/artifacts/tables/q2_data_split.csv",
        "questions/q2/artifacts/tables/q2_validation_checks.csv",
    }
    rows.append(
        _row(
            "task5_manifest_uses_final_q2_dependencies",
            required_upstream.issubset(upstream)
            and "questions/q2/artifacts/models/q2_prediction_model.joblib" not in upstream,
            len(upstream),
        )
    )

    audit = _read_csv(tables / "q3_dependency_audit.csv")
    rows.append(_row("task5_q2_dependencies_verified", not audit.empty and audit["passed"].astype(bool).all(), len(audit)))
    if not audit.empty:
        values = dict(zip(audit["check"], audit["value"], strict=False))
        rows.append(
            _row(
                "task5_fixed_split_reused",
                int(values.get("q2_train_count", -1)) == 514
                and int(values.get("q2_test_count", -1)) == 221
                and int(values.get("q2_split_overlap_count", -1)) == 0,
                f"{values.get('q2_train_count')}/{values.get('q2_test_count')}",
            )
        )

    lateral_metrics = _read_csv(tables / "q3_lateral_model_metrics.csv")
    rows.append(
        _row(
            "task5_lateral_model_selected_by_cv_rmse",
            not lateral_metrics.empty
            and lateral_metrics["selected"].astype(bool).sum() == 1
            and "mape" not in {column.lower() for column in lateral_metrics.columns},
            len(lateral_metrics),
        )
    )

    training_support = _read_csv(tables / "q3_training_support.csv")
    threshold = _read_csv(tables / "q3_support_threshold.csv")
    rows.append(
        _row(
            "task5_support_threshold_train_only",
            len(training_support) == 514 and not threshold.empty and int(threshold["training_n"].iloc[0]) == 514,
            len(training_support),
        )
    )

    sampling = _read_csv(tables / "q3_sampling_baseline.csv")
    rows.append(
        _row(
            "task5_sampling_baseline_size",
            not sampling.empty and int(sampling["sample_count"].iloc[0]) >= 20_000 and len(sampling) == 100,
            len(sampling),
        )
    )
    runs = _read_csv(tables / "q3_optimization_runs.csv")
    rows.append(
        _row(
            "task5_differential_evolution_five_seeds",
            set(runs.get("seed", pd.Series(dtype=int)).astype(int)) == {2026, 2027, 2028, 2029, 2030}
            and runs.get("success", pd.Series(dtype=bool)).astype(bool).all(),
            len(runs),
        )
    )

    optimal = _read_csv(tables / "q3_optimal_parameters.csv")
    required_optima = {"nominal_optimum", "robust_recommended_optimum"}
    rows.append(
        _row(
            "task5_nominal_and_robust_optima_reported",
            required_optima.issubset(set(optimal.get("candidate_type", pd.Series(dtype=str)))),
            len(optimal),
        )
    )
    objective_ok = False
    if not optimal.empty:
        target_distance = float(q3_config["target"]["forward_distance_yd"])
        target_lateral = float(q3_config["target"]["lateral_yd"])
        manual = ((optimal["predicted_carry_yd"] - target_distance) ** 2 + (optimal["predicted_lateral_yd"] - target_lateral) ** 2) ** 0.5
        objective_ok = bool((manual - optimal["objective_yd"]).abs().max() <= 1e-9)
    rows.append(_row("task5_objective_recomputes", objective_ok, "max_abs_error<=1e-9"))

    robustness = _read_csv(tables / "q3_parameter_robustness.csv")
    robust_ok = False
    if not optimal.empty and not robustness.empty:
        robust = optimal.set_index("candidate_type").loc["robust_recommended_optimum"]
        detail = robustness[robustness["candidate_id"] == robust["candidate_id"]]
        if not detail.empty:
            robust_ok = math.isclose(
                float(robust["p90_miss_distance_yd"]),
                float(detail["miss_distance_yd"].quantile(0.90)),
                abs_tol=1e-9,
            )
    rows.append(_row("task5_robust_metrics_recomputable", robust_ok, len(robustness)))

    crosscheck = _read_csv(tables / "q3_model_crosscheck.csv")
    rows.append(
        _row(
            "task5_model_crosscheck_complete",
            not crosscheck.empty
            and crosscheck["carry_model_member"].nunique() >= 5
            and crosscheck["lateral_model_member"].nunique() >= 5,
            len(crosscheck),
        )
    )
    sensitivity = _read_csv(tables / "q3_target_distance_sensitivity.csv")
    rows.append(
        _row(
            "task5_target_distance_sensitivity_complete",
            {195.0, 200.0, 205.0}.issubset(set(sensitivity.get("target_distance_yd", pd.Series(dtype=float)).astype(float))),
            len(sensitivity),
        )
    )
    ode = _read_csv(tables / "q3_ode_crosscheck.csv")
    rows.append(
        _row(
            "task5_ode_crosscheck_successful",
            not ode.empty
            and {"constant_lift", "spin_factor_lift"}.issubset(set(ode["model"]))
            and ode["integration_status"].eq("success").all(),
            len(ode),
        )
    )

    figure_stems = [
        "q3_optimal_trajectory_3d",
        "q3_optimal_trajectory_side",
        "q3_optimal_trajectory_top",
        "q3_objective_slice_speed_angle",
        "q3_objective_slice_spin",
    ]
    figure_ok = all(
        (figures / f"{stem}.png").exists()
        and (figure_data / f"{stem}.csv").exists()
        and (figure_data / f"{stem}.meta.json").exists()
        for stem in figure_stems
    )
    rows.append(_row("task5_figures_have_data_and_metadata", figure_ok, len(figure_stems)))

    metadata_path = q3 / "artifacts" / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    rows.append(_row("task5_metadata_paths_posix", bool(metadata) and _posix_paths(metadata), len(metadata)))

    status_ok = True
    if require_status_docs:
        root_readme = (root / "README.md").read_text(encoding="utf-8")
        q3_readme = (q3 / "README.md").read_text(encoding="utf-8")
        status_ok = (
            manifest.get("status") == "done"
            and ("| q3 | done |" in root_readme or "q3 | done" in root_readme)
            and "状态：`done`" in q3_readme
        )
    rows.append(_row("task5_status_files_synced", status_ok, str(status_ok).lower()))
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q3 validation")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--skip-status-docs", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    checks = validate_outputs(root, config_path=args.config, require_status_docs=not args.skip_status_docs)
    save_table(checks, stem="q3_validation_checks", question_dir=root / "questions" / "q3")
    failed = checks[~checks["passed"].astype(bool)]
    if not failed.empty:
        print(failed.to_string(index=False))
        return 1
    print(f"[ok] q3 validation passed {len(checks)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
