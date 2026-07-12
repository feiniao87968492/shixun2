# q1 结果与结论

## 1. 当前状态

本问处于前期拆解阶段，尚未生成实证结果。后续所有结论必须由 `docs/evidence_chain.csv` 中的 `supported` 记录支撑。

## 2. 计划结果

| 指标 / 输出 | 单位 | 计划产物 | Claim ID |
|---|---|---|---|
| 输入输出相关性矩阵 | 无 | `q1_correlation_matrix.csv` | Q1-C01 |
| 飞行距离影响因素排序 | 无 | `q1_feature_importance.csv` | Q1-C01 |
| 缺失与异常审计 | 无 | `q1_missing_audit.csv` | Q1-C02 |

## 3. 复现命令

```bash
python questions/q1/scripts/pipeline.py --config configs/default.yaml
```
