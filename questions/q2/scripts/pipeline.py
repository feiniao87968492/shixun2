#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
from pathlib import Path

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
    evaluate_ode_models,
    validation_checks as ode_validation_checks,
)
from preprocessing import (  # noqa: E402
    ODE_REQUIRED_FEATURES,
    fixed_train_test_split,
    load_clean_data,
    load_project_config,
    select_drag_calibration_records,
    spin_geometry_check,
    split_frames,
)
from supervised import run_supervised_models  # noqa: E402
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
    tables["q2_spin_geometry_check"] = save_table(
        spin_geometry_check(clean), stem="q2_spin_geometry_check", question_dir=question_dir
    )["csv"]

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

    constants = PhysicalConstants.from_config(config["physics"])
    ode_required = [*ODE_REQUIRED_FEATURES, "carry_distance_yd", "apex_height_yd", "lateral_offset_yd"]
    ode_train = train.dropna(subset=ode_required).reset_index(drop=True)
    ode_test = test.dropna(subset=ode_required).reset_index(drop=True)
    representative = select_drag_calibration_records(
        ode_train,
        required_features=ODE_REQUIRED_FEATURES,
        representative_count=int(config["ode"]["drag_calibration"]["representative_count"]),
    )
    tables["q2_ode_representative_records"] = save_table(
        representative, stem="q2_ode_representative_records", question_dir=question_dir
    )["csv"]
    cd_bounds = tuple(float(value) for value in config["ode"]["parameter_bounds"]["cd"])
    cd, surface = calibrate_drag_cd(
        representative,
        constants=constants,
        solver=config["ode"]["solver"],
        bounds=cd_bounds,
        grid_size=int(config["ode"]["drag_calibration"]["grid_size"]),
    )
    tables["q2_ode_parameter_surface"] = save_table(
        surface, stem="q2_ode_parameter_surface", question_dir=question_dir
    )["csv"]
    ode_outputs = evaluate_ode_models(ode_test, constants=constants, solver=config["ode"]["solver"], cd=cd)
    for key, stem in [
        ("predictions", "q2_ode_test_predictions"),
        ("metrics", "q2_ode_test_metrics"),
        ("comparison", "q2_ode_model_comparison"),
        ("failures", "q2_ode_failures"),
    ]:
        tables[stem] = save_table(ode_outputs[key], stem=stem, question_dir=question_dir)["csv"]

    parameter_rows = [
        {
            "model": "drag",
            "parameter": "C_D",
            "value": cd,
            "lower_bound": cd_bounds[0],
            "upper_bound": cd_bounds[1],
            "calibration_stage": str(config["ode"]["drag_calibration"]["calibration_stage"]),
            "source": "training split preliminary grid scan; not final C_D/C_L calibration",
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
    tables["q2_ode_validation_checks"] = save_table(
        ode_validation_checks(ode_test.iloc[0], constants=constants, solver=config["ode"]["solver"], cd=cd),
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
        "physics_source": constants.source,
        "tables": {name: str(path.relative_to(root)) for name, path in tables.items()},
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
