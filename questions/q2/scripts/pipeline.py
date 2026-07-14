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

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402
from ode_model import (  # noqa: E402
    PhysicalConstants,
    calibrate_drag_cd,
    calibrate_lift_parameters,
    calibration_failure_rows,
    carry_definition_comparison,
    evaluate_ode_models,
    ode_sensitivity,
    q3_boundary_stability_checks,
    typical_errors_and_trajectories,
    validation_checks as ode_validation_checks,
)
from preprocessing import (  # noqa: E402
    ODE_REQUIRED_FEATURES,
    fixed_train_test_split,
    load_clean_data,
    load_project_config,
    select_calibration_records,
    select_typical_records,
    spin_geometry_check,
    split_frames,
)
from supervised import run_repeated_split_stability, run_supervised_models  # noqa: E402
from validate import validate_outputs  # noqa: E402
from visualize import create_visualizations  # noqa: E402

IMPLEMENTED = True


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def values_sha256(values: pd.Series) -> str:
    payload = "\n".join(map(str, sorted(values.astype(int).tolist()))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def parameter_boundary_row(
    *,
    model: str,
    parameter: str,
    value: float,
    lower_bound: float | str,
    upper_bound: float | str,
    calibration_stage: str,
    source: str,
    full_train_objective: float | str = "",
    parameter_status: str = "ok",
) -> dict[str, object]:
    if isinstance(lower_bound, str) or isinstance(upper_bound, str):
        return {
            "model": model,
            "parameter": parameter,
            "value": value,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "calibration_stage": calibration_stage,
            "source": source,
            "at_lower_bound": False,
            "at_upper_bound": False,
            "distance_to_lower_bound": "",
            "distance_to_upper_bound": "",
            "boundary_warning": "",
            "parameter_status": parameter_status,
            "full_train_objective": full_train_objective,
        }

    span = float(upper_bound) - float(lower_bound)
    tolerance = max(span * 1e-8, 1e-12)
    lower_distance = float(value) - float(lower_bound)
    upper_distance = float(upper_bound) - float(value)
    at_lower = lower_distance <= tolerance
    at_upper = upper_distance <= tolerance
    near_boundary = min(lower_distance, upper_distance) <= span * 0.01
    warning = "within_1pct_of_bound" if near_boundary else ""
    return {
        "model": model,
        "parameter": parameter,
        "value": float(value),
        "lower_bound": float(lower_bound),
        "upper_bound": float(upper_bound),
        "calibration_stage": calibration_stage,
        "source": source,
        "at_lower_bound": bool(at_lower),
        "at_upper_bound": bool(at_upper),
        "distance_to_lower_bound": float(lower_distance),
        "distance_to_upper_bound": float(upper_distance),
        "boundary_warning": warning,
        "parameter_status": parameter_status,
        "full_train_objective": full_train_objective,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q2 modeling pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    question_dir = root / "questions" / "q2"

    steps = [
        "load and validate inputs",
        "preprocess data",
        "run baseline",
        "fit or solve main model",
        "validate and diagnose",
        "run sensitivity analysis",
        "save tables, figures, figure data, and metadata",
        "update evidence records",
    ]
    if args.dry_run:
        print("q2 planned pipeline:")
        for index, step in enumerate(steps, start=1):
            print(f"  {index}. {step}")
        print(f"question_dir={question_dir}")
        print(f"config={root / args.config}")
        return 0

    if not IMPLEMENTED:
        print(
            "q2 pipeline is a scaffold. Fill approach.md first, implement the pipeline, "
            "then set IMPLEMENTED = True."
        )
        return 2

    summary = run_pipeline(root=root, config_path=args.config)
    print("[ok] q2 pipeline completed")
    print(f"question_dir={question_dir}")
    print(f"train_n={summary['train_n']}")
    print(f"test_n={summary['test_n']}")
    print("selected_supervised_models=" + "; ".join(summary["selected_supervised_models"]))
    print(f"preliminary_drag_cd={summary['preliminary_drag_cd']:.6g}")
    return 0


def run_pipeline(*, root: Path, config_path: str) -> dict[str, object]:
    question_dir = root / "questions" / "q2"
    config = load_project_config(root, config_path)
    clean = load_clean_data(root, config)
    split = fixed_train_test_split(clean, config)
    train, test = split_frames(clean, split)
    tables: dict[str, Path] = {}

    tables["q2_data_split"] = save_table(split, stem="q2_data_split", question_dir=question_dir)["csv"]
    spin_geometry = spin_geometry_check(clean)
    tables["q2_spin_geometry_check"] = save_table(
        spin_geometry, stem="q2_spin_geometry_check", question_dir=question_dir
    )["csv"]
    selected_sign = int(
        spin_geometry.loc[spin_geometry["relationship"] == "selected_sidespin_sign", "selected_sign"].iloc[0]
    )

    supervised_outputs = run_supervised_models(
        train,
        test,
        config,
        model_dir=question_dir / "artifacts" / "models",
    )
    tables["q2_supervised_metrics"] = save_table(
        supervised_outputs["metrics"], stem="q2_supervised_metrics", question_dir=question_dir
    )["csv"]
    cv_columns = [
        "target",
        "feature_set",
        "features",
        "model",
        "cv_rmse",
        "cv_rmse_std",
        "cv_mae",
        "cv_r2",
        "selection_rule",
    ]
    tables["q2_supervised_cv_results"] = save_table(
        supervised_outputs["metrics"][cv_columns],
        stem="q2_supervised_cv_results",
        question_dir=question_dir,
    )["csv"]
    tables["q2_supervised_predictions"] = save_table(
        supervised_outputs["predictions"], stem="q2_supervised_predictions", question_dir=question_dir
    )["csv"]
    tables["q2_supervised_bootstrap_ci"] = save_table(
        supervised_outputs["bootstrap_ci"], stem="q2_supervised_bootstrap_ci", question_dir=question_dir
    )["csv"]
    tables["q2_supervised_error_groups"] = save_table(
        supervised_outputs["error_groups"], stem="q2_supervised_error_groups", question_dir=question_dir
    )["csv"]
    tables["q2_supervised_repeated_split"] = save_table(
        run_repeated_split_stability(clean, config),
        stem="q2_supervised_repeated_split",
        question_dir=question_dir,
    )["csv"]

    constants = PhysicalConstants.from_config(config["physics"])
    ode_required = [*ODE_REQUIRED_FEATURES, "carry_distance_yd", "apex_height_yd", "lateral_offset_yd"]
    ode_train = train.dropna(subset=ode_required).reset_index(drop=True)
    ode_test = test.dropna(subset=ode_required).reset_index(drop=True)
    drag_representative = select_calibration_records(
        ode_train,
        required_features=ODE_REQUIRED_FEATURES,
        representative_count=int(config["ode"]["drag_calibration"]["representative_count"]),
        calibration_type="drag",
        random_seed=int(config["random_seed"]),
    )
    lift_representative = select_calibration_records(
        ode_train,
        required_features=ODE_REQUIRED_FEATURES,
        representative_count=int(config["ode"]["lift_calibration"]["representative_count"]),
        calibration_type="lift",
        random_seed=int(config["random_seed"]) + 17,
    )
    representative = pd.concat([drag_representative, lift_representative], ignore_index=True)
    tables["q2_drag_calibration_records"] = save_table(
        drag_representative, stem="q2_drag_calibration_records", question_dir=question_dir
    )["csv"]
    tables["q2_lift_calibration_records"] = save_table(
        lift_representative, stem="q2_lift_calibration_records", question_dir=question_dir
    )["csv"]
    tables["q2_ode_representative_records"] = save_table(
        representative, stem="q2_ode_representative_records", question_dir=question_dir
    )["csv"]
    cd_bounds = tuple(float(value) for value in config["ode"]["parameter_bounds"]["cd"])
    cl_bounds = tuple(float(value) for value in config["ode"]["parameter_bounds"]["cl"])
    lift_scale_bounds = tuple(float(value) for value in config["ode"]["parameter_bounds"]["lift_scale"])
    carry_definition = str(config["ode"]["carry_definition"])
    failure_penalty = float(config["ode"]["calibration_failure_penalty"])
    local_optimization = dict(config["ode"]["local_optimization"])
    calibration_solver = dict(config["ode"]["solver"])
    calibration_solver["max_step"] = float(config["ode"]["lift_calibration"].get("solver_max_step", calibration_solver["max_step"]))
    cd, drag_surface, drag_runs = calibrate_drag_cd(
        drag_representative,
        constants=constants,
        solver=calibration_solver,
        bounds=cd_bounds,
        grid_size=int(config["ode"]["drag_calibration"]["grid_size"]),
        local_optimization=local_optimization,
        carry_definition=carry_definition,
        failure_penalty=failure_penalty,
        full_train_records=ode_train,
        return_runs=True,
    )
    constant_params, constant_surface, constant_runs = calibrate_lift_parameters(
        lift_representative,
        constants=constants,
        solver=calibration_solver,
        cd_bounds=cd_bounds,
        lift_bounds=cl_bounds,
        grid_size=int(config["ode"]["lift_calibration"]["grid_size"]),
        model="constant_lift",
        side_sign=selected_sign,
        lateral_weight=float(config["ode"]["lift_calibration"]["lateral_weight"]),
        local_optimization=local_optimization,
        carry_definition=carry_definition,
        failure_penalty=failure_penalty,
        full_train_records=ode_train,
        return_runs=True,
    )
    spin_params, spin_surface, spin_runs = calibrate_lift_parameters(
        lift_representative,
        constants=constants,
        solver=calibration_solver,
        cd_bounds=cd_bounds,
        lift_bounds=lift_scale_bounds,
        grid_size=int(config["ode"]["lift_calibration"]["grid_size"]),
        model="spin_factor_lift",
        side_sign=selected_sign,
        lateral_weight=float(config["ode"]["lift_calibration"]["lateral_weight"]),
        local_optimization=local_optimization,
        carry_definition=carry_definition,
        failure_penalty=failure_penalty,
        full_train_records=ode_train,
        return_runs=True,
    )
    surface = pd.concat([drag_surface, constant_surface, spin_surface], ignore_index=True)
    tables["q2_ode_parameter_surface"] = save_table(
        surface, stem="q2_ode_parameter_surface", question_dir=question_dir
    )["csv"]
    tables["q2_drag_optimization_runs"] = save_table(
        drag_runs, stem="q2_drag_optimization_runs", question_dir=question_dir
    )["csv"]
    tables["q2_constant_lift_optimization_runs"] = save_table(
        constant_runs, stem="q2_constant_lift_optimization_runs", question_dir=question_dir
    )["csv"]
    tables["q2_spin_factor_optimization_runs"] = save_table(
        spin_runs, stem="q2_spin_factor_optimization_runs", question_dir=question_dir
    )["csv"]
    model_parameters = {
        "vacuum": {"cd": 0.0, "cl": 0.0, "lift_scale": 0.0},
        "drag": {"cd": cd, "cl": 0.0, "lift_scale": 0.0},
        "constant_lift": constant_params,
        "spin_factor_lift": spin_params,
    }
    q3_compatible_ode = "spin_factor_lift"
    selected_runs = {
        "drag": drag_runs[drag_runs["selected"].astype(bool)].iloc[0],
        "constant_lift": constant_runs[constant_runs["selected"].astype(bool)].iloc[0],
        "spin_factor_lift": spin_runs[spin_runs["selected"].astype(bool)].iloc[0],
    }
    candidate_models = ["drag", "constant_lift", "spin_factor_lift"]
    valid_full_train_objectives = {
        model: float(run["full_train_objective"])
        for model, run in selected_runs.items()
        if bool(run["accepted"]) and int(run["full_train_failed_count"]) == 0
    }
    if set(candidate_models) - set(valid_full_train_objectives):
        missing = sorted(set(candidate_models) - set(valid_full_train_objectives))
        raise RuntimeError(f"q2 ODE calibration has no accepted full-train result for: {missing}")
    q2_best_fit_ode = min(candidate_models, key=lambda model: valid_full_train_objectives[model])
    model_variants = list(config["ode"]["model_variants"])
    ode_outputs = evaluate_ode_models(
        ode_test,
        constants=constants,
        solver=config["ode"]["solver"],
        parameters=model_parameters,
        carry_definition=carry_definition,
        model_variants=model_variants,
        side_sign=selected_sign,
    )
    for key, stem in [
        ("predictions", "q2_ode_test_predictions"),
        ("metrics", "q2_ode_test_metrics"),
        ("comparison", "q2_ode_model_comparison"),
        ("failures", "q2_ode_failures"),
    ]:
        tables[stem] = save_table(ode_outputs[key], stem=stem, question_dir=question_dir)["csv"]
    tables["q2_carry_definition_comparison"] = save_table(
        carry_definition_comparison(ode_outputs["predictions"], primary_definition=carry_definition),
        stem="q2_carry_definition_comparison",
        question_dir=question_dir,
    )["csv"]
    failure_table_specs = [
        (
            "q2_drag_calibration_failures",
            calibration_failure_rows(
                drag_representative,
                model="drag",
                constants=constants,
                solver=calibration_solver,
                params=model_parameters["drag"],
                side_sign=selected_sign,
                carry_definition=carry_definition,
                stage="calibration_representative",
            ),
        ),
        (
            "q2_constant_lift_calibration_failures",
            calibration_failure_rows(
                lift_representative,
                model="constant_lift",
                constants=constants,
                solver=calibration_solver,
                params=model_parameters["constant_lift"],
                side_sign=selected_sign,
                carry_definition=carry_definition,
                stage="calibration_representative",
            ),
        ),
        (
            "q2_spin_factor_calibration_failures",
            calibration_failure_rows(
                lift_representative,
                model="spin_factor_lift",
                constants=constants,
                solver=calibration_solver,
                params=model_parameters["spin_factor_lift"],
                side_sign=selected_sign,
                carry_definition=carry_definition,
                stage="calibration_representative",
            ),
        ),
    ]
    for stem, frame in failure_table_specs:
        tables[stem] = save_table(frame, stem=stem, question_dir=question_dir)["csv"]

    typical_records = select_typical_records(ode_test, required_features=ODE_REQUIRED_FEATURES)
    typical_source = typical_records.merge(
        ode_test,
        on="record_id",
        how="left",
        suffixes=("", "_source"),
    )
    tables["q2_typical_records"] = save_table(
        typical_records, stem="q2_typical_records", question_dir=question_dir
    )["csv"]
    typical_errors, constant_trajectories = typical_errors_and_trajectories(
        typical_source,
        constants=constants,
        solver=config["ode"]["solver"],
        parameters=model_parameters,
        model_variants=model_variants,
        trajectory_model="constant_lift",
        side_sign=selected_sign,
        carry_definition=carry_definition,
    )
    _spin_errors, spin_trajectories = typical_errors_and_trajectories(
        typical_source,
        constants=constants,
        solver=config["ode"]["solver"],
        parameters=model_parameters,
        model_variants=model_variants,
        trajectory_model=q3_compatible_ode,
        side_sign=selected_sign,
        carry_definition=carry_definition,
    )
    trajectories = pd.concat([constant_trajectories, spin_trajectories], ignore_index=True)
    tables["q2_ode_typical_errors"] = save_table(
        typical_errors, stem="q2_ode_typical_errors", question_dir=question_dir
    )["csv"]
    tables["q2_typical_trajectories_constant_lift"] = save_table(
        constant_trajectories, stem="q2_typical_trajectories_constant_lift", question_dir=question_dir
    )["csv"]
    tables["q2_typical_trajectories_spin_factor"] = save_table(
        spin_trajectories, stem="q2_typical_trajectories_spin_factor", question_dir=question_dir
    )["csv"]
    tables["q2_typical_trajectories"] = save_table(
        trajectories, stem="q2_typical_trajectories", question_dir=question_dir
    )["csv"]
    sensitivity = ode_sensitivity(
        typical_source,
        constants=constants,
        solver=config["ode"]["solver"],
        baseline_params={
            "constant_lift": model_parameters["constant_lift"],
            q3_compatible_ode: model_parameters[q3_compatible_ode],
        },
        relative_changes=[float(value) for value in config["ode"]["sensitivity_relative_changes"]],
        side_sign=selected_sign,
        carry_definition=carry_definition,
        models=["constant_lift", q3_compatible_ode],
        initial_heights_m=[0.001, 0.01, 0.05],
    )
    tables["q2_ode_sensitivity"] = save_table(
        sensitivity, stem="q2_ode_sensitivity", question_dir=question_dir
    )["csv"]

    ode_metric_frame = ode_outputs["metrics"].set_index("model")
    drag_lower_bound = abs(float(cd) - cd_bounds[0]) <= max((cd_bounds[1] - cd_bounds[0]) * 1e-8, 1e-12)
    drag_worse_than_vacuum = (
        float(ode_metric_frame.loc["drag", "carry_rmse"]) > float(ode_metric_frame.loc["vacuum", "carry_rmse"])
    )
    drag_status = "boundary_solution" if drag_lower_bound and drag_worse_than_vacuum else "ok"
    best_drag_run = selected_runs["drag"]
    best_constant_run = selected_runs["constant_lift"]
    best_spin_run = selected_runs["spin_factor_lift"]
    parameter_rows = [
        parameter_boundary_row(
            model="drag",
            parameter="C_D",
            value=cd,
            lower_bound=cd_bounds[0],
            upper_bound=cd_bounds[1],
            calibration_stage="coarse_grid_plus_bounded_local_optimization",
            source="train split drag representative records; fixed test split excluded",
            full_train_objective=float(best_drag_run["full_train_objective"]),
            parameter_status=drag_status,
        ),
        parameter_boundary_row(
            model="constant_lift",
            parameter="C_D",
            value=constant_params["cd"],
            lower_bound=cd_bounds[0],
            upper_bound=cd_bounds[1],
            calibration_stage="coarse_grid_plus_bounded_local_optimization",
            source="train split lift representative records with constant C_L",
            full_train_objective=float(best_constant_run["full_train_objective"]),
        ),
        parameter_boundary_row(
            model="constant_lift",
            parameter="C_L",
            value=constant_params["cl"],
            lower_bound=cl_bounds[0],
            upper_bound=cl_bounds[1],
            calibration_stage="coarse_grid_plus_bounded_local_optimization",
            source="train split lift representative records with constant C_L",
            full_train_objective=float(best_constant_run["full_train_objective"]),
        ),
        parameter_boundary_row(
            model="spin_factor_lift",
            parameter="C_D",
            value=spin_params["cd"],
            lower_bound=cd_bounds[0],
            upper_bound=cd_bounds[1],
            calibration_stage="coarse_grid_plus_bounded_local_optimization",
            source="train split lift representative records with C_L(S)=k_L*S",
            full_train_objective=float(best_spin_run["full_train_objective"]),
        ),
        parameter_boundary_row(
            model="spin_factor_lift",
            parameter="k_L",
            value=spin_params["lift_scale"],
            lower_bound=lift_scale_bounds[0],
            upper_bound=lift_scale_bounds[1],
            calibration_stage="coarse_grid_plus_bounded_local_optimization",
            source="train split lift representative records with C_L(S)=k_L*S",
            full_train_objective=float(best_spin_run["full_train_objective"]),
        ),
        parameter_boundary_row(
            model="physics",
            parameter="mass_kg",
            value=constants.mass_kg,
            lower_bound="",
            upper_bound="",
            calibration_stage="fixed_from_problem_statement",
            source=constants.source,
        ),
        parameter_boundary_row(
            model="physics",
            parameter="radius_m",
            value=constants.radius_m,
            lower_bound="",
            upper_bound="",
            calibration_stage="fixed_from_problem_statement",
            source=constants.source,
        ),
        parameter_boundary_row(
            model="physics",
            parameter="air_density_kg_m3",
            value=constants.air_density_kg_m3,
            lower_bound="",
            upper_bound="",
            calibration_stage="fixed_from_problem_statement",
            source=constants.source,
        ),
        parameter_boundary_row(
            model="physics",
            parameter="gravity_m_s2",
            value=constants.gravity_m_s2,
            lower_bound="",
            upper_bound="",
            calibration_stage="fixed_from_problem_statement",
            source=constants.source,
        ),
        parameter_boundary_row(
            model="physics",
            parameter="initial_height_m",
            value=constants.initial_height_m,
            lower_bound="",
            upper_bound="",
            calibration_stage=constants.initial_height_type,
            source="Numerical convention to avoid immediate ground-event detection; not measured tee height.",
        ),
    ]
    tables["q2_ode_parameters"] = save_table(
        parameter_rows, stem="q2_ode_parameters", question_dir=question_dir
    )["csv"]
    parameter_json = {
        "side_spin_sign": selected_sign,
        "carry_definition": carry_definition,
        "ode_solver": config["ode"]["solver"],
        "best_fit_ode_model": q2_best_fit_ode,
        "best_fit_selection_rule": "minimum_full_train_objective_among_accepted_models",
        "q3_compatible_ode_model": q3_compatible_ode,
        "model_parameters": model_parameters,
        "full_train_objectives": valid_full_train_objectives,
        "calibration": {
            "drag_records": int(len(drag_representative)),
            "lift_records": int(len(lift_representative)),
            "drag_grid_size": int(config["ode"]["drag_calibration"]["grid_size"]),
            "lift_grid_size": int(config["ode"]["lift_calibration"]["grid_size"]),
            "solver": calibration_solver,
            "local_optimization": local_optimization,
            "failure_penalty": failure_penalty,
            "source": "train split representative records only; fixed test split excluded from calibration",
        },
    }
    parameters_json_path = question_dir / "artifacts" / "models" / "q2_ode_parameters.json"
    parameters_json_path.parent.mkdir(parents=True, exist_ok=True)
    with parameters_json_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(parameter_json, ensure_ascii=False, indent=2))
    ode_check_frame = ode_validation_checks(
        ode_test.iloc[0],
        constants=constants,
        solver=config["ode"]["solver"],
        carry_definition=carry_definition,
        cd=cd,
        cl=constant_params["cl"],
        lift_scale=spin_params["lift_scale"],
        side_sign=selected_sign,
    )
    q3_boundary_checks = q3_boundary_stability_checks(
        pd.concat([ode_train, ode_test], ignore_index=True),
        constants=constants,
        solver=config["ode"]["solver"],
        params=model_parameters[q3_compatible_ode],
        side_sign=selected_sign,
        carry_definition=carry_definition,
    )
    ode_check_frame = pd.concat(
        [
            ode_check_frame,
            q3_boundary_checks,
            pd.DataFrame(
                [
                    {
                        "check": "full_ode_variants_present",
                        "passed": {"vacuum", "drag", "constant_lift", "spin_factor_lift"}.issubset(
                            set(model_variants)
                        ),
                        "value": float(len(model_variants)),
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["q2_ode_validation_checks"] = save_table(
        ode_check_frame,
        stem="q2_ode_validation_checks",
        question_dir=question_dir,
    )["csv"]

    figure_outputs = create_visualizations(
        root=root,
        dpi=int(config.get("plotting", {}).get("dpi", 300)),
    )

    selected = supervised_outputs["metrics"][supervised_outputs["metrics"]["selected"].astype(bool)]
    summary = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": current_git_commit(root),
        "python_version": platform.python_version(),
        "package_versions": package_versions(),
        "config_path": rel_posix(root / config_path, root),
        "config_sha256": file_sha256(root / config_path),
        "data_path": rel_posix(root / config["input_path"], root),
        "data_sha256": file_sha256(root / config["input_path"]),
        "train_ids_sha256": values_sha256(split.loc[split["split"] == "train", "record_id"]),
        "test_ids_sha256": values_sha256(split.loc[split["split"] == "test", "record_id"]),
        "drag_calibration_record_ids": drag_representative["record_id"].astype(int).tolist(),
        "lift_calibration_record_ids": lift_representative["record_id"].astype(int).tolist(),
        "carry_definition": carry_definition,
        "best_fit_ode_model": q2_best_fit_ode,
        "best_fit_selection_rule": "minimum_full_train_objective_among_accepted_models",
        "full_train_objectives": valid_full_train_objectives,
        "q3_compatible_ode_model": q3_compatible_ode,
        "q3_compatible_boundary_checks_passed": bool(q3_boundary_checks["passed"].astype(bool).all()),
        "train_n": int(len(train)),
        "test_n": int(len(test)),
        "ode_train_n": int(len(ode_train)),
        "ode_test_n": int(len(ode_test)),
        "selected_supervised_models": [
            f"{row.target}:{row.feature_set}/{row.model}" for row in selected.itertuples(index=False)
        ],
        "preliminary_drag_cd": float(cd),
        "constant_lift_cd": float(constant_params["cd"]),
        "constant_lift_cl": float(constant_params["cl"]),
        "spin_factor_lift_cd": float(spin_params["cd"]),
        "spin_factor_lift_k_l": float(spin_params["lift_scale"]),
        "side_spin_sign": selected_sign,
        "physics_source": constants.source,
        "initial_height_m": constants.initial_height_m,
        "initial_height_type": constants.initial_height_type,
        "optimization_runs": {
            "drag": rel_posix(tables["q2_drag_optimization_runs"], root),
            "constant_lift": rel_posix(tables["q2_constant_lift_optimization_runs"], root),
            "spin_factor_lift": rel_posix(tables["q2_spin_factor_optimization_runs"], root),
        },
        "tables": {name: rel_posix(path, root) for name, path in tables.items()},
        "models": {"q2_ode_parameters": rel_posix(parameters_json_path, root)},
        "figures": {
            name: {kind: rel_posix(path, root) for kind, path in paths.items()}
            for name, paths in figure_outputs.items()
        },
    }
    metadata_path = question_dir / "artifacts" / "run_metadata.json"
    with metadata_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False, indent=2))

    checks = validate_outputs(root, config_path=config_path, require_validation_table=False)
    tables["q2_validation_checks"] = save_table(
        checks, stem="q2_validation_checks", question_dir=question_dir
    )["csv"]
    failed = checks[~checks["passed"]]
    if not failed.empty:
        raise RuntimeError(f"q2 validation failed after pipeline run: {failed['check'].tolist()}")
    return summary


if __name__ == "__main__":
    raise SystemExit(main())
