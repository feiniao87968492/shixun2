from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "questions" / "q1" / "scripts"
TABLES = ROOT / "questions" / "q1" / "artifacts" / "tables"


def load_analysis_module():
    spec = importlib.util.spec_from_file_location("q1_analysis_review2", SCRIPTS / "analysis.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_s3_sensitivity_reports_actual_ranked_sample_size() -> None:
    sensitivity = pd.read_csv(TABLES / "q1_sensitivity_comparison.csv")
    assert {"n", "ranked_n", "analysis_type"}.issubset(sensitivity.columns)

    s3 = sensitivity.loc[sensitivity["scenario"] == "S3_imputed"].iloc[0]
    assert int(s3["ranked_n"]) == int(s3["n"]) == 735
    assert s3["analysis_type"] == "descriptive_imputed_marginal"


def test_speed_overlap_models_use_same_sample_and_paired_cv_folds() -> None:
    summary = pd.read_csv(TABLES / "q1_speed_overlap_models.csv")
    folds = pd.read_csv(TABLES / "q1_speed_overlap_fold_scores.csv")

    assert summary["n"].nunique() == 1
    assert int(summary["n"].iloc[0]) == 669
    assert {"fold_count", "paired_delta_rmse_vs_ball_speed"}.issubset(summary.columns)
    assert set(summary["fold_count"]) == {25}

    fold_counts = folds.groupby("fold")["model"].nunique()
    assert fold_counts.nunique() == 1
    assert int(fold_counts.iloc[0]) == 3


def test_group_importance_uses_repeated_cv_and_block_permutation() -> None:
    groups = pd.read_csv(TABLES / "q1_group_importance.csv")

    required = {"importance_std", "positive_frequency", "fold_count", "permutation_repeats", "block_permutation"}
    assert required.issubset(groups.columns)
    assert groups["fold_count"].min() >= 25
    assert (groups["importance_std"] > 0).all()
    assert groups["positive_frequency"].between(0, 1).all()
    assert groups["block_permutation"].astype(bool).all()


def test_rank_stability_is_explicitly_marginal_only() -> None:
    stability = pd.read_csv(TABLES / "q1_rank_stability.csv")
    summary = pd.read_csv(TABLES / "q1_feature_summary.csv")

    expected = {
        "marginal_rank_interval",
        "marginal_top3_frequency",
        "marginal_top5_frequency",
        "stability_scope",
    }
    assert expected.issubset(stability.columns)
    assert expected.issubset(summary.columns)
    assert set(stability["stability_scope"]) == {"marginal_correlation_bootstrap"}
    assert "rank_interval" not in summary.columns
    assert "top3_frequency" not in summary.columns


def test_ridge_coefficients_are_repeated_estimates_not_single_fit_std_zero() -> None:
    ridge = pd.read_csv(TABLES / "q1_ridge_coefficients.csv")

    required = {"ridge_coef_std", "ridge_fold_count", "positive_frequency", "negative_frequency"}
    assert required.issubset(ridge.columns)
    assert ridge["ridge_fold_count"].min() >= 25
    assert (ridge["ridge_coef_std"] > 0).any()


def test_legacy_equal_weight_ranking_is_marked_not_for_final_conclusion() -> None:
    ranking = pd.read_csv(TABLES / "q1_feature_ranking.csv")

    assert {"deprecated", "not_for_final_conclusion"}.issubset(ranking.columns)
    assert ranking["deprecated"].astype(bool).all()
    assert ranking["not_for_final_conclusion"].astype(bool).all()


def test_outlier_audit_splits_missing_and_quantile_removal_reasons() -> None:
    outliers = pd.read_csv(TABLES / "q1_outlier_audit.csv")
    required = {"missing_removed_n", "quantile_removed_n", "both_removed_n"}

    assert required.issubset(outliers.columns)
    joint = outliers.loc[outliers["scenario"] == "D_joint_trim_1pct"].iloc[0]
    assert int(joint["removed_n"]) == (
        int(joint["missing_removed_n"]) + int(joint["quantile_removed_n"]) + int(joint["both_removed_n"])
    )


def test_validate_outputs_checks_review2_method_invariants() -> None:
    analysis = load_analysis_module()
    checks = analysis.validate_outputs(ROOT)
    expected_checks = {
        "s3_sensitivity_ranked_n_matches_reported_n",
        "speed_overlap_same_sample",
        "speed_overlap_paired_folds",
        "group_importance_repeated_cv",
        "group_importance_block_permutation",
        "rank_stability_marginal_scope",
        "ridge_coefficients_repeated_estimates",
        "legacy_ranking_deprecated",
    }
    assert expected_checks.issubset(set(checks["check"]))
    assert checks.loc[checks["check"].isin(expected_checks), "passed"].all()


def test_pipeline_summary_names_final_and_stable_feature_sets() -> None:
    pipeline_source = (SCRIPTS / "pipeline.py").read_text(encoding="utf-8")
    run_summary = json.loads((TABLES / "q1_run_summary.json").read_text(encoding="utf-8"))

    assert "top_features=" not in pipeline_source
    assert "summary_order_features" in run_summary
    assert run_summary["stable_key_features"] == ["ball_speed_mph"]
    assert "top_features" not in run_summary
