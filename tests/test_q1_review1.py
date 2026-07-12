from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "questions" / "q1" / "scripts"
TABLES = ROOT / "questions" / "q1" / "artifacts" / "tables"


def load_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_invalid_zero_measurements_are_corrected_and_audited() -> None:
    preprocessing = load_module("preprocessing.py", "q1_preprocessing")

    raw = preprocessing.load_data(ROOT)
    clean, invalid_zero_records = preprocessing.replace_invalid_zero_values(raw)

    assert set(invalid_zero_records["record_id"]) == {225, 226, 308}
    assert invalid_zero_records["club_speed_invalid_zero"].sum() == 3
    assert invalid_zero_records["attack_angle_invalid_zero"].sum() == 3
    assert clean["club_speed_mph"].isna().sum() == 66
    assert clean["attack_angle_deg"].isna().sum() == 68
    assert not clean["club_speed_mph"].eq(0).any()
    assert not clean["attack_angle_deg"].eq(0).any()


def test_review1_required_tables_and_numeric_validation_checks_are_registered() -> None:
    analysis = load_module("analysis.py", "q1_analysis_review1")
    checks = analysis.validate_outputs(ROOT)

    required_tables = {
        "q1_invalid_zero_records.csv",
        "q1_outlier_audit.csv",
        "q1_model_performance.csv",
        "q1_ridge_coefficients.csv",
        "q1_permutation_importance.csv",
        "q1_spin_representation_comparison.csv",
        "q1_sample_definition_comparison.csv",
        "q1_feature_summary.csv",
    }
    assert required_tables.issubset(set(checks["check"]))
    assert {"numeric", "schema", "reproducibility"}.issubset(set(checks["kind"]))


def test_feature_summary_uses_layered_categories_not_only_aggregate_rank() -> None:
    import pandas as pd

    summary_path = TABLES / "q1_feature_summary.csv"
    assert summary_path.exists()
    summary = pd.read_csv(summary_path)

    required_columns = {
        "feature",
        "marginal_rank",
        "ridge_abs_rank",
        "permutation_rank",
        "stability_category",
        "final_interpretation",
    }
    assert required_columns.issubset(summary.columns)
    assert "aggregate_score" not in summary.columns
    attack = summary.loc[summary["feature"] == "attack_angle_deg"].iloc[0]
    assert attack["stability_category"] != "stable_key"
