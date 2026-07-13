# Task Plan: 实训题2建模任务推进

## Goal

Complete the full scope of `docs/plans/task6.md` for q3 final remediation:
preserve the current q3 main inverse-design flow while replacing the narrow
single-surrogate robustness decision with a full supported near-optimal
candidate pool, common random number perturbations, launch-direction scenarios,
joint model-parameter robustness, independent 195/200/205 yd re-optimization,
near-optimal parameter range reporting, expanded validation, updated
docs/evidence, then commit, push, and verify the remote SHA.

## Current Phase

Phase 18 - q3 task6 final robustness remediation

## Completed Phases

- [x] Phase 1-5: repository initialization, raw snapshot, problem decomposition, initial commit.
- [x] Phase 6-10: q1 task1 implementation, artifacts, validation, commit, push.
- [x] Phase 11: q1 review1 reproducibility audit closeout.
- [x] Phase 12: q1 review2 method audit closeout.
- [x] Phase 13: q2 first-stage stop point from `docs/plans/task2.md` section 26.
- [x] Phase 14: q2 full task2 ODE/lift continuation, committed and pushed.
- [x] Phase 15: q2 task3 recalibration and acceptance, committed and pushed.
- [x] Phase 16: q2 task4 final ODE remediation, committed and pushed.
- [x] Phase 17: q3 task5 inverse-design implementation, committed and pushed.
- [x] Phase 18: q3 task6 final robustness remediation, committed and pushed.

## Phase 13: q2 task2 first stage

- [x] q2 config and manifest fixed.
- [x] Fixed and saved 70%/30% split.
- [x] Supervised models implemented: Dummy, Linear, Ridge, ExtraTrees, HistGradientBoosting.
- [x] Supervised test metrics, predictions, bootstrap CIs, grouped errors, figures, and model files generated.
- [x] Vacuum and drag-only ODE implemented with unit conversions and analytic vacuum validation.
- [x] q2 first-stage docs, evidence chain, registry, paper draft, devlog, findings, and progress updated.
- [x] Validation passed and first-stage work was committed/pushed.

## Phase 14: q2 full task2 completion

- [x] Re-read `docs/plans/task2.md` and identify remaining requirements beyond section 26.
- [x] Add RED tests in `tests/test_q2_full_task2.py`.
- [x] Extend `configs/default.yaml` for `constant_lift`, `spin_factor_lift`, `cl`, and `lift_scale`.
- [x] Implement lift-aware spin vector construction and ODE variants.
- [x] Calibrate `C_D/C_L` and `C_D/k_L` on train-only records; save a 2D parameter surface.
- [x] Evaluate `vacuum`, `drag`, `constant_lift`, and `spin_factor_lift` on the fixed test split.
- [x] Generate 100/150/200 yd typical records, errors, trajectories, and trajectory figures.
- [x] Generate supervised repeated-split stability and ODE sensitivity analysis.
- [x] Extend `validate.py` for final task2 artifacts and physical invariants.
- [x] Update q2 docs, evidence chain, figure/table registry, paper draft, devlog, findings, and progress.
- [ ] Run full validation, commit, and push.

## Phase 14 RED Result

`python -m pytest tests\test_q2_full_task2.py -q` fails for the expected missing-scope reasons:

- q2 config only lists `vacuum` and `drag`.
- `simulate_shot` does not accept `cl` or `lift_scale`.
- `q2_typical_records.csv` and trajectory/sensitivity artifacts do not exist.
- trajectory figure bundles and `q2_ode_parameters.json` do not exist.

## Key First-Stage Results

- Fixed split: train=514, test=221, random_seed=2026.
- Selected supervised model for `carry_distance_yd`: `launch_state_model / hist_gradient_boosting`, test RMSE=8.337 yd, MAPE=4.986%.
- Selected supervised model for `apex_height_yd`: `launch_state_model / hist_gradient_boosting`, test RMSE=1.739 yd, MAPE=14.335%.
- Vacuum analytic max error: 0.000456.
- ODE failure rate: 0 for vacuum and drag.
- Preliminary drag-only `C_D=0.05` is on the lower bound and must not be claimed as final `C_D/C_L`.

## Full Task2 Validation To Run Before Final Commit

- [x] `python questions\q2\scripts\pipeline.py --config configs/default.yaml`
- [x] `python questions\q2\scripts\validate.py --config configs/default.yaml`
- [x] `python -m pytest tests\test_q2_full_task2.py -q`
- [x] `python -m pytest -q`
- [x] `python scripts\check_repo.py`
- [x] `python scripts\snapshot_raw.py --verify`
- [x] `git diff --check`

## Phase 15: q2 task3 recalibration and final acceptance

- [x] Audit current q2 code, artifacts, docs, and validators against `docs/plans/task3.md`.
- [x] Add RED tests for task3 deliverables and confirm they fail for the current missing scope.
- [x] Implement separate drag/lift representative sampling and config wiring.
- [x] Add coarse-search plus bounded local optimization for drag, constant-lift, and spin-factor-lift models.
- [x] Add parameter boundary metadata and warnings, including drag boundary status.
- [x] Correct headwind/tailwind direction and extend sensitivity to both ODE role models.
- [x] Generate separate constant-lift and spin-factor typical trajectory artifact sets.
- [x] Compare forward carry and horizontal Euclidean carry definitions.
- [x] Record initial-height type and sensitivity results.
- [x] Extend q2 validation and metadata to cover task3 acceptance checks.
- [x] Sync q2 docs, root status, evidence chain, figure registry, report text, findings, and progress.
- [x] Run pipeline, validate, rerun pipeline, reproducibility checks, pytest, repo checks, raw snapshot verification, and whitespace check.
- [x] Stage with raw/PDF/Excel guard, commit task3 work, push, and verify remote SHA.

## Phase 16: q2 task4 final ODE remediation

- [x] Read `docs/plans/task4.md` and confirm scope is q2 ODE final remediation.
- [x] Temporarily downgrade q2 status to `conditionally_passed` in root/q2 docs and manifest.
- [x] Add RED tests for forward-x carry semantics, real optimizer status, failure accounting, q3 boundary checks, and POSIX metadata paths.
- [x] Implement configured `carry_definition=forward_x` through calibration, evaluation, typical errors, sensitivity, and comparison tables.
- [x] Replace short local-optimization limits with configured Powell options and true `optimizer_success/objective_finite/accepted` status.
- [x] Include integration failures in the calibration objective and emit per-model calibration failure tables.
- [x] Select q2 best-fit ODE from full-train objectives, not a hard-coded model.
- [x] Add q3-compatible spin-factor boundary stability checks and validation coverage.
- [x] Regenerate q2 artifacts, docs, evidence chain, registry, report text, findings, and progress.
- [x] Run pipeline, validate, task tests, full pytest, repo/raw/diff checks, reproducibility checks.
- [x] Restore q2 status to `done`, stage with raw/PDF/Excel guard, commit, push, and verify remote SHA.

## Phase 17: q3 task5 inverse-design implementation

- [x] Read `docs/plans/task5.md` and confirm scope is q3 robust inverse-design.
- [x] Confirm q2 task4 is complete, so q3 may include ODE crosschecks instead of stopping at supervised-only status.
- [x] Restore q3 context from README, problem statement, modeling contract, q3 docs, devlog, evidence chain, and planning files.
- [x] Add RED tests for q3 dependencies, lateral surrogate, support diagnostics, optimization, robustness, ODE crosscheck, figures, validation, docs, and metadata.
- [x] Implement q3 pipeline modules and config.
- [x] Generate q3 artifacts and figures.
- [x] Update q3/root docs, evidence chain, registry, report, findings, devlog, and progress.
- [x] Run q3 pipeline, q3 validation, task tests, full pytest, repo/raw/diff checks, reproducibility checks.
- [x] Set q3 status to `done`, stage with raw/PDF/Excel guard, commit, push, and verify remote SHA.

## Phase 17 RED/GREEN Result

- RED command: `python -m pytest tests\test_q3_task5_inverse_design.py -q`.
- RED result: 6 expected failures for missing q3 config, missing q3 artifacts, and unsynced q3 docs/status.
- GREEN commands so far:
  - `python questions\q3\scripts\pipeline.py --config configs/default.yaml`
  - `python questions\q3\scripts\validate.py --config configs/default.yaml`
  - `python -m pytest tests\test_q3_task5_inverse_design.py -q`
- Current q3 result: nominal objective=0.010 yd; robust objective=0.022 yd; robust p90 miss=3.135 yd.
- Implementation commit: `490f01dfaf2ebd2158c82701fca5b5168a6a08d0`, pushed to `origin/main` and verified by `git ls-remote`.

## Phase 18: q3 task6 final robustness remediation

- [x] Read `docs/plans/task6.md` and required q3 startup context.
- [x] Temporarily downgrade q3 status to `conditionally_passed` in root/q3 status docs and manifest.
- [x] Add RED tests in `tests/test_q3_final_robustness.py`.
- [x] Remove the hard-coded first-12 robustness candidate limit and write `q3_robust_candidate_pool.csv`.
- [x] Use common random numbers and bootstrap p90 CIs across robustness candidates.
- [x] Add launch-direction perturbation scenarios: `ideal`, `stable_player`, and `ordinary_player`.
- [x] Add full-model-input support checks and perturbation out-of-support fractions.
- [x] Add joint model-parameter robustness tables and select the final recommendation by stable-player joint p90.
- [x] Reoptimize targets 195/200/205 yd independently with LHS, at least 3 DE seeds, local refinement, and supported solution selection.
- [x] Report near-optimal parameter ranges and non-uniqueness diagnostics.
- [x] Fix DE success semantics to distinguish `scipy_success`, `objective_finite`, and `accepted`.
- [x] Extend q3 validation checks for all task6 acceptance criteria.
- [x] Regenerate q3 artifacts, figures, run metadata, and validation table.
- [x] Update q3/root docs, evidence chain, figure/table registry, report, appendix, decision/risk logs, findings, devlog, and progress.
- [x] Run q3 pipeline, q3 validation, task6 tests, task5 tests, full pytest, repo check, raw snapshot verify, diff check, and reproducibility checks.
- [x] Restore q3 status to `done`, stage with raw/PDF/Excel guard, commit, push, and verify remote SHA.

## Phase 18 RED/GREEN Result

- RED command: `python -m pytest tests\test_q3_final_robustness.py -q`.
- RED result: 5 expected failures:
  - `q3.perturbation.launch_direction_scenarios` is missing.
  - `q3_robust_candidate_pool.csv` is missing.
  - `q3_joint_robustness_summary.csv` / detail are missing.
  - `q3_target_optimization_runs.csv` is missing.
  - `q3_near_optimal_parameter_ranges.csv` and related support/validation outputs are missing.
- GREEN commands:
  - `python questions\q3\scripts\pipeline.py --config configs/default.yaml`
  - `python questions\q3\scripts\validate.py --config configs/default.yaml`
  - `python -m pytest tests\test_q3_final_robustness.py -q`
  - `python -m pytest tests\test_q3_task5_inverse_design.py -q`
  - `python -m pytest -q`
  - `python scripts\check_repo.py`
  - `python scripts\snapshot_raw.py --verify`
  - `git diff --check`
- Reproducibility: major q3 CSV hash check passed after setting q3 ExtraTrees ensemble members to `n_jobs=1`.
- Implementation commit: `42e61c7c841609146185b4f4577ab30e137477d3`, pushed to `origin/main` and verified by `git ls-remote`.

## Git Safety

Before commit, ensure no raw/PDF/Excel files are staged:

```powershell
git diff --cached --name-only | Select-String -Pattern '(^|/)data/raw/problem/|\.xlsx$|\.xls$|\.pdf$'
```
