# q2 结果与结论

## 1. 当前状态

第二问已完成 `docs/plans/task2.md` 第 26 节定义的第一阶段停止点：固定 70%/30% 划分、监督预测基线与候选模型、真空/仅阻力 ODE、单位换算和真空解析解校验。当前结果不得解释为最终空气动力参数标定；升力项、最终 `C_D/C_L`、100/150/200 yd 典型轨迹和灵敏度分析仍未完成。

## 2. 数据划分

使用 `random_seed=2026` 对 `data/processed/golf_shots_clean.csv` 建立固定主划分：

| split | 样本数 | 产物 |
|---|---:|---|
| train | 514 | `questions/q2/artifacts/tables/q2_data_split.csv` |
| test | 221 | `questions/q2/artifacts/tables/q2_data_split.csv` |

监督模型和 ODE 第一阶段评估均使用同一个测试集；模型选择只使用训练集 5 折交叉验证，测试集只用于最终报告指标。

## 3. 监督预测模型

候选模型包括 `DummyRegressor`、线性回归、RidgeCV、ExtraTrees 和 HistGradientBoosting。每个目标分别比较 `launch_state_model` 和 `full_shot_model` 两套特征。

| 目标 | 训练 CV 选中模型 | 测试 RMSE (yd) | 测试 MAPE (%) | 测试 MAE (yd) | 测试 R2 |
|---|---|---:|---:|---:|---:|
| carry_distance_yd | launch_state_model / hist_gradient_boosting | 8.337 | 4.986 | 5.248 | 0.947 |
| apex_height_yd | launch_state_model / hist_gradient_boosting | 1.739 | 14.335 | 1.253 | 0.948 |

Dummy 基线在测试集上的 RMSE 分别为 36.343 yd 和 7.706 yd，说明监督模型确实学习到了发射状态与飞行输出之间的预测信息。完整指标、预测值、Bootstrap 区间和分组误差见：

- `questions/q2/artifacts/tables/q2_supervised_metrics.csv`
- `questions/q2/artifacts/tables/q2_supervised_predictions.csv`
- `questions/q2/artifacts/tables/q2_supervised_bootstrap_ci.csv`
- `questions/q2/artifacts/tables/q2_supervised_error_groups.csv`

## 4. ODE 第一阶段验证

物理常数来自题面 OCR 第 9 行及 `docs/references.md`：

| 常数 | 值 |
|---|---:|
| golf ball mass | 0.0456 kg |
| diameter | 0.04267 m |
| radius | 0.021335 m |
| air density | 1.225 kg/m^3 |
| gravity | 9.80665 m/s^2 |

单位换算和真空解析解校验通过：

| 检查 | 值 | 状态 |
|---|---:|---|
| 1 mph to m/s | 0.447040 | pass |
| 60 rpm to rad/s | 6.283185 | pass |
| 1 yd to m | 0.914400 | pass |
| 真空数值解与解析解最大差异 | 0.000456 | pass |
| drag carry 小于 vacuum carry | 2.725583 | pass |
| 落地事件 | 1.000000 | pass |

第一阶段仅做一维 `C_D` 粗网格扫描，得到 `C_D=0.05`，且该值位于搜索下界 `[0.05, 0.60]`。因此它只能作为 `preliminary_drag_only` 结果，不得宣称为最终阻力系数，更不得宣称已经得到 `C_L`。

| ODE 模型 | carry RMSE (yd) | carry MAPE (%) | apex RMSE (yd) | apex MAPE (%) | lateral MAE (yd) | failure rate |
|---|---:|---:|---:|---:|---:|---:|
| vacuum | 32.233 | 18.215 | 7.196 | 41.868 | 14.665 | 0.000 |
| drag | 36.465 | 21.028 | 7.591 | 43.890 | 15.052 | 0.000 |

drag-only 在当前粗网格和简化结构下没有优于 vacuum，说明下一阶段必须检查参数边界、升力方向、旋转项和距离定义后，再进入正式 `C_D/C_L` 标定。

## 5. 复现命令

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
python questions/q2/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_first_stage.py -q
```
