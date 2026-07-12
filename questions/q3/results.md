# q3 结果与结论

## 1. 当前状态

本问处于前期拆解阶段，尚未生成优化结果。最优参数不得手工填写，必须由 q3 流水线复现。

## 2. 计划结果

| 指标 / 输出 | 单位 | 计划产物 | Claim ID |
|---|---|---|---|
| 最优击球参数 | mph / degree / rpm | `q3_optimal_parameters.csv` | Q3-C01 |
| 最优落点距离 | yd | `q3_optimal_parameters.csv` | Q3-C01 |
| 最优三维轨迹 | yd 或 m | `q3_optimal_trajectory.png` + 同名数据 | Q3-C02 |

## 3. 复现命令

```bash
python questions/q3/scripts/pipeline.py --config configs/default.yaml
```
