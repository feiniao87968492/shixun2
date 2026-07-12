# Task Plan: 实训题2 建模任务推进

## Goal

完成 `docs/plans/task2.md` 第 26 节定义的第二问第一阶段停止点，并在验证通过后提交、推送到 `origin/main`。

## Current Phase

Phase 13 - q2 first-stage closeout

## Completed Phases

- [x] Phase 1-5: repository initialization, raw snapshot, problem decomposition, initial commit.
- [x] Phase 6-10: q1 task1 implementation, artifacts, validation, commit, push.
- [x] Phase 11: q1 review1 reproducibility audit closeout.
- [x] Phase 12: q1 review2 method audit closeout.

## Phase 13: q2 task2 first stage

- [x] Read `docs/plans/task2.md` and identify first-stage stop point.
- [x] Confirm local raw files and physical constants source.
- [x] Add RED tests in `tests/test_q2_first_stage.py`.
- [x] Fix `configs/default.yaml` q2 block and `questions/q2/manifest.yaml`.
- [x] Implement fixed 70%/30% split and save `q2_data_split.csv`.
- [x] Implement supervised models: Dummy, Linear, Ridge, ExtraTrees, HistGradientBoosting.
- [x] Generate supervised test metrics, predictions, bootstrap CIs, grouped errors, figures, and model files.
- [x] Implement vacuum and drag-only ODE with unit conversions and analytic vacuum validation.
- [x] Generate q2 first-stage artifacts and run metadata.
- [x] Update q2 docs, evidence chain, figure/table registry, README, paper draft, devlog, findings, and progress.
- [x] Run q2 pipeline and targeted q2 validation.
- [x] Run full repository validation.
- [x] Commit and push q2 first-stage work.

## Key Results

- Fixed split: train=514, test=221, random_seed=2026.
- Selected supervised model for `carry_distance_yd`: `launch_state_model / hist_gradient_boosting`, test RMSE=8.337 yd, MAPE=4.986%.
- Selected supervised model for `apex_height_yd`: `launch_state_model / hist_gradient_boosting`, test RMSE=1.739 yd, MAPE=14.335%.
- Vacuum analytic max error: 0.000456.
- ODE failure rate: 0 for vacuum and drag.
- Preliminary drag-only `C_D=0.05` is on the lower bound and must not be claimed as final `C_D/C_L`.

## Validation To Run Before Commit

- [x] `python questions\q2\scripts\pipeline.py --config configs/default.yaml`
- [x] `python questions\q2\scripts\validate.py --config configs/default.yaml`
- [x] `python -m pytest tests\test_q2_first_stage.py -q`
- [x] `python -m pytest -q`
- [x] `python scripts\check_repo.py`
- [x] `python scripts\snapshot_raw.py --verify`
- [x] `git diff --check`

## Git Safety

Before commit, ensure no raw/PDF/Excel files are staged:

```powershell
git diff --cached --name-only | Select-String -Pattern '(^|/)data/raw/problem/|\.xlsx$|\.xls$|\.pdf$'
```
