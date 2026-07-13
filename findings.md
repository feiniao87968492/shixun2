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

## Q2 Task3 Recalibration Scope

- `docs/plans/task3.md` is the current authoritative plan.
- The task is q2整改/重标定/最终验收, not q3 implementation.
- Existing task2 artifacts are insufficient for task3 because they still use a shared representative table, grid-only ODE calibration, one typical trajectory set, reversed wind direction semantics in sensitivity, incomplete carry-definition comparison, and incomplete run metadata.
- Completion requires regenerated ODE artifacts, expanded validation coverage, synchronized q2/root status docs, repeated-run reproducibility evidence, commit, push, and remote SHA verification.

## Q2 Task3 Results

- Drag calibration now uses `ode.drag_calibration`: 36 representative records and 10 coarse-grid points.
- Lift calibration now uses `ode.lift_calibration`: 24 representative records and 6x6 coarse-grid points.
- Representative records are selected by multidimensional KMeans coverage over ball speed, launch angle, spin rate, and carry distance.
- ODE parameter calibration uses coarse search plus bounded `scipy.optimize.minimize` local optimization; selected runs record full-train objectives.
- Recalibrated parameters:
  - drag: `C_D=0.05`, `boundary_solution`.
  - constant_lift: `C_D=0.27, C_L=0.18`.
  - spin_factor_lift: `C_D=0.49, k_L=1.6`.
- ODE test carry RMSE:
  - vacuum=32.233 yd.
  - drag=36.465 yd.
  - constant_lift=16.506 yd.
  - spin_factor_lift=31.996 yd.
- Model roles are explicit:
  - `best_fit_ode_model=constant_lift`.
  - `q3_compatible_ode_model=spin_factor_lift`.
- Carry definition comparison supports adopting forward distance `D_x=x_land`.
- Wind sensitivity now uses `tailwind_1mps=(1,0,0)` and `headwind_1mps=(-1,0,0)`; average carry satisfies tailwind > no_wind > headwind for both role models.
- `run_metadata.json` now records git commit, data/config hashes, package versions, split hashes, calibration ids, model roles, and optimization run paths.
- Repeated pipeline run matched major CSV SHA256 hashes.

## Q2 Task4 Scope

- `docs/plans/task4.md` is the current authoritative plan.
- The task remains limited to q2 ODE final remediation.
- Required changes beyond task3:
  - Add configured primary carry definition `q2.ode.carry_definition=forward_x`.
  - Use forward-x carry consistently in calibration objectives, ODE metrics, typical errors, sensitivity, and comparison tables.
  - Replace `maxiter=1/maxfev=4` local optimization with configured Powell options and true optimizer termination status.
  - Distinguish `optimizer_success`, `objective_finite`, and `accepted`; selected runs must have zero calibration/full-train failures.
  - Penalize or reject integration failures instead of silently dropping failed samples.
  - Emit per-model calibration failure sample tables.
  - Determine q2 best-fit ODE from valid full-train objectives; q3-compatible model remains `spin_factor_lift` only if boundary stability checks pass.
  - Add validation checks for optimizer termination, forward-x carry consistency, zero failures, q3 boundary stability, and POSIX metadata paths.

## Q3 Task5 Scope

- `docs/plans/task5.md` is the current authoritative plan.
- The task is q3 robust inverse-design for a 200 yd target, using the final q2 carry/apex models and q2 ODE parameters.
- q3 scripts are currently scaffolds, and q3 manifest still references stale q2 dependency paths.
- q2 task4 is complete: q2 status is `done`, q2 carry definition is `forward_x`, q2 best-fit ODE is `constant_lift`, q3-compatible ODE is `spin_factor_lift`, and q3 boundary stability checks pass.
- Because q2 ODE remediation is complete, q3 should include ODE crosschecks and optimal trajectory figures rather than stopping at supervised-only status.
- q3 must preserve the q2 fixed split: train=514, test=221. Lateral model training, support thresholds, best-observed baseline, and optimizer support diagnostics must use train-only data.
- Processed data stores apex as `max_height_yd`; q2 loaders create the `apex_height_yd` alias. q3 should follow that convention instead of assuming the raw alias exists.
- Required output families include dependency audit, lateral model metrics/predictions, support tables, observed/sampling/DE optimization tables, nominal and robust optimum rows, parameter robustness, model crosscheck, target-distance sensitivity, ODE crosscheck, optimal trajectory, validation checks, run metadata, and paper-level figures with source CSV/meta.

## Q3 Task5 Results

- q3 dependency audit passes all 13 checks: q2 carry/apex models load, q2 split is train=514/test=221/no overlap, q2 validation has no blocking failures, q2 ODE parameters are valid, input has 735 complete key records, and q2 carry feature order matches q3 feature order.
- Lateral model selection: `hist_gradient_boosting` selected by train 5-fold CV RMSE; fixed-test RMSE=5.475 yd, MAE=3.870 yd, R2=0.958, bias=0.939 yd.
- Best observed train baseline: `record_id=609`, observed carry=198.403 yd, lateral=-5.107 yd, objective=5.351 yd.
- Nominal optimum: ball_speed=121.113 mph, launch_angle=19.616 deg, spin_rate=2627.708 rpm, spin_axis=-0.366 deg, predicted carry=199.992 yd, lateral=-0.007 yd, objective=0.010 yd, support=supported.
- Robust recommended optimum: ball_speed=120.751 mph, launch_angle=19.482 deg, spin_rate=2348.781 rpm, spin_axis=0.450 deg, predicted carry=200.006 yd, lateral=-0.021 yd, objective=0.022 yd, support=supported, perturbation p90=3.135 yd.
- Five DE runs completed with finite accepted outputs; vectorized population scoring avoids scalar sklearn prediction timeouts.
- Model crosscheck classifies both nominal and robust candidates as `highly_model_sensitive`; this is a required q3 limitation.
- ODE crosscheck integrates successfully for `constant_lift` and `spin_factor_lift`. For robust recommendation, constant_lift predicts D_x=193.187 yd and spin_factor_lift predicts D_x=195.032 yd, so ODE is crosscheck evidence only.

## Q3 Task6 Scope

- `docs/plans/task6.md` is the current authoritative plan.
- The task is final q3 remediation, not a replacement of the existing inverse-design flow.
- q3 must remain on the q2 fixed split: train=514, test=221. Do not reshuffle data, change q2 carry/apex models, change q3 lateral split evaluation, relax hard search bounds, change the 200 yd target function, shrink the 20,000 LHS baseline, remove the five DE seeds, replace the kNN support framework, or alter the q2 ODE interface.
- q3 is temporarily downgraded to `conditionally_passed` until the new robustness and validation evidence passes.
- Current task5 limitations to fix:
  - robustness candidate selection is hard-coded to the top 12 supported near-optimal candidates;
  - perturbations do not use common random numbers across candidates;
  - launch direction is fixed and absent from perturbation scenarios;
  - final robust recommendation is based on single-surrogate parameter noise instead of joint model-parameter uncertainty;
  - 195/205 yd sensitivity rescored the original 200 yd pool instead of independently reoptimizing;
  - parameter conclusions are too point-estimate precise for a plateaued surrogate;
  - support diagnostics use decision-space support only, not full five-feature model input support;
  - q3 validation does not cover the above acceptance criteria.

## Q3 Task6 Results

- Task6 retains the q2 fixed split train=514/test=221, q2 carry/apex models, q3 lateral fixed-test evaluation, hard search bounds, 20,000 point LHS baseline, five DE seeds, kNN support framework, and q2 ODE interface.
- Robust candidate selection now covers all 482 supported near-optimal candidates because the supported near-optimal set is below the 500-candidate full-computation threshold.
- Parameter robustness uses common random numbers and three launch-direction scenarios:
  - `ideal`: launch direction sd=0.0 deg.
  - `stable_player`: launch direction sd=0.5 deg.
  - `ordinary_player`: launch direction sd=1.0 deg.
- Single-surrogate robust optimum: ball_speed=120.868 mph, launch_angle=18.978 deg, spin_rate=2344.294 rpm, spin_axis=0.118 deg, objective=0.156 yd, stable_player single-surrogate p90=4.932 yd.
- Final joint robust recommendation: ball_speed=122.958 mph, launch_angle=20.437 deg, spin_rate=2720.784 rpm, spin_axis=-1.255 deg, objective=0.204 yd, stable_player joint p90=7.133 yd, p95=8.332 yd, within-5-yd simulated proportion=0.724.
- The within-3/5 yd values are simulated proportions under the configured parameter error distribution, launch-direction scenario, and surrogate ensemble; they are not true golfer hit probabilities.
- Target-distance reoptimization produced supported best solutions for:
  - 195 yd: objective=0.011 yd, predicted carry=194.990 yd.
  - 200 yd: objective=0.010 yd, predicted carry=199.992 yd.
  - 205 yd: objective=0.016 yd, predicted carry=205.005 yd.
- Near-optimal non-uniqueness diagnostics: 482 supported near-optimal parameter sets, 256 distinct predicted landing pairs, largest prediction plateau size 20.
- Full-input support comparison reports the final joint robust recommendation as supported in both decision-space and full model-input support, with out_of_support_fraction=0.

## Q2 Task4 Performance Debugging

- A full pipeline run with true Powell optimization timed out after 40 minutes.
- Objective timing:
  - drag representative objective: about 0.8 s for 36 records.
  - constant-lift objective at calibration `max_step=0.05`: about 2.5 s for 24 records.
  - spin-factor objective at calibration `max_step=0.05`: about 3.5 s for 24 records.
- Powell timing at calibration `max_step=0.15`:
  - constant-lift single start: success, 95 function evaluations, about 99 s.
  - spin-factor single start: success, 111 function evaluations, about 120 s.
- Decision: use `solver_max_step=0.15` only for calibration-time local search, while fixed test evaluation and validation still use the configured formal ODE solver.

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
