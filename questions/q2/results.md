# q2 结果与结论

## 1. 数据划分与变量选择

使用 `random_seed=2026` 建立固定 70%/30% 主划分：

| split | 样本数 | 产物 |
|---|---:|---|
| train | 514 | `questions/q2/artifacts/tables/q2_data_split.csv` |
| test | 221 | `questions/q2/artifacts/tables/q2_data_split.csv` |

监督模型和 ODE 测试评估均使用同一测试集；模型选择和 ODE 参数标定不使用测试集。

## 2. 监督预测结果

两个目标均由 `launch_state_model / hist_gradient_boosting` 在训练集 CV 中胜出。

| 目标 | 测试 RMSE (yd) | 测试 MAPE (%) | 测试 MAE (yd) | 测试 R2 |
|---|---:|---:|---:|---:|
| carry_distance_yd | 8.337 | 4.986 | 5.248 | 0.947 |
| apex_height_yd | 1.739 | 14.335 | 1.253 | 0.948 |

30 次重复 70/30 划分显示，HistGradientBoosting 的 carry RMSE 均值为 7.720 yd，胜出频率 0.767；apex RMSE 均值为 1.742 yd，胜出频率 0.600。完整结果见 `q2_supervised_repeated_split.csv`。

## 3. 三维动力学方程

ODE 内部使用 SI 单位，输出换算为 yd。物理常数来自题面 OCR 与 `docs/references.md`：

| 常数 | 值 |
|---|---:|
| mass | 0.0456 kg |
| diameter | 0.04267 m |
| radius | 0.021335 m |
| air density | 1.225 kg/m^3 |
| gravity | 9.80665 m/s^2 |

验证检查全部通过：mph/rpm/yd 单位换算、真空数值解与解析解、落地事件、正后旋向上升力、零侧旋零方向时横向位移接近 0。

## 4. 阻力和升力参数标定

参数只在训练集代表样本上标定，测试集不参与目标函数。

| 模型 | 参数 |
|---|---|
| drag | `C_D=0.05` |
| constant_lift | `C_D=0.27, C_L=0.18` |
| spin_factor_lift | `C_D=0.27, k_L=0.8` |

`drag` 的 `C_D=0.05` 仍在下界，应解释为 drag-only 基线的边界解；含升力模型改善说明仅阻力结构不足。参数曲面见 `q2_ode_parameter_surface.csv/png`。

## 5. ODE 测试集比较

| ODE 模型 | carry RMSE (yd) | carry MAPE (%) | apex RMSE (yd) | apex MAPE (%) | lateral MAE (yd) | failure rate |
|---|---:|---:|---:|---:|---:|---:|
| vacuum | 32.233 | 18.215 | 7.196 | 41.868 | 14.665 | 0.000 |
| drag | 36.465 | 21.028 | 7.591 | 43.890 | 15.052 | 0.000 |
| constant_lift | 16.506 | 10.284 | 3.069 | 16.261 | 8.410 | 0.000 |
| spin_factor_lift | 29.001 | 16.970 | 4.261 | 25.259 | 9.137 | 0.000 |

常数升力模型在当前数据上误差最低；自旋因子升力对最高点和部分典型样本有改善，但整体 carry 误差未优于常数升力。

## 6. 典型 100/150/200 yd 轨迹

典型记录从固定测试集按实际 carry 距目标最近选择：

| 目标 | sample_id | actual carry (yd) | 距目标 (yd) |
|---:|---:|---:|---:|
| 100 | 683 | 99.825 | 0.175 |
| 150 | 713 | 150.219 | 0.219 |
| 200 | 623 | 200.273 | 0.273 |

典型误差见 `q2_ode_typical_errors.csv`，轨迹点见 `q2_typical_trajectories.csv`，三视图见：

- `q2_typical_trajectories_3d.png`
- `q2_typical_trajectories_side.png`
- `q2_typical_trajectories_top.png`

## 7. 灵敏度与局限

ODE 灵敏度表明：在典型记录上，降低 `C_D` 会增加 carry，增加 `k_L` 会增加最高点和飞行时间；小风速、自旋衰减和积分器参数变化均已记录在 `q2_ode_sensitivity.csv`。当前 ODE 仍是全局有效参数模型，适合生成可解释轨迹和为 q3 提供接口，但监督模型在点预测精度上更高。

## 8. 复现命令

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
python questions/q2/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_full_task2.py -q
```
