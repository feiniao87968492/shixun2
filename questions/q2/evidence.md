# q2 证据链摘要

| Claim ID | 主张 | 证据 | 验证 | 状态 |
|---|---|---|---|---|
| Q2-C01 | 监督模型可在固定测试集预测 carry 与 apex | `q2_supervised_metrics.csv`、`q2_supervised_predictions.csv`、预测散点图、残差图 | 固定 70/30 划分，训练 CV 选模，测试集最终评估 | supported |
| Q2-C02 | 真空/阻力 ODE 的单位、落地事件和解析解校验通过 | `q2_ode_validation_checks.csv`、`q2_ode_test_metrics.csv` | 真空解析误差 < 1e-3；failure rate=0 | supported |
| Q2-C03 | 含升力 ODE 明显改善 drag-only 结构 | `q2_ode_parameters.csv`、`q2_ode_test_metrics.csv`、`q2_ode_parameter_surface.csv/png` | train-only 标定；固定测试集比较四层模型 | supported |
| Q2-C04 | 典型 100/150/200 yd 轨迹可由 ODE 接口复现 | `q2_typical_records.csv`、`q2_ode_typical_errors.csv`、`q2_typical_trajectories.csv`、三张轨迹图 | 典型记录只从测试集按实际 carry 距目标最近选择 | supported |
| Q2-C05 | 监督与 ODE 结果具备稳定性/灵敏度证据 | `q2_supervised_repeated_split.csv`、`q2_ode_sensitivity.csv/png` | 30 次重复划分；参数/积分/假设扰动 | supported |

所有 supported 主张均可由 `python questions/q2/scripts/pipeline.py --config configs/default.yaml` 重新生成，并由 `python questions/q2/scripts/validate.py --config configs/default.yaml` 检查。
