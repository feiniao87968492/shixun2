from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_PATH = ROOT / "questions" / "q1" / "scripts" / "analysis.py"


def load_analysis_module():
    spec = importlib.util.spec_from_file_location("q1_analysis", ANALYSIS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_and_clean_golf_data_uses_real_header_and_canonical_columns() -> None:
    analysis = load_analysis_module()

    raw = analysis.load_raw_golf_data(ROOT)
    clean = analysis.clean_golf_data(raw)

    assert len(clean) == 735
    assert "ball_speed_mph" in clean.columns
    assert "carry_distance_yd" in clean.columns
    assert clean["record_id"].is_unique
    assert clean["club_speed_mph"].isna().sum() == 63
    assert clean["attack_angle_deg"].isna().sum() == 65


def test_sample_views_enforce_missing_value_and_spin_representation_contracts() -> None:
    analysis = load_analysis_module()
    clean = analysis.clean_golf_data(analysis.load_raw_golf_data(ROOT))

    views = analysis.build_sample_views(clean)

    assert {"S1_core", "S2_complete", "S3_imputed"}.issubset(views)
    assert "club_speed_mph" not in views["S1_core"].features
    assert "attack_angle_deg" not in views["S1_core"].features
    assert "spin_rate_rpm" in views["S1_core"].features
    assert "backspin_rpm" not in views["S1_core"].features
    assert len(views["S2_complete"].frame) < len(clean)
    assert views["S3_imputed"].frame[views["S3_imputed"].features].isna().sum().sum() == 0
    assert {"club_speed_missing", "attack_angle_missing"}.issubset(views["S3_imputed"].features)


def test_correlations_are_long_form_complete_and_finite() -> None:
    analysis = load_analysis_module()
    clean = analysis.clean_golf_data(analysis.load_raw_golf_data(ROOT))

    correlations = analysis.compute_correlations(clean, analysis.INPUT_FEATURES, analysis.OUTPUT_COLUMNS)

    assert {"pearson", "spearman", "kendall"}.issubset(correlations)
    for table in correlations.values():
        assert {"feature", "output", "correlation", "n"}.issubset(table.columns)
        assert set(table["output"]) == set(analysis.OUTPUT_COLUMNS)
        assert table["correlation"].notna().all()
    carry_rows = correlations["pearson"][correlations["pearson"]["output"] == "carry_distance_yd"]
    assert set(carry_rows["feature"]) == set(analysis.INPUT_FEATURES)


def test_aggregate_rankings_uses_median_rank_score_and_stability_labels() -> None:
    analysis = load_analysis_module()
    method_table = pd.DataFrame(
        {
            "feature": ["ball_speed_mph", "launch_angle_deg", "spin_rate_rpm"],
            "pearson": [0.9, 0.5, 0.1],
            "spearman": [0.8, 0.4, 0.2],
            "ridge_coef": [1.2, 0.3, 0.2],
            "permutation_importance": [10.0, 3.0, 1.0],
        }
    )
    stability = pd.DataFrame(
        {
            "feature": ["ball_speed_mph", "launch_angle_deg", "spin_rate_rpm"],
            "rank_interval": ["1-1", "2-2", "3-3"],
            "top3_frequency": [1.0, 1.0, 1.0],
        }
    )

    ranking = analysis.aggregate_rankings(method_table, stability)

    assert list(ranking["feature"]) == ["ball_speed_mph", "launch_angle_deg", "spin_rate_rpm"]
    assert {"pearson_score", "spearman_score", "ridge_score", "permutation_score"}.issubset(
        ranking.columns
    )
    assert ranking.loc[0, "aggregate_score"] == 1.0
    assert ranking.loc[0, "final_rank"] == 1
    assert ranking.loc[0, "stability"] == "stable_key"
