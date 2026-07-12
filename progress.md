# Progress Log

## Session: 2026-07-12 - repository initialization

- Initialized the modeling repository structure.
- Archived raw files locally under `data/raw/problem/` and generated `data/raw_manifest.csv`.
- Completed problem decomposition and q1-q3 scaffolding.
- Initial repository checks and raw snapshot verification passed.

## Session: 2026-07-12 - q1 task1 and reviews

- Implemented q1 data audit, correlation analysis, model-based importance, sensitivity analysis, figures, and evidence records.
- Closed q1 review1 reproducibility gaps.
- Closed q1 review2 method-audit gaps.
- Latest q1 state is committed and pushed at `13ebeb8 fix(q1): address review2 method audit`.

## Session: 2026-07-12 - q2 first-stage RED tests

- Read `docs/plans/task2.md` and confirmed the first-stage stop point.
- Confirmed local raw files exist and remain untracked.
- Verified physical constants from raw OCR/docs:
  - mass=0.0456 kg
  - diameter=0.04267 m
  - gravity=9.80665 m/s^2
  - air density=1.225 kg/m^3
- Added `tests/test_q2_first_stage.py`.
- RED result: `python -m pytest tests\test_q2_first_stage.py -q` failed as expected because q2 config, split artifacts, supervised artifacts, and ODE modules were missing.

## Session: 2026-07-12 - q2 first-stage implementation

- Added q2 config and fixed manifest upstream artifacts.
- Implemented:
  - `questions/q2/scripts/preprocessing.py`
  - `questions/q2/scripts/supervised.py`
  - `questions/q2/scripts/ode_model.py`
  - q2 `pipeline.py`, `validate.py`, and `visualize.py`
- Added q2 loading-layer alias: `max_height_yd` -> `apex_height_yd`.
- Ran `python questions\q2\scripts\pipeline.py --config configs/default.yaml`.
- Pipeline result:
  - train_n=514
  - test_n=221
  - selected models: `apex_height_yd:launch_state_model/hist_gradient_boosting`; `carry_distance_yd:launch_state_model/hist_gradient_boosting`
  - preliminary_drag_cd=0.05
- Ran `python -m pytest tests\test_q2_first_stage.py -q`: 4 passed.
- Ran `python questions\q2\scripts\validate.py --config configs/default.yaml`: 45 checks passed.
- Updated q2 docs, evidence chain, figure/table registry, README, paper draft, devlog, task plan, findings, and progress.

## Commit and Push

- Staged only allowed files; raw/PDF/Excel guard produced no matches.
- Created commit `faaf93d feat(q2): add first-stage supervised and ode baseline`.
- HTTPS push failed because command-line TCP to `github.com:443` was reset, while GitHub API/SSH were reachable.
- Pushed successfully through one-time SSH URL: `git@github.com:feiniao87968492/shixun2.git`.
- Synced `refs/remotes/origin/main` to `faaf93d`.

## Final Verification Before Commit

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| q2 pipeline | `python questions\q2\scripts\pipeline.py --config configs/default.yaml` | Regenerate q2 first-stage artifacts | Passed; train=514 test=221 | pass |
| q2 validation | `python questions\q2\scripts\validate.py --config configs/default.yaml` | q2 checks pass | 45 checks passed | pass |
| full pytest | `python -m pytest -q` | all tests pass | 23 passed | pass |
| repo check | `python scripts\check_repo.py` | no errors | passed with expected q3 scaffold warning | pass |
| raw verify | `python scripts\snapshot_raw.py --verify` | raw hashes match | verified 3 raw files | pass |
| whitespace check | `git diff --check` | no output | no output | pass |

## Session: 2026-07-12 - q2 full task2 continuation

- Re-read `docs/plans/task2.md`; section 26 first-stage is already complete, but full task2 still requires lift ODEs, train-only parameter calibration, typical trajectory analysis, sensitivity analysis, validation, and documentation.
- Added `tests/test_q2_full_task2.py` before production changes.
- RED command: `python -m pytest tests\test_q2_full_task2.py -q`.
- RED result: 4 failures for expected missing behavior/artifacts:
  - q2 config lacks `constant_lift`, `spin_factor_lift`, `cl`, and `lift_scale`.
  - `simulate_shot` lacks `cl` and `lift_scale` parameters.
  - final typical record, trajectory, sensitivity, and repeated-split tables are missing.
  - trajectory figure bundles and `q2_ode_parameters.json` are missing.
- Rewrote `task_plan.md` and `findings.md` to reflect full task2 scope instead of the old first-stage-only objective.

## Session: 2026-07-12 - q2 full task2 implementation

- Extended q2 config to include `constant_lift`, `spin_factor_lift`, `cl`, and `lift_scale`.
- Implemented spin-vector construction, constant-lift ODE, spin-factor-lift ODE, train-only representative grid calibration, four-model test evaluation, typical-record errors/trajectories, ODE sensitivity, and supervised repeated-split stability.
- Generated final q2 artifacts through:
  - `python questions\q2\scripts\pipeline.py --config configs/default.yaml`
- Key outputs:
  - ODE parameters: drag `C_D=0.05`; constant_lift `C_D=0.27,C_L=0.18`; spin_factor_lift `C_D=0.27,k_L=0.8`.
  - ODE carry RMSE: vacuum=32.233 yd; drag=36.465 yd; constant_lift=16.506 yd; spin_factor_lift=29.001 yd.
  - Typical records: 100 yd -> sample_id 683; 150 yd -> 713; 200 yd -> 623.
- Validation and tests:
  - `python questions\q2\scripts\validate.py --config configs/default.yaml`: 69 checks passed.
  - `python -m pytest tests\test_q2_full_task2.py -q`: 4 passed.
  - Initial full pytest failed because old first-stage tests assumed only `preliminary_drag_only` and only two ODE failure rows.
  - Root cause: stale test assumptions after expanding task2 to full ODE hierarchy.
  - Fixed `tests/test_q2_first_stage.py` to accept full task2 calibrated state while preserving first-stage invariants.
  - `python -m pytest -q`: 27 passed.
- Updated q2 docs, manifest, evidence summary, global evidence chain, figure/table registry, paper draft, devlog, task plan, and progress.

## Session: 2026-07-12 - q2 final validation

- Final validation after documentation sync:
  - `python questions\q2\scripts\validate.py --config configs/default.yaml`: 69 checks passed.
  - `python -m pytest -q`: 27 passed.
  - `python scripts\check_repo.py`: passed with 1 expected q3 scaffold warning.
  - `python scripts\snapshot_raw.py --verify`: verified 3 raw files.
  - `git diff --check`: no output.
