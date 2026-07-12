#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
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
    evaluate_ode_models,
    ode_sensitivity,
    typical_errors_and_trajectories,
    validation_checks as ode_validation_checks,
)
from preprocessing import (  # noqa: E402
    ODE_REQUIRED_FEATURES,
    fixed_train_test_split,
    load_clean_data,
    load_project_config,
    select_typical_records,
    select_drag_calibration_records,
    spin_geometry_check,
    split_frames,
)
from supervised import run_repeated_split_stability, run_supervised_models  # noqa: E402
from validate import validate_outputs  # noqa: E402
from visualize import create_visualizations  # noqa: E402

IMPLEMENTED = True


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
    representative = select_drag_calibration_records(
        ode_train,
        required_features=ODE_REQUIRED_FEATURES,
        representative_count=int(config["ode"]["lift_calibration"]["representative_count"]),
    )
    tables["q2_ode_representative_records"] = save_table(
        representative, stem="q2_ode_representative_records", question_dir=question_dir
    )["csv"]
    cd_bounds = tuple(float(value) for value in config["ode"]["parameter_bounds"]["cd"])
    cl_bounds = tuple(float(value) for value in config["ode"]["parameter_bounds"]["cl"])
    lift_scale_bounds = tuple(float(value) for value in config["ode"]["parameter_bounds"]["lift_scale"])
    calibration_solver = dict(config["ode"]["solver"])
    calibration_solver["max_step"] = float(config["ode"]["lift_calibration"].get("solver_max_step", calibration_solver["max_step"]))
    cd, surface = calibrate_drag_cd(
        representative,
        constants=constants,
        solver=calibration_solver,
        bounds=cd_bounds,
        grid_size=int(config["ode"]["lift_calibration"]["grid_size"]),
    )
    constant_params, constant_surface = calibrate_lift_parameters(
        representative,
        constants=constants,
        solver=calibration_solver,
        cd_bounds=cd_bounds,
        lift_bounds=cl_bounds,
        grid_size=int(config["ode"]["lift_calibration"]["grid_size"]),
        model="constant_lift",
        side_sign=selected_sign,
        lateral_weight=float(config["ode"]["lift_calibration"]["lateral_weight"]),
    )
    spin_params, spin_surface = calibrate_lift_parameters(
        representative,
        constants=constants,
        solver=calibration_solver,
        cd_bounds=cd_bounds,
        lift_bounds=lift_scale_bounds,
        grid_size=int(config["ode"]["lift_calibration"]["grid_size"]),
        model="spin_factor_lift",
        side_sign=selected_sign,
        lateral_weight=float(config["ode"]["lift_calibration"]["lateral_weight"]),
    )
    surface = pd.concat([surface, constant_surface, spin_surface], ignore_index=True)
    tables["q2_ode_parameter_surface"] = save_table(
        surface, stem="q2_ode_parameter_surface", question_dir=question_dir
    )["csv"]
    model_parameters = {
        "vacuum": {"cd": 0.0, "cl": 0.0, "lift_scale": 0.0},
        "drag": {"cd": cd, "cl": 0.0, "lift_scale": 0.0},
        "constant_lift": constant_params,
        "spin_factor_lift": spin_params,
    }
    model_variants = list(config["ode"]["model_variants"])
    ode_outputs = evaluate_ode_models(
        ode_test,
        constants=constants,
        solver=config["ode"]["solver"],
        parameters=model_parameters,
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
    trajectory_model = "spin_factor_lift"
    typical_errors, trajectories = typical_errors_and_trajectories(
        typical_source,
        constants=constants,
        solver=config["ode"]["solver"],
        parameters=model_parameters,
        model_variants=model_variants,
        trajectory_model=trajectory_model,
        side_sign=selected_sign,
    )
    tables["q2_ode_typical_errors"] = save_table(
        typical_errors, stem="q2_ode_typical_errors", question_dir=question_dir
    )["csv"]
    tables["q2_typical_trajectories"] = save_table(
        trajectories, stem="q2_typical_trajectories", question_dir=question_dir
    )["csv"]
    sensitivity = ode_sensitivity(
        typical_source,
        constants=constants,
        solver=config["ode"]["solver"],
        baseline_params=model_parameters[trajectory_model],
        relative_changes=[float(value) for value in config["ode"]["sensitivity_relative_changes"]],
        side_sign=selected_sign,
    )
    tables["q2_ode_sensitivity"] = save_table(
        sensitivity, stem="q2_ode_sensitivity", question_dir=question_dir
    )["csv"]

    parameter_rows = [
        {
            "model": "drag",
            "parameter": "C_D",
            "value": cd,
            "lower_bound": cd_bounds[0],
            "upper_bound": cd_bounds[1],
            "calibration_stage": "train_representative_grid",
            "source": "train split representative grid scan; final drag-only baseline",
        },
        {
            "model": "constant_lift",
            "parameter": "C_D",
            "value": constant_params["cd"],
            "lower_bound": cd_bounds[0],
            "upper_bound": cd_bounds[1],
            "calibration_stage": str(config["ode"]["lift_calibration"]["calibration_stage"]),
            "source": "train split representative grid scan with constant C_L",
        },
        {
            "model": "constant_lift",
            "parameter": "C_L",
            "value": constant_params["cl"],
            "lower_bound": cl_bounds[0],
            "upper_bound": cl_bounds[1],
            "calibration_stage": str(config["ode"]["lift_calibration"]["calibration_stage"]),
            "source": "train split representative grid scan with constant C_L",
        },
        {
            "model": "spin_factor_lift",
            "parameter": "C_D",
            "value": spin_params["cd"],
            "lower_bound": cd_bounds[0],
            "upper_bound": cd_bounds[1],
            "calibration_stage": str(config["ode"]["lift_calibration"]["calibration_stage"]),
            "source": "train split representative grid scan with C_L(S)=k_L*S",
        },
        {
            "model": "spin_factor_lift",
            "parameter": "k_L",
            "value": spin_params["lift_scale"],
            "lower_bound": lift_scale_bounds[0],
            "upper_bound": lift_scale_bounds[1],
            "calibration_stage": str(config["ode"]["lift_calibration"]["calibration_stage"]),
            "source": "train split representative grid scan with C_L(S)=k_L*S",
        },
        {
            "model": "physics",
            "parameter": "mass_kg",
            "value": constants.mass_kg,
            "lower_bound": "",
            "upper_bound": "",
            "calibration_stage": "fixed_from_problem_statement",
            "source": constants.source,
        },
        {
            "model": "physics",
            "parameter": "radius_m",
            "value": constants.radius_m,
            "lower_bound": "",
            "upper_bound": "",
            "calibration_stage": "fixed_from_problem_statement",
            "source": constants.source,
        },
        {
            "model": "physics",
            "parameter": "air_density_kg_m3",
            "value": constants.air_density_kg_m3,
            "lower_bound": "",
            "upper_bound": "",
            "calibration_stage": "fixed_from_problem_statement",
            "source": constants.source,
        },
        {
            "model": "physics",
            "parameter": "gravity_m_s2",
            "value": constants.gravity_m_s2,
            "lower_bound": "",
            "upper_bound": "",
            "calibration_stage": "fixed_from_problem_statement",
            "source": constants.source,
        },
    ]
    tables["q2_ode_parameters"] = save_table(
        parameter_rows, stem="q2_ode_parameters", question_dir=question_dir
    )["csv"]
    parameter_json = {
        "side_spin_sign": selected_sign,
        "trajectory_model": trajectory_model,
        "model_parameters": model_parameters,
        "calibration": {
            "records": int(len(representative)),
            "grid_size": int(config["ode"]["lift_calibration"]["grid_size"]),
            "solver": calibration_solver,
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
        cd=cd,
        cl=constant_params["cl"],
        lift_scale=spin_params["lift_scale"],
        side_sign=selected_sign,
    )
    ode_check_frame = pd.concat(
        [
            ode_check_frame,
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
    checks = validate_outputs(root, require_validation_table=False)
    tables["q2_validation_checks"] = save_table(
        checks, stem="q2_validation_checks", question_dir=question_dir
    )["csv"]
    failed = checks[~checks["passed"]]
    if not failed.empty:
        raise RuntimeError(f"q2 validation failed after pipeline run: {failed['check'].tolist()}")

    selected = supervised_outputs["metrics"][supervised_outputs["metrics"]["selected"].astype(bool)]
    summary = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "config_path": str((root / config_path).relative_to(root)),
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
        "trajectory_model": trajectory_model,
        "side_spin_sign": selected_sign,
        "physics_source": constants.source,
        "tables": {name: str(path.relative_to(root)) for name, path in tables.items()},
        "models": {"q2_ode_parameters": str(parameters_json_path.relative_to(root))},
        "figures": {
            name: {kind: str(path.relative_to(root)) for kind, path in paths.items()}
            for name, paths in figure_outputs.items()
        },
    }
    metadata_path = question_dir / "artifacts" / "run_metadata.json"
    with metadata_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    raise SystemExit(main())
