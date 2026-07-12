# q2 结果与结论

## 1. 当前状态

本问处于前期拆解阶段，尚未生成实证结果。监督预测、ODE 参数标定和轨迹图必须由脚本生成后再更新本文件。

## 2. 计划结果

| 指标 / 输出 | 单位 | 计划产物 | Claim ID |
|---|---|---|---|
| 监督模型 RMSE/MAPE | yd / % | `q2_supervised_metrics.csv` | Q2-C01 |
| ODE 参数与典型误差 | 无 / % | `q2_ode_typical_errors.csv` | Q2-C02 |
| 典型三维轨迹 | yd 或 m | `q2_typical_trajectories.png` + 同名数据 | Q2-C02 |

## 3. 复现命令

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
```
