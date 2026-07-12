# Findings & Decisions

## Repository Context

- Current repo: `D:\Users\zty\数学建模\赛题集\实训2`
- Remote: `https://github.com/feiniao87968492/shixun2`
- Branch: `main`
- Raw files are local under `data/raw/problem/` and must not be committed.

## Q1 Findings

- q1 is complete through review2.
- Final q1 interpretation is based on `questions/q1/artifacts/tables/q1_feature_summary.csv`.
- Key conclusions:
  - `ball_speed_mph` is the most stable key factor for carry distance.
  - `club_speed_mph` has marginal association but overlaps strongly with ball speed.
  - `launch_angle_deg` has structural nonlinear contribution.
  - `attack_angle_deg` is not a stable key factor.

## Q2 First-Stage Requirements

`docs/plans/task2.md` section 26 requires this round to stop after:

1. q2 config and manifest fixes.
2. Fixed 70%/30% split.
3. Dummy, linear, Ridge, ExtraTrees, HistGradientBoosting.
4. Supervised test metrics.
5. Vacuum and drag-only ODE.
6. Unit conversions and analytic validation.
7. No final `C_D,C_L` claim.

## Q2 First-Stage Results

- Fixed split saved in `questions/q2/artifacts/tables/q2_data_split.csv`:
  - train=514
  - test=221
  - random_seed=2026
- Supervised model candidates covered:
  - Dummy
  - Linear
  - Ridge
  - ExtraTrees
  - HistGradientBoosting
- Feature sets:
  - `launch_state_model`
  - `full_shot_model`
- Selected models by training CV RMSE:
  - `carry_distance_yd`: `launch_state_model / hist_gradient_boosting`
  - `apex_height_yd`: `launch_state_model / hist_gradient_boosting`
- Test metrics:
  - carry RMSE=8.337 yd, MAPE=4.986%, MAE=5.248 yd, R2=0.947
  - apex RMSE=1.739 yd, MAPE=14.335%, MAE=1.253 yd, R2=0.948

## Q2 ODE Findings

- Physical constants:
  - mass=0.0456 kg
  - diameter=0.04267 m
  - radius=0.021335 m
  - air density=1.225 kg/m^3
  - gravity=9.80665 m/s^2
- Unit conversion checks passed:
  - 1 mph = 0.44704 m/s
  - 60 rpm = 2*pi rad/s
  - 1 yd = 0.9144 m
- Vacuum numeric vs analytic max error: 0.000456.
- ODE test metrics:
  - vacuum carry RMSE=32.233 yd; apex RMSE=7.196 yd; failure rate=0
  - drag carry RMSE=36.465 yd; apex RMSE=7.591 yd; failure rate=0
- `C_D=0.05` is only a `preliminary_drag_only` boundary result and must not be claimed as final `C_D/C_L`.

## Decisions

| Decision | Rationale |
|---|---|
| Use q2 loading-layer alias `max_height_yd -> apex_height_yd` | Keeps q1 artifact unchanged while matching task2 terminology. |
| Select supervised models by training CV RMSE only | Prevents test-set leakage. |
| Save all q2 figures with same-stem CSV and meta.json | Maintains repository visualization contract. |
| Stop before lift and final parameter calibration | Required by task2 section 26. |
