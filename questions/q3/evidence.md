# q3 证据说明

本文件解释本小问关键主张的证据。机器可读索引仍以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q3-C01 | 在给定边界和训练支持检查下可求得 200 yd 目标的名义最优与稳健推荐参数 | `q3_optimal_parameters.csv`、`q3_best_observed_baseline.csv`、`q3_sampling_baseline.csv`、`q3_optimization_runs.csv`、`q3_parameter_robustness.csv` | 20,000 点 LHS、5 seed DE、5,000 点/seed 局部采样、目标函数复算、扰动 p90 复算、16 项 q3 validation | 监督代理模型有模型分歧；稳健扰动是情景假设 | supported |
| Q3-C02 | 稳健推荐参数下的 ODE 轨迹可由 q2 ODE 接口复现并生成三维/侧视/俯视图表数据 | `q3_ode_crosscheck.csv`、`q3_optimal_trajectory.csv`、`q3_optimal_trajectory_3d.png`、同名 figure_data/meta | q2 ODE 参数版本记录、constant_lift 与 spin_factor_lift 积分成功、图表数据/meta 检查 | ODE 仅为交叉检查，不能写成真实实验验证 | supported |
| Q3-C03 | 横向偏移代理模型可在 q2 固定测试集上评价并用于 q3 目标函数 | `q3_lateral_model_metrics.csv`、`q3_lateral_predictions.csv`、`q3_surrogate_ensemble_metrics.csv` | 训练集 5 折 CV 选模、固定 test=221 评价、无 MAPE 主指标 | lateral 误差会直接影响优化目标 | supported |
