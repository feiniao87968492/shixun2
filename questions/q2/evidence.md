# q2 证据说明

机器可读索引以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q2-C01 | 监督模型可预测飞行距离和最高点高度，并在固定测试集报告误差 | `q2_supervised_metrics.csv`、`q2_supervised_predictions.csv`、预测散点图、残差图 | 固定 70/30 测试集，训练集 5 折 CV 选模，Dummy/线性/Ridge/ExtraTrees/HistGradientBoosting 对照 | 仍是单次主划分；重复划分稳定性待后续补充 | supported |
| Q2-C02 | 第一阶段真空和仅阻力 ODE 通过单位换算、落地事件和真空解析解校验 | `q2_ode_validation_checks.csv`、`q2_ode_test_metrics.csv`、`q2_ode_parameters.csv` | 真空解析解最大差异 0.000456；221 条测试样本 failure rate 为 0 | drag-only 尚未优于 vacuum，`C_D=0.05` 位于下界，不是最终标定 | supported_first_stage |
| Q2-C03 | 标定后的含升力三维 ODE 可生成 100/150/200 yd 典型轨迹并解释误差来源 | 待生成 `q2_typical_trajectories*` 与 `q2_ode_typical_errors.csv` | 待完成升力模型、参数可识别性和灵敏度分析 | 尚未完成，不得用于论文最终结论 | planned |
