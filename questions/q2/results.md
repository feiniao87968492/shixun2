# q2 结果与结论

## 1. 数据划分与变量选择

使用 `random_seed=2026` 建立固定 70%/30% 主划分：train=514、test=221。划分保存于 `questions/q2/artifacts/tables/q2_data_split.csv`。监督模型和 ODE 测试评估均使用同一测试集；监督选模和 ODE 参数标定均不使用测试集。

主特征集 `launch_state_model` 使用球速、发射角、发射方向、自旋速率和自旋轴偏角；扩展特征集 `full_shot_model` 额外加入杆头速度和攻击角。

## 2. 监督预测基线

基线模型包括 `DummyRegressor(strategy="mean")`、线性回归和 RidgeCV。Dummy 基线在固定测试集上的 RMSE 为：

- carry: 36.343 yd
- apex: 7.706 yd

这些结果用于说明后续模型是否真正学习到击球状态与飞行输出之间的信息。

## 3. 监督主模型及测试结果

两个目标均由 `launch_state_model / hist_gradient_boosting` 在训练集 5 折 CV 中胜出。

| 目标 | 测试 RMSE (yd) | 测试 MAPE (%) | 测试 MAE (yd) | 测试 R2 |
|---|---:|---:|---:|---:|
| carry_distance_yd | 8.337 | 4.986 | 5.248 | 0.947 |
| apex_height_yd | 1.739 | 14.335 | 1.253 | 0.948 |

完整候选模型指标、测试预测和 Bootstrap 区间见 `q2_supervised_metrics.csv`、`q2_supervised_predictions.csv` 和 `q2_supervised_bootstrap_ci.csv`。

## 4. 预测误差诊断

预测散点图和残差图均已保存：

- `q2_prediction_scatter_carry.png`
- `q2_prediction_scatter_apex.png`
- `q2_residuals_carry.png`
- `q2_residuals_apex.png`

分组误差见 `q2_supervised_error_groups.csv`。30 次重复 70/30 划分显示，HistGradientBoosting 的 carry RMSE 均值为 7.720 yd，胜出频率 0.767；apex RMSE 均值为 1.742 yd，胜出频率 0.600。

## 5. 三维动力学方程

坐标定义为 `x` 前向、`y` 右向、`z` 向上。ODE 内部使用 SI 单位，输出换算为 yd。物理常数来自题面 OCR 与 `docs/references.md`：

| 常数 | 值 |
|---|---:|
| mass | 0.0456 kg |
| diameter | 0.04267 m |
| radius | 0.021335 m |
| air density | 1.225 kg/m^3 |
| gravity | 9.80665 m/s^2 |

自旋向量由 `spin_rate_rpm` 与 `spin_axis_deg` 构造，侧旋符号由 `q2_spin_geometry_check.csv` 的重构误差决定。验证表中 `positive_backspin_lifts_up=True`，说明当前坐标约定下正后旋产生向上升力。

## 6. 阻力和升力参数标定

参数只在训练集代表样本上标定，固定测试集不参与目标函数。

| 模型 | 参数 |
|---|---|
| drag | `C_D=0.05` |
| constant_lift | `C_D=0.27, C_L=0.18` |
| spin_factor_lift | `C_D=0.27, k_L=0.8` |

`drag` 的 `C_D=0.05` 位于下界，只能解释为仅阻力基线边界解；含升力参数应解释为当前简化模型下的有效参数。参数曲面见 `q2_ode_parameter_surface.csv/png`。

## 7. ODE 模型逐级比较

本题实现四层 ODE：

- `vacuum`：重力。
- `drag`：重力 + 二次阻力。
- `constant_lift`：重力 + 阻力 + 常数升力。
- `spin_factor_lift`：重力 + 阻力 + `C_L(S)=k_L S`。

四层模型均在固定测试集上积分成功，failure rate 均为 0。

## 8. 测试集 ODE 误差

| ODE 模型 | carry RMSE (yd) | carry MAPE (%) | apex RMSE (yd) | apex MAPE (%) | lateral MAE (yd) | failure rate |
|---|---:|---:|---:|---:|---:|---:|
| vacuum | 32.233 | 18.215 | 7.196 | 41.868 | 14.665 | 0.000 |
| drag | 36.465 | 21.028 | 7.591 | 43.890 | 15.052 | 0.000 |
| constant_lift | 16.506 | 10.284 | 3.069 | 16.261 | 8.410 | 0.000 |
| spin_factor_lift | 29.001 | 16.970 | 4.261 | 25.259 | 9.137 | 0.000 |

常数升力模型在当前数据上的整体误差最低；自旋因子升力对部分典型样本有效，但整体 carry 误差未优于常数升力。

## 9. 典型 100/150/200 yd 轨迹

典型记录从固定测试集按实际 carry 距目标最近选择：

| 目标 | sample_id | actual carry (yd) | 距目标 (yd) |
|---:|---:|---:|---:|
| 100 | 683 | 99.825 | 0.175 |
| 150 | 713 | 150.219 | 0.219 |
| 200 | 623 | 200.273 | 0.273 |

典型误差见 `q2_ode_typical_errors.csv`，轨迹点见 `q2_typical_trajectories.csv`，三维图、侧视图和俯视图均已保存。

## 10. 灵敏度与参数可识别性

灵敏度分析包括监督模型 30 次重复划分、ODE 参数扰动、积分器扰动和模型假设扰动。`q2_ode_sensitivity.csv` 显示，在典型记录上降低 `C_D` 会增加 carry，增加 `k_L` 会增加最高点和飞行时间。参数曲面用于检查 `C_D` 与升力参数之间的补偿关系和边界问题。

## 11. 监督模型与 ODE 的功能差异

监督模型在点预测精度上明显更高，适合直接预测 carry 和 apex。ODE 模型误差较大，但能生成完整三维轨迹、飞行时间、横向偏移和参数灵敏度，因此更适合解释物理机制和为第三问提供可搜索的轨迹接口。

## 12. 模型局限性

当前 ODE 使用全局有效气动参数、无完整风场、无精细自旋衰减和球面姿态模型；含升力参数不应外推为通用空气动力系数。数据为观测记录，第一问和第二问中的统计关系不应解释为因果效应。
