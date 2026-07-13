# 2026 实训题2 高尔夫球飞行轨迹预测与最优击球策略建模 - 论文草稿

> 本文件用于保持论文正文与仓库证据链同步，正式排版可迁移到 LaTeX、Word 或竞赛模板。

## 摘要

本文基于 735 条高尔夫球实测击球记录，先分析输入击球参数与飞行输出之间的统计关联，再建立飞行距离和最高点高度的监督预测模型，并构建三维动力学轨迹模型。第一问结果显示，球速是飞行距离最稳定的关键关联因素，杆头速度与球速存在信息重叠，发射角具有结构性非线性贡献，攻击角不宜写作稳定关键因素。第二问完成固定 70%/30% 划分下的监督预测与四层 ODE 轨迹模型：HistGradientBoosting 在 carry 和 apex 预测中分别达到 RMSE=8.337 yd 与 1.739 yd；含常数升力 ODE 的测试集 carry RMSE=16.506 yd，明显优于 vacuum 和 drag-only。第三问尚待在 q2 已验证接口基础上开展 200 yd 目标优化。

## 问题重述

题目要求完成三项任务：分析影响飞行距离的关键因素；预测飞行距离和最高点高度并建立三维轨迹模型；在 200 yd 目标约束下搜索最优击球参数。所有结论均以 `docs/evidence_chain.csv` 登记的脚本、数据和产物为准。

## 第一问：落点影响因素分析

第一问使用 735 条记录。输入变量包括球速、发射角、发射方向、自旋速率、自旋轴偏角、后旋、侧旋、杆头速度和攻击角；输出变量包括飞行距离、最高点高度、总距离和横向偏移。`record_id=225,226,308` 的杆头速度和攻击角异常 0 值已按规则修正为缺失。

主要结论：

- 球速与飞行距离 Pearson=0.758、Spearman=0.776，是最稳定的关键关联变量。
- 杆头速度边际相关较强，但与球速重叠；同样本配对 CV 下，加入杆头速度对仅球速模型的 RMSE 改善极小。
- 发射角边际线性相关较弱，但二次项模型和非线性置换重要性显示其具有结构性贡献。
- 攻击角相关弱且 Ridge 方向不稳定，不写作稳定关键因素。

主要证据：

- `questions/q1/artifacts/tables/q1_feature_summary.csv`
- `questions/q1/artifacts/tables/q1_speed_overlap_fold_scores.csv`
- `questions/q1/artifacts/tables/q1_launch_angle_quadratic.csv`
- `questions/q1/artifacts/figures/q1_raw_importance_comparison.png`

## 第二问：监督预测

第二问使用 q1 清洗后的 `data/processed/golf_shots_clean.csv`。固定主划分为 train=514、test=221，随机种子 2026。监督模型比较 Dummy、Linear、RidgeCV、ExtraTrees 和 HistGradientBoosting，并分别使用 `launch_state_model` 与 `full_shot_model` 两套特征。模型选择只依据训练集 5 折 CV RMSE，测试集只用于最终评价。

两个目标均由 `launch_state_model / hist_gradient_boosting` 在训练集 CV 中胜出。测试集结果如下：

| 目标 | RMSE (yd) | MAPE (%) | MAE (yd) | R2 |
|---|---:|---:|---:|---:|
| carry_distance_yd | 8.337 | 4.986 | 5.248 | 0.947 |
| apex_height_yd | 1.739 | 14.335 | 1.253 | 0.948 |

30 次重复 70/30 划分稳定性显示，HistGradientBoosting 在 carry 目标上的胜出频率为 0.767，apex 目标胜出频率为 0.600。

## 第二问：三维 ODE 轨迹模型

坐标定义为 `x` 前向、`y` 右向、`z` 向上。ODE 内部使用 SI 单位，输出换算为 yd。自旋向量由 `spin_rate_rpm` 和 `spin_axis_deg` 构造；侧旋符号由 `q2_spin_geometry_check.csv` 的重构误差决定。正后旋在该坐标下产生向上 Magnus 力，验证表中 `positive_backspin_lifts_up=True`。

模型层级：

- `vacuum`：重力。
- `drag`：重力 + 二次阻力。
- `constant_lift`：重力 + 阻力 + 常数升力。
- `spin_factor_lift`：重力 + 阻力 + `C_L(S)=k_L S`。

参数只在训练集代表样本上标定，固定测试集不参与目标函数：

| 模型 | 参数 |
|---|---|
| drag | `C_D=0.05` |
| constant_lift | `C_D=0.27, C_L=0.18` |
| spin_factor_lift | `C_D=0.49, k_L=1.6` |

`drag` 的 `C_D=0.05` 位于搜索下界，不能解释为真实阻力系数；含升力模型参数应解释为当前简化 ODE 的有效参数。

测试集四层模型比较：

| ODE 模型 | carry RMSE (yd) | apex RMSE (yd) | lateral MAE (yd) | failure rate |
|---|---:|---:|---:|---:|
| vacuum | 32.233 | 7.196 | 14.665 | 0.000 |
| drag | 36.465 | 7.591 | 15.052 | 0.000 |
| constant_lift | 16.506 | 3.069 | 8.410 | 0.000 |
| spin_factor_lift | 31.996 | 7.885 | 10.832 | 0.000 |

常数升力模型在整体测试误差上最低；自旋因子升力在部分典型样本上表现更接近，但整体 carry 误差未优于常数升力。

典型 100/150/200 yd 记录从测试集按实际 carry 距目标最近选择，样本为 683、713、623。轨迹点、三维图、侧视图和俯视图均已生成，并可由 pipeline 复现。

主要证据：

- `questions/q2/artifacts/tables/q2_supervised_metrics.csv`
- `questions/q2/artifacts/tables/q2_ode_parameters.csv`
- `questions/q2/artifacts/tables/q2_ode_test_metrics.csv`
- `questions/q2/artifacts/tables/q2_typical_records.csv`
- `questions/q2/artifacts/tables/q2_ode_sensitivity.csv`
- `questions/q2/artifacts/figures/q2_typical_trajectories_3d.png`

## 第三问：最优击球策略

第三问待完成。应复用 q2 已验证的监督代理模型、ODE 接口和发射状态变量，在 200 yd 目标下搜索击球参数组合。

## 局限

本文当前结论来自观测数据，不能直接支持因果判断。Q2 的 ODE 使用全局有效参数、无完整风场、无精细自旋衰减和球面姿态模型，因此更适合解释轨迹生成机制和服务后续优化；若目标是单点预测，监督模型精度更高。
