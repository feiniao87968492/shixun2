# Task Plan: 实训题2建模任务推进

## Goal

Complete the full scope of `docs/plans/task4.md` for q2 final ODE remediation:
make forward-x carry the configured primary definition, run real local
optimization with trustworthy termination status, penalize integration failures,
validate the q3-compatible ODE boundary behavior, regenerate artifacts and docs,
then restore q2 to `done`, commit, push, and verify the remote SHA.

## Current Phase

Phase 16 - q2 task4 final ODE remediation

## Completed Phases

- [x] Phase 1-5: repository initialization, raw snapshot, problem decomposition, initial commit.
- [x] Phase 6-10: q1 task1 implementation, artifacts, validation, commit, push.
- [x] Phase 11: q1 review1 reproducibility audit closeout.
- [x] Phase 12: q1 review2 method audit closeout.
- [x] Phase 13: q2 first-stage stop point from `docs/plans/task2.md` section 26.
- [x] Phase 14: q2 full task2 ODE/lift continuation, committed and pushed.
- [x] Phase 15: q2 task3 recalibration and acceptance, committed and pushed.

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

## Git Safety

Before commit, ensure no raw/PDF/Excel files are staged:

```powershell
git diff --cached --name-only | Select-String -Pattern '(^|/)data/raw/problem/|\.xlsx$|\.xls$|\.pdf$'
```
