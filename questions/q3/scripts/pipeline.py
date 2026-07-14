#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata as importlib_metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dependencies import LAUNCH_FEATURES, file_sha256, load_dependencies, values_sha256  # noqa: E402
from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402
from modeling_common.reproducibility import write_q2_q3_release_manifest  # noqa: E402
from objective import VARIABLES, candidate_frame, evaluate_candidates  # noqa: E402
from ode_verify import run_ode_crosscheck  # noqa: E402
from optimize import (  # noqa: E402
    best_observed_baseline,
    differential_evolution_runs,
    evaluate_designs,
    local_refinement,
    optimize_for_target,
    sampling_baseline,
    top_candidates,
)
from robustness import (  # noqa: E402
    all_scenario_robustness_summary,
    joint_model_parameter_robustness,
    model_crosscheck,
    near_optimal_parameter_ranges,
    near_optimal_candidates,
    optimal_parameter_rows,
    robust_candidate_pool,
    robustness_summary,
    simulate_parameter_robustness,
    support_comparison,
    target_distance_sensitivity,
)
from support import fit_full_input_support_model, fit_support_model, search_bounds  # noqa: E402
from surrogate import fit_lateral_model, fit_surrogate_ensembles  # noqa: E402
from validate import validate_outputs  # noqa: E402
from visualize import create_visualizations  # noqa: E402

IMPLEMENTED = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q3 robust inverse-design pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def current_git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return result.stdout.strip()


def package_versions() -> dict[str, str]:
    packages = ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "PyYAML"]
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib_metadata.version(package)
        except importlib_metadata.PackageNotFoundError:
            versions[package] = "not_installed"
    return versions


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def frame_sha256(frame: pd.DataFrame, columns: list[str]) -> str:
    payload = frame[columns].sort_values(columns).to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _evaluated_observed(
    observed: pd.DataFrame,
    *,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: Any,
    config: dict[str, Any],
) -> pd.DataFrame:
    row = observed.iloc[0]
    design = pd.DataFrame([{feature: row[feature] for feature in LAUNCH_FEATURES}])
    evaluated = evaluate_designs(
        design,
        carry_model=carry_model,
        lateral_model=lateral_model,
        apex_model=apex_model,
        support_model=support_model,
        config=config,
    )
    evaluated["candidate_id"] = row["candidate_id"]
    evaluated["candidate_type"] = "best_observed_baseline"
    evaluated["source"] = "q2 fixed train split actual record"
    return evaluated


def objective_slice_data(
    *,
    optimal: pd.DataFrame,
    train: pd.DataFrame,
    carry_model: Any,
    lateral_model: Any,
    apex_model: Any,
    support_model: Any,
    config: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    robust = optimal.set_index("candidate_type").loc["joint_robust_recommended_optimum"]
    nominal = optimal.set_index("candidate_type").loc["nominal_optimum"]
    outputs: dict[str, pd.DataFrame] = {}
    grid_n = int(config["plotting"].get("slice_grid_size", 50))

    speed_values = np.linspace(config["variables"]["ball_speed_mph"]["lower"], config["variables"]["ball_speed_mph"]["upper"], grid_n)
    angle_values = np.linspace(config["variables"]["launch_angle_deg"]["lower"], config["variables"]["launch_angle_deg"]["upper"], grid_n)
    rows = []
    for speed in speed_values:
        for angle in angle_values:
            rows.append(
                {
                    "ball_speed_mph": speed,
                    "launch_angle_deg": angle,
                    "launch_direction_deg": 0.0,
                    "spin_rate_rpm": float(robust["spin_rate_rpm"]),
                    "spin_axis_deg": float(robust["spin_axis_deg"]),
                    "row_type": "grid",
                }
            )
    speed_angle = evaluate_candidates(
        pd.DataFrame(rows)[LAUNCH_FEATURES],
        carry_model=carry_model,
        lateral_model=lateral_model,
        apex_model=apex_model,
        support_model=support_model,
        target_distance_yd=float(config["target"]["forward_distance_yd"]),
        target_lateral_yd=float(config["target"]["lateral_yd"]),
    )
    speed_angle["row_type"] = "grid"
    speed_angle = pd.concat(
        [
            speed_angle,
            train[[*LAUNCH_FEATURES]].assign(row_type="train", objective_yd=np.nan),
            pd.DataFrame([nominal]).assign(row_type="nominal_optimum"),
            pd.DataFrame([robust]).assign(row_type="joint_robust_recommended_optimum"),
        ],
        ignore_index=True,
        sort=False,
    )
    outputs["q3_objective_slice_speed_angle"] = speed_angle

    spin_values = np.linspace(config["variables"]["spin_rate_rpm"]["lower"], config["variables"]["spin_rate_rpm"]["upper"], grid_n)
    axis_values = np.linspace(config["variables"]["spin_axis_deg"]["lower"], config["variables"]["spin_axis_deg"]["upper"], grid_n)
    rows = []
    for spin_rate in spin_values:
        for spin_axis in axis_values:
            rows.append(
                {
                    "ball_speed_mph": float(robust["ball_speed_mph"]),
                    "launch_angle_deg": float(robust["launch_angle_deg"]),
                    "launch_direction_deg": 0.0,
                    "spin_rate_rpm": spin_rate,
                    "spin_axis_deg": spin_axis,
                    "row_type": "grid",
                }
            )
    spin = evaluate_candidates(
        pd.DataFrame(rows)[LAUNCH_FEATURES],
        carry_model=carry_model,
        lateral_model=lateral_model,
        apex_model=apex_model,
        support_model=support_model,
        target_distance_yd=float(config["target"]["forward_distance_yd"]),
        target_lateral_yd=float(config["target"]["lateral_yd"]),
    )
    spin["row_type"] = "grid"
    spin = pd.concat(
        [
            spin,
            train[[*LAUNCH_FEATURES]].assign(row_type="train", objective_yd=np.nan),
            pd.DataFrame([nominal]).assign(row_type="nominal_optimum"),
            pd.DataFrame([robust]).assign(row_type="joint_robust_recommended_optimum"),
        ],
        ignore_index=True,
        sort=False,
    )
    outputs["q3_objective_slice_spin"] = spin
    return outputs


def run_pipeline(*, root: Path, config_path: str) -> dict[str, object]:
    question_dir = root / "questions" / "q3"
    tables: dict[str, Path] = {}

    deps = load_dependencies(root, config_path)
    config = deps.config
    if not deps.audit["passed"].astype(bool).all():
        failed = deps.audit[~deps.audit["passed"].astype(bool)]
        raise RuntimeError(f"q3 dependency audit failed: {failed['check'].tolist()}")
    tables["q3_dependency_audit"] = save_table(deps.audit, stem="q3_dependency_audit", question_dir=question_dir)["csv"]

    support_model, support_threshold, training_support = fit_support_model(deps.train, config)
    full_support_model, full_support_threshold, full_training_support = fit_full_input_support_model(deps.train, config)
    tables["q3_search_bounds"] = save_table(search_bounds(deps.train, config), stem="q3_search_bounds", question_dir=question_dir)["csv"]
    tables["q3_support_threshold"] = save_table(
        support_threshold, stem="q3_support_threshold", question_dir=question_dir
    )["csv"]
    tables["q3_training_support"] = save_table(
        training_support, stem="q3_training_support", question_dir=question_dir
    )["csv"]
    tables["q3_full_input_support_threshold"] = save_table(
        full_support_threshold, stem="q3_full_input_support_threshold", question_dir=question_dir
    )["csv"]
    tables["q3_full_input_training_support"] = save_table(
        full_training_support, stem="q3_full_input_training_support", question_dir=question_dir
    )["csv"]

    git_commit = current_git_commit(root)
    lateral_model, lateral_metrics, lateral_predictions = fit_lateral_model(
        deps.train,
        deps.test,
        config,
        model_dir=question_dir / "artifacts" / "models",
        git_commit=git_commit,
        train_data_sha256=values_sha256(deps.train["record_id"]),
    )
    tables["q3_lateral_model_metrics"] = save_table(
        lateral_metrics, stem="q3_lateral_model_metrics", question_dir=question_dir
    )["csv"]
    tables["q3_lateral_predictions"] = save_table(
        lateral_predictions, stem="q3_lateral_predictions", question_dir=question_dir
    )["csv"]

    carry_ensemble, lateral_ensemble, ensemble_metrics = fit_surrogate_ensembles(deps.train, deps.test, config)
    tables["q3_surrogate_ensemble_metrics"] = save_table(
        ensemble_metrics, stem="q3_surrogate_ensemble_metrics", question_dir=question_dir
    )["csv"]

    observed = best_observed_baseline(deps.train, config)
    tables["q3_best_observed_baseline"] = save_table(
        observed, stem="q3_best_observed_baseline", question_dir=question_dir
    )["csv"]
    observed_evaluated = _evaluated_observed(
        observed,
        carry_model=deps.carry_model,
        lateral_model=lateral_model,
        apex_model=deps.apex_model,
        support_model=support_model,
        config=config,
    )

    sampling_top, sampling_all = sampling_baseline(
        carry_model=deps.carry_model,
        lateral_model=lateral_model,
        apex_model=deps.apex_model,
        support_model=support_model,
        config=config,
    )
    tables["q3_sampling_baseline"] = save_table(
        sampling_top, stem="q3_sampling_baseline", question_dir=question_dir
    )["csv"]

    de_runs, de_candidates = differential_evolution_runs(
        carry_model=deps.carry_model,
        lateral_model=lateral_model,
        apex_model=deps.apex_model,
        support_model=support_model,
        config=config,
    )
    local_candidates = local_refinement(
        de_runs,
        carry_model=deps.carry_model,
        lateral_model=lateral_model,
        apex_model=deps.apex_model,
        support_model=support_model,
        config=config,
    )
    all_top = top_candidates(sampling_top, de_candidates, local_candidates, observed_evaluated, limit=int(config["top_candidate_count"]))
    for seed, subset in local_candidates.groupby("seed"):
        best = subset.sort_values(["objective_yd", "support_knn_distance"]).iloc[0]
        de_runs.loc[de_runs["seed"] == int(seed), "best_refined_objective_yd"] = float(best["objective_yd"])
        de_runs.loc[de_runs["seed"] == int(seed), "best_refined_candidate_id"] = best["candidate_id"]
    tables["q3_optimization_runs"] = save_table(
        de_runs, stem="q3_optimization_runs", question_dir=question_dir
    )["csv"]
    tables["q3_top_candidates"] = save_table(
        all_top, stem="q3_top_candidates", question_dir=question_dir
    )["csv"]

    candidate_pool = robust_candidate_pool(all_top, config)
    pool_columns = [
        "candidate_id",
        "nominal_rank",
        "objective_yd",
        "support_category",
        "selection_method",
        "cluster_id",
        "selected_for_robustness",
        *VARIABLES,
        "launch_direction_deg",
        "predicted_carry_yd",
        "predicted_lateral_yd",
        "predicted_apex_yd",
        "support_knn_distance",
        "support_threshold",
        "source",
        "rank",
        "seed",
    ]
    tables["q3_robust_candidate_pool"] = save_table(
        candidate_pool[[column for column in pool_columns if column in candidate_pool.columns]],
        stem="q3_robust_candidate_pool",
        question_dir=question_dir,
    )["csv"]
    robust_candidates = near_optimal_candidates(all_top, config)
    robustness_detail = simulate_parameter_robustness(
        robust_candidates,
        carry_model=deps.carry_model,
        lateral_model=lateral_model,
        apex_model=deps.apex_model,
        support_model=support_model,
        full_support_model=full_support_model,
        config=config,
    )
    robustness_metrics = robustness_summary(robustness_detail, config=config)
    tables["q3_single_surrogate_parameter_robustness"] = save_table(
        robustness_metrics, stem="q3_single_surrogate_parameter_robustness", question_dir=question_dir
    )["csv"]
    all_robustness_metrics = all_scenario_robustness_summary(robustness_detail)
    support_compare = support_comparison(
        robust_candidates,
        robustness_detail,
        full_support_model=full_support_model,
    )
    tables["q3_support_comparison"] = save_table(
        support_compare, stem="q3_support_comparison", question_dir=question_dir
    )["csv"]
    joint_detail, joint_summary = joint_model_parameter_robustness(
        robust_candidates,
        carry_models=carry_ensemble,
        lateral_models=lateral_ensemble,
        apex_model=deps.apex_model,
        support_comparison_table=support_compare,
        config=config,
    )
    tables["q3_joint_robustness_detail"] = save_table(
        joint_detail, stem="q3_joint_robustness_detail", question_dir=question_dir
    )["csv"]
    tables["q3_joint_robustness_summary"] = save_table(
        joint_summary, stem="q3_joint_robustness_summary", question_dir=question_dir
    )["csv"]
    optimal = optimal_parameter_rows(all_top, robustness_metrics, all_robustness_metrics, joint_summary, config)
    tables["q3_optimal_parameters"] = save_table(
        optimal, stem="q3_optimal_parameters", question_dir=question_dir
    )["csv"]
    robustness_export_ids = set(optimal["candidate_id"].astype(str))
    robustness_detail_export = robustness_detail[
        robustness_detail["candidate_id"].astype(str).isin(robustness_export_ids)
    ].copy()
    tables["q3_parameter_robustness"] = save_table(
        robustness_detail_export, stem="q3_parameter_robustness", question_dir=question_dir
    )["csv"]
    near_ranges = near_optimal_parameter_ranges(robust_candidates, joint_summary, config)
    tables["q3_near_optimal_parameter_ranges"] = save_table(
        near_ranges, stem="q3_near_optimal_parameter_ranges", question_dir=question_dir
    )["csv"]

    crosscheck = model_crosscheck(
        optimal,
        carry_models=carry_ensemble,
        lateral_models=lateral_ensemble,
        apex_model=deps.apex_model,
        config=config,
    )
    tables["q3_model_crosscheck"] = save_table(
        crosscheck, stem="q3_model_crosscheck", question_dir=question_dir
    )["csv"]
    target_run_frames: list[pd.DataFrame] = []
    target_optimal_frames: list[pd.DataFrame] = []
    for target_distance in config["target_distance_sensitivity_yd"]:
        target_runs, target_optimal = optimize_for_target(
            float(target_distance),
            carry_model=deps.carry_model,
            lateral_model=lateral_model,
            apex_model=deps.apex_model,
            support_model=support_model,
            config=config,
        )
        target_run_frames.append(target_runs)
        target_optimal_frames.append(target_optimal)
    target_runs_all = pd.concat(target_run_frames, ignore_index=True, sort=False)
    target_optimal_all = pd.concat(target_optimal_frames, ignore_index=True, sort=False)
    tables["q3_target_optimization_runs"] = save_table(
        target_runs_all, stem="q3_target_optimization_runs", question_dir=question_dir
    )["csv"]
    tables["q3_target_optimal_parameters"] = save_table(
        target_optimal_all, stem="q3_target_optimal_parameters", question_dir=question_dir
    )["csv"]
    target_sensitivity = target_distance_sensitivity(target_optimal_all)
    tables["q3_target_distance_sensitivity"] = save_table(
        target_sensitivity, stem="q3_target_distance_sensitivity", question_dir=question_dir
    )["csv"]

    ode_candidates = pd.concat([observed_evaluated, optimal], ignore_index=True, sort=False)
    ode_crosscheck, trajectory = run_ode_crosscheck(
        ode_candidates,
        full_config=deps.full_config,
        q2_parameters=deps.q2_ode_parameters,
        q2_metadata=deps.q2_metadata,
    )
    tables["q3_ode_crosscheck"] = save_table(
        ode_crosscheck, stem="q3_ode_crosscheck", question_dir=question_dir
    )["csv"]
    tables["q3_optimal_trajectory"] = save_table(
        trajectory, stem="q3_optimal_trajectory", question_dir=question_dir
    )["csv"]

    for stem, frame in objective_slice_data(
        optimal=optimal,
        train=deps.train,
        carry_model=deps.carry_model,
        lateral_model=lateral_model,
        apex_model=deps.apex_model,
        support_model=support_model,
        config=config,
    ).items():
        tables[stem] = save_table(frame, stem=stem, question_dir=question_dir)["csv"]

    figure_outputs = create_visualizations(root=root, dpi=int(config["plotting"]["dpi"]))

    metadata = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": git_commit,
        "python_version": platform.python_version(),
        "package_versions": package_versions(),
        "config_path": rel_posix(root / config_path, root),
        "config_sha256": file_sha256(root / config_path),
        "data_path": rel_posix(root / config["input_path"], root),
        "data_sha256": file_sha256(root / config["input_path"]),
        "train_ids_sha256": values_sha256(deps.train["record_id"]),
        "test_ids_sha256": values_sha256(deps.test["record_id"]),
        "train_design_sha256": frame_sha256(deps.train, ["record_id", *LAUNCH_FEATURES]),
        "q3_status": "done",
        "q2_dependency_audit_passed": bool(deps.audit["passed"].astype(bool).all()),
        "q3_ode_verified": bool(deps.audit.loc[deps.audit["check"] == "q3_ode_verified", "passed"].iloc[0]),
        "target": config["target"],
        "fixed_inputs": config["fixed_inputs"],
        "nominal_candidate_id": str(optimal.set_index("candidate_type").loc["nominal_optimum", "candidate_id"]),
        "robust_candidate_id": str(
            optimal.set_index("candidate_type").loc["joint_robust_recommended_optimum", "candidate_id"]
        ),
        "lateral_model": {
            "path": "questions/q3/artifacts/models/q3_lateral_model.joblib",
            "selected_model": str(lateral_metrics[lateral_metrics["selected"].astype(bool)]["model"].iloc[0]),
            "selection_metric": "cv_rmse",
        },
        "q2": {
            "git_commit": deps.q2_metadata.get("git_commit", "unknown"),
            "run_metadata_sha256": file_sha256(root / "questions/q2/artifacts/run_metadata.json"),
            "ode_parameters_sha256": file_sha256(root / "questions/q2/artifacts/models/q2_ode_parameters.json"),
            "config_sha256": deps.q2_metadata.get("config_sha256", "unknown"),
            "data_sha256": deps.q2_metadata.get("data_sha256", "unknown"),
            "carry_definition": deps.q2_metadata.get("carry_definition", "unknown"),
            "best_fit_ode_model": deps.q2_metadata.get("best_fit_ode_model", "unknown"),
            "q3_compatible_ode_model": deps.q2_metadata.get("q3_compatible_ode_model", "unknown"),
        },
        "tables": {name: rel_posix(path, root) for name, path in tables.items()},
        "figures": {
            name: {kind: rel_posix(path, root) for kind, path in paths.items()}
            for name, paths in figure_outputs.items()
        },
    }
    metadata_path = question_dir / "artifacts" / "run_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    checks = validate_outputs(root, config_path=config_path, require_status_docs=False)
    tables["q3_validation_checks"] = save_table(
        checks, stem="q3_validation_checks", question_dir=question_dir
    )["csv"]
    failed = checks[~checks["passed"].astype(bool)]
    if not failed.empty:
        raise RuntimeError(f"q3 validation failed after pipeline run: {failed['check'].tolist()}")
    release_manifest_path = write_q2_q3_release_manifest(root, config_path=config_path)

    summary = {
        "train_n": int(len(deps.train)),
        "test_n": int(len(deps.test)),
        "release_manifest": rel_posix(release_manifest_path, root),
        "nominal_objective_yd": float(optimal.set_index("candidate_type").loc["nominal_optimum", "objective_yd"]),
        "robust_objective_yd": float(
            optimal.set_index("candidate_type").loc["joint_robust_recommended_optimum", "objective_yd"]
        ),
        "robust_p90_miss_yd": float(
            optimal.set_index("candidate_type").loc["joint_robust_recommended_optimum", "joint_p90_miss_distance_yd"]
        ),
        "selected_lateral_model": str(lateral_metrics[lateral_metrics["selected"].astype(bool)]["model"].iloc[0]),
    }
    return summary


def main() -> int:
    args = parse_args()
    root = project_root()
    steps = [
        "audit q2 dependencies",
        "train lateral surrogate",
        "fit train-only support diagnostics",
        "run observed and sampling baselines",
        "run five-seed differential evolution and local refinement",
        "select nominal and robust optima",
        "run robustness, model crosscheck, target sensitivity, and ODE crosscheck",
        "save q3 tables, figures, metadata, and validation checks",
    ]
    if args.dry_run:
        print("q3 planned pipeline:")
        for index, step in enumerate(steps, start=1):
            print(f"  {index}. {step}")
        print(f"config={root / args.config}")
        return 0
    summary = run_pipeline(root=root, config_path=args.config)
    print("[ok] q3 pipeline completed")
    print(f"train_n={summary['train_n']}")
    print(f"test_n={summary['test_n']}")
    print(f"selected_lateral_model={summary['selected_lateral_model']}")
    print(f"nominal_objective_yd={summary['nominal_objective_yd']:.6f}")
    print(f"robust_objective_yd={summary['robust_objective_yd']:.6f}")
    print(f"robust_p90_miss_yd={summary['robust_p90_miss_yd']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
