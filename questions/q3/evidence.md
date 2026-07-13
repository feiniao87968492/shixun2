# q3 证据说明

本文档解释本小问关键主张的证据。机器可读索引仍以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q3-C01 | 在给定边界和训练支持检查下可求得 200 yd 目标的名义最优、单代理稳健解和联合模型-参数稳健推荐 | `q3_optimal_parameters.csv`、`q3_robust_candidate_pool.csv`、`q3_parameter_robustness.csv`、`q3_joint_robustness_summary.csv`、`q3_joint_robustness_detail.csv` | 20,000 点 LHS、5 seed DE、5,000 点/seed 局部采样、482 个 supported near-optimal 候选、共同随机数、3 个发射方向情景、31 项 q3 validation | 监督代理模型有模型分歧；模拟比例不是真实球员命中概率 | supported |
| Q3-C02 | 稳健推荐参数下的 ODE 轨迹可由 q2 ODE 接口复现并生成三维/侧视/俯视图表数据 | `q3_ode_crosscheck.csv`、`q3_optimal_trajectory.csv`、`q3_optimal_trajectory_3d.png`、同名 figure_data/meta | q2 ODE 参数版本记录、constant_lift 与 spin_factor_lift 积分成功、图表数据/meta 检查 | ODE 仅为交叉检查，不能写成真实实验验证 | supported |
| Q3-C03 | 横向偏移代理模型可在 q2 固定测试集上评价并用于 q3 目标函数 | `q3_lateral_model_metrics.csv`、`q3_lateral_predictions.csv`、`q3_surrogate_ensemble_metrics.csv` | 训练集 5 折 CV 选模、固定 test=221 评价、无 MAPE 主指标 | lateral 误差会直接影响优化目标 | supported |
| Q3-C04 | 195/200/205 yd 目标距离均已独立重优化而非复用 200 yd 候选池 | `q3_target_optimization_runs.csv`、`q3_target_optimal_parameters.csv` | 每个目标含 LHS baseline、至少 3 个 DE seed、local refinement，且 supported best 不劣于目标专属 LHS best | 仍是监督代理目标函数下的重优化 | supported |
| Q3-C05 | 近优解存在明显非唯一性，参数结论应报告区间而非唯一单点 | `q3_near_optimal_parameter_ranges.csv`、`q3_robust_candidate_pool.csv`、`q3_support_comparison.csv` | 482 个 supported near-optimal 参数组、256 个不同预测落点组、最大预测平台 20、完整 full-input support 检查 | 非唯一性来自当前代理模型平台，非真实击球物理定律 | supported |
