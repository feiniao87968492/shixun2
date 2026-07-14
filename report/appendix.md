# 附录

## 关键推导

待填写。

## 算法伪代码

待填写。

## 补充图表

- q3 最优轨迹三维图：`questions/q3/artifacts/figures/q3_optimal_trajectory_3d.png`
- q3 最优轨迹侧视图：`questions/q3/artifacts/figures/q3_optimal_trajectory_side.png`
- q3 最优轨迹俯视图：`questions/q3/artifacts/figures/q3_optimal_trajectory_top.png`
- q3 速度-发射角目标函数切片：`questions/q3/artifacts/figures/q3_objective_slice_speed_angle.png`
- q3 自旋速率-自旋轴目标函数切片：`questions/q3/artifacts/figures/q3_objective_slice_spin.png`

## 代码与数据说明

第三问正式入口：

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
python questions/q2/scripts/validate.py --config configs/default.yaml
python questions/q3/scripts/pipeline.py --config configs/default.yaml
python questions/q3/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_q3_integration.py -q
```

核心结果表：

- `questions/q3/artifacts/tables/q3_dependency_audit.csv`
- `questions/q3/artifacts/tables/q3_lateral_model_metrics.csv`
- `questions/q3/artifacts/tables/q3_best_observed_baseline.csv`
- `questions/q3/artifacts/tables/q3_sampling_baseline.csv`
- `questions/q3/artifacts/tables/q3_optimization_runs.csv`
- `questions/q3/artifacts/tables/q3_optimal_parameters.csv`
- `questions/q3/artifacts/tables/q3_parameter_robustness.csv`
- `questions/q3/artifacts/tables/q3_robust_candidate_pool.csv`
- `questions/q3/artifacts/tables/q3_single_surrogate_parameter_robustness.csv`
- `questions/q3/artifacts/tables/q3_joint_robustness_summary.csv`
- `questions/q3/artifacts/tables/q3_joint_robustness_detail.csv`
- `questions/q3/artifacts/tables/q3_support_comparison.csv`
- `questions/q3/artifacts/tables/q3_near_optimal_parameter_ranges.csv`
- `questions/q3/artifacts/tables/q3_target_optimization_runs.csv`
- `questions/q3/artifacts/tables/q3_target_optimal_parameters.csv`
- `questions/q3/artifacts/tables/q3_model_crosscheck.csv`
- `questions/q3/artifacts/tables/q3_target_distance_sensitivity.csv`
- `questions/q3/artifacts/tables/q3_ode_crosscheck.csv`
- `questions/q3/artifacts/tables/q3_validation_checks.csv`
- `docs/reproducibility/q2_q3_release_manifest.json`
