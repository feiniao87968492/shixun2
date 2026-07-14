from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
Q2 = ROOT / "questions" / "q2"
Q3 = ROOT / "questions" / "q3"
RELEASE_MANIFEST = ROOT / "docs" / "reproducibility" / "q2_q3_release_manifest.json"

CORE_CSVS = [
    "questions/q2/artifacts/tables/q2_ode_parameters.csv",
    "questions/q2/artifacts/tables/q2_ode_test_metrics.csv",
    "questions/q2/artifacts/tables/q2_ode_test_predictions.csv",
    "questions/q2/artifacts/tables/q2_validation_checks.csv",
    "questions/q3/artifacts/tables/q3_optimal_parameters.csv",
    "questions/q3/artifacts/tables/q3_joint_robustness_summary.csv",
    "questions/q3/artifacts/tables/q3_target_optimal_parameters.csv",
    "questions/q3/artifacts/tables/q3_near_optimal_parameter_ranges.csv",
    "questions/q3/artifacts/tables/q3_ode_crosscheck.csv",
    "questions/q3/artifacts/tables/q3_validation_checks.csv",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    assert path.exists(), f"missing JSON artifact: {path.relative_to(ROOT)}"
    return json.loads(path.read_text(encoding="utf-8"))


def load_ode_module() -> Any:
    spec = importlib.util.spec_from_file_location("q2_task7_ode_model", Q2 / "scripts" / "ode_model.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_q2_solver_uses_configured_time_horizon_and_reports_horizon_status() -> None:
    config = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))["q2"]
    solver = dict(config["ode"]["solver"])
    assert solver["max_flight_time_s"] == pytest.approx(20.0)

    ode_model = load_ode_module()
    constants = ode_model.PhysicalConstants.from_config(config["physics"])
    row = pd.Series(
        {
            "ball_speed_mph": 120.0,
            "launch_angle_deg": 20.0,
            "launch_direction_deg": 0.0,
            "spin_rate_rpm": 2500.0,
            "spin_axis_deg": 0.0,
        }
    )
    short_solver = dict(solver)
    short_solver["max_flight_time_s"] = 0.001
    prediction, _trajectory = ode_model.simulate_shot(
        row,
        model="vacuum",
        constants=constants,
        solver=short_solver,
        carry_definition="forward_x",
    )

    assert prediction["integration_status"] == "time_horizon_exceeded"
    assert prediction["solver_success"] is True
    assert prediction["flight_time_s"] == pytest.approx(0.001, abs=1e-6)


def test_release_manifest_records_current_q2_q3_artifact_hashes() -> None:
    manifest = read_json(RELEASE_MANIFEST)
    q2_metadata = Q2 / "artifacts" / "run_metadata.json"
    q3_metadata = Q3 / "artifacts" / "run_metadata.json"

    assert manifest["git_commit"]
    assert manifest["config_sha256"] == sha256(ROOT / "configs" / "default.yaml")
    assert manifest["data_sha256"] == sha256(ROOT / "data" / "processed" / "golf_shots_clean.csv")
    assert manifest["q2_run_metadata_sha256"] == sha256(q2_metadata)
    assert manifest["q3_run_metadata_sha256"] == sha256(q3_metadata)

    csv_hashes = manifest["core_csv_sha256"]
    assert set(CORE_CSVS).issubset(csv_hashes)
    for rel_path in CORE_CSVS:
        assert csv_hashes[rel_path] == sha256(ROOT / rel_path)


def test_q3_metadata_and_dependency_audit_use_current_q2_metadata_hash() -> None:
    q2_metadata_path = Q2 / "artifacts" / "run_metadata.json"
    q3_metadata = read_json(Q3 / "artifacts" / "run_metadata.json")
    q2_metadata = read_json(q2_metadata_path)
    q2_metadata_hash = sha256(q2_metadata_path)

    assert q3_metadata["q2"]["run_metadata_sha256"] == q2_metadata_hash
    assert q3_metadata["q2"]["carry_definition"] == q2_metadata["carry_definition"] == "forward_x"
    assert q3_metadata["q2"]["q3_compatible_ode_model"] == q2_metadata["q3_compatible_ode_model"]

    audit = pd.read_csv(Q3 / "artifacts" / "tables" / "q3_dependency_audit.csv")
    audit_values = audit.set_index("check")["value"].to_dict()
    assert audit_values["q2_run_metadata_sha256"] == q2_metadata_hash
    assert audit_values["q2_carry_definition"] == "forward_x"


def test_q3_documented_parameters_are_recomputable_from_current_csv() -> None:
    optimal = pd.read_csv(Q3 / "artifacts" / "tables" / "q3_optimal_parameters.csv")
    rec = optimal.set_index("candidate_type").loc["joint_robust_recommended_optimum"]

    q3_readme = (Q3 / "README.md").read_text(encoding="utf-8")
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    expected_strings = [
        f"{float(rec['ball_speed_mph']):.3f}",
        f"{float(rec['launch_angle_deg']):.3f}",
        f"{float(rec['spin_rate_rpm']):.3f}",
        f"{float(rec['spin_axis_deg']):.3f}",
        f"{float(rec['joint_p90_miss_distance_yd']):.3f}",
    ]
    for text in expected_strings:
        assert text in q3_readme
        assert text in root_readme


def test_q3_ode_crosscheck_all_current_candidates_integrate_successfully() -> None:
    crosscheck = pd.read_csv(Q3 / "artifacts" / "tables" / "q3_ode_crosscheck.csv")
    assert not crosscheck.empty
    required_types = {
        "best_observed_baseline",
        "nominal_optimum",
        "joint_robust_recommended_optimum",
    }
    assert required_types.issubset(set(crosscheck["candidate_type"]))
    assert crosscheck["integration_status"].eq("success").all()
