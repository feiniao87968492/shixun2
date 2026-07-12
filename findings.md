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
- Selected models by training CV RMSE:
  - `carry_distance_yd`: `launch_state_model / hist_gradient_boosting`
  - `apex_height_yd`: `launch_state_model / hist_gradient_boosting`
- Test metrics:
  - carry RMSE=8.337 yd, MAPE=4.986%, MAE=5.248 yd, R2=0.947
  - apex RMSE=1.739 yd, MAPE=14.335%, MAE=1.253 yd, R2=0.948

## Q2 ODE First-Stage Findings

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
- ODE first-stage test metrics:
  - vacuum carry RMSE=32.233 yd; apex RMSE=7.196 yd; failure rate=0
  - drag carry RMSE=36.465 yd; apex RMSE=7.591 yd; failure rate=0
- `C_D=0.05` is only a `preliminary_drag_only` boundary result and must not be claimed as final `C_D/C_L`.

## Q2 Full Task2 Results

- Added ODE-2 `constant_lift` and ODE-3 `spin_factor_lift`.
- Spin vectors are built from `spin_rate_rpm` and `spin_axis_deg`; `positive_backspin_lifts_up` and `zero_sidespin_zero_direction_lateral_near_zero` pass in `q2_ode_validation_checks.csv`.
- ODE calibration uses train split representative records only; fixed test split is excluded from calibration.
- ODE parameters:
  - drag: `C_D=0.05` (boundary baseline).
  - constant_lift: `C_D=0.27, C_L=0.18`.
  - spin_factor_lift: `C_D=0.27, k_L=0.8`.
- ODE test carry RMSE:
  - vacuum=32.233 yd.
  - drag=36.465 yd.
  - constant_lift=16.506 yd.
  - spin_factor_lift=29.001 yd.
- Typical records selected from fixed test split by nearest actual carry:
  - 100 yd: sample_id 683, actual carry=99.825 yd.
  - 150 yd: sample_id 713, actual carry=150.219 yd.
  - 200 yd: sample_id 623, actual carry=200.273 yd.
- Generated final artifacts:
  - `q2_ode_parameter_surface.csv/png`
  - `q2_typical_records.csv`
  - `q2_ode_typical_errors.csv`
  - `q2_typical_trajectories.csv`
  - `q2_typical_trajectories_3d/side/top.png`
  - `q2_ode_sensitivity.csv/png`
  - `q2_supervised_repeated_split.csv`
- q2 validation passes 69 checks; full pytest passes 27 tests.

## Phase 14 RED Evidence

`python -m pytest tests\test_q2_full_task2.py -q` failed as expected:

- q2 config is missing `constant_lift`, `spin_factor_lift`, `cl`, and `lift_scale`.
- `simulate_shot` is missing `cl` and `lift_scale` arguments.
- `q2_typical_records.csv`, `q2_ode_typical_errors.csv`, `q2_typical_trajectories.csv`, `q2_ode_sensitivity.csv`, and `q2_supervised_repeated_split.csv` are absent.
- trajectory figure bundles and `q2_ode_parameters.json` are absent.

## Decisions

| Decision | Rationale |
|---|---|
| Use q2 loading-layer alias `max_height_yd -> apex_height_yd` | Keeps q1 artifact unchanged while matching task2 terminology. |
| Select supervised models by training CV RMSE only | Prevents test-set leakage. |
| Save all q2 figures with same-stem CSV and meta.json | Maintains repository visualization contract. |
| Continue from first-stage baseline instead of rewriting q2 | Existing split, supervised modeling, unit conversions, and vacuum/drag checks are valid foundations for the full task2 scope. |
