# 2026 实训题2 高尔夫球飞行轨迹预测与最优击球策略建模 - 论文草稿

> 本文件用于保持论文正文与仓库证据链同步，正式排版可迁移到 LaTeX、Word 或竞赛模板。

## 摘要

本文基于 735 条高尔夫球实测击球记录，先分析输入击球参数与飞行输出之间的统计关联，再建立飞行距离和最高点高度的监督预测模型，并构建三维动力学轨迹模型，最后求解 200 yd 目标下的稳健击球策略。第一问结果显示，球速是飞行距离最稳定的关键关联因素，杆头速度与球速存在信息重叠，发射角具有结构性非线性贡献，攻击角不宜写作稳定关键因素。第二问完成固定 70%/30% 划分下的监督预测与四层 ODE 轨迹模型：HistGradientBoosting 在 carry 和 apex 预测中分别达到 RMSE=8.337 yd 与 1.739 yd；按 forward-x carry 统一重标定后，含常数升力 ODE 的测试集 D_x carry RMSE=7.157 yd，明显优于 vacuum 和 drag-only。第三问以 q2 carry 模型和 q3 lateral 模型构造监督目标函数，得到稳健推荐参数：球速 120.751 mph、发射角 19.482 度、自旋速率 2348.781 rpm、自旋轴偏角 0.450 度，预测距洞 0.022 yd，扰动 p90 距洞 3.135 yd。模型分歧检查显示最优区为 highly_model_sensitive，因此结论应解释为监督代理下的推荐策略，并由 ODE 轨迹作交叉检查。

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
| constant_lift | `C_D=0.238654, C_L=0.203952` |
| spin_factor_lift | `C_D=0.050059, k_L=0.151837` |

`drag` 的 `C_D=0.05` 位于搜索下界，不能解释为真实阻力系数；含升力模型参数应解释为当前简化 ODE 的有效参数。

测试集四层模型比较：

| ODE 模型 | D_x carry RMSE (yd) | apex RMSE (yd) | lateral MAE (yd) | failure rate |
|---|---:|---:|---:|---:|
| vacuum | 32.502 | 7.196 | 14.665 | 0.000 |
| drag | 36.830 | 7.591 | 15.052 | 0.000 |
| constant_lift | 7.157 | 2.173 | 2.961 | 0.000 |
| spin_factor_lift | 30.530 | 6.410 | 5.173 | 0.000 |

常数升力模型由完整训练集目标自动确定为第二问 best-fit ODE，且在固定测试集上 D_x carry 误差最低；自旋因子升力作为第三问兼容 ODE 保留，并通过 16 个边界组合稳定性检查。

典型 100/150/200 yd 记录从测试集按实际 carry 距目标最近选择，样本为 683、713、623。轨迹点、三维图、侧视图和俯视图均已生成，并可由 pipeline 复现。

主要证据：

- `questions/q2/artifacts/tables/q2_supervised_metrics.csv`
- `questions/q2/artifacts/tables/q2_ode_parameters.csv`
- `questions/q2/artifacts/tables/q2_ode_test_metrics.csv`
- `questions/q2/artifacts/tables/q2_typical_records.csv`
- `questions/q2/artifacts/tables/q2_ode_sensitivity.csv`
- `questions/q2/artifacts/figures/q2_typical_trajectories_3d.png`

## 第三问：最优击球策略

第三问固定发射方向为 0 度，决策变量为球速、发射角、自旋速率和自旋轴偏角。目标函数为

```text
J(u)=sqrt((D(u)-200)^2 + L(u)^2)
```

其中 `D(u)` 使用 q2 carry 监督模型预测，`L(u)` 使用 q3 在固定 q2 训练集上训练的 lateral 代理模型预测。横向偏移模型比较 Dummy、Linear、Ridge、HistGradientBoosting 和 ExtraTrees，按训练集 5 折 CV RMSE 选择 HistGradientBoosting；其固定测试集 RMSE=5.475 yd，MAE=3.870 yd，R2=0.958。

为防止把外推点误作可执行策略，q3 在 q2 训练集四维发射状态空间中计算 k=5 的 kNN 支持距离，并以留一法距离的 95% 分位数作为 supported 阈值。优化证据包括：训练集最佳观测记录、20,000 点 LHS 基线、5 个随机种子的差分进化和每个 DE 解附近 5,000 点局部 LHS 采样。最佳观测训练记录为 `record_id=609`，实测距洞口 5.351 yd。

名义最优为：

| 参数 | 数值 |
|---|---:|
| 球速 | 121.113 mph |
| 发射角 | 19.616 degree |
| 自旋速率 | 2627.708 rpm |
| 自旋轴偏角 | -0.366 degree |
| 预测 carry | 199.992 yd |
| 预测 lateral | -0.007 yd |
| 目标函数 | 0.010 yd |

稳健推荐为：

| 参数 | 数值 |
|---|---:|
| 球速 | 120.751 mph |
| 发射角 | 19.482 degree |
| 自旋速率 | 2348.781 rpm |
| 自旋轴偏角 | 0.450 degree |
| 预测 carry | 200.006 yd |
| 预测 lateral | -0.021 yd |
| 目标函数 | 0.022 yd |
| 扰动 p90 距洞 | 3.135 yd |

2,000 次参数扰动显示，稳健推荐距洞小于 3 yd 的概率为 0.887，小于 5 yd 的概率为 0.992。模型集合交叉检查显示名义和稳健点均为 `highly_model_sensitive`，说明不同代理模型对最优区预测差异较大。因此论文结论采用稳健推荐，但明确它是监督代理模型下的数据驱动策略。

ODE 复核使用 q2 `constant_lift` 和 `spin_factor_lift`，对最佳观测记录、名义最优和稳健推荐均积分成功。稳健推荐在 `constant_lift` 下 D_x carry=193.187 yd、lateral=0.557 yd；在 `spin_factor_lift` 下 D_x carry=195.032 yd、lateral=0.044 yd。监督模型与 ODE 的差异提示该区域存在物理外推不确定性，故 ODE 只作为交叉检查和轨迹展示，不作为真实击球验证。

## 局限

本文当前结论来自观测数据，不能直接支持因果判断。Q2 的 ODE 使用全局有效参数、无完整风场、无精细自旋衰减和球面姿态模型，因此更适合解释轨迹生成机制和服务后续优化；若目标是单点预测，监督模型精度更高。Q3 的最优策略对代理模型选择敏感，且扰动范围为情景假设，不代表实测球员误差分布。
