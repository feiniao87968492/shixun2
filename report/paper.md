# 2026 年实训题2 高尔夫球飞行轨迹预测与最优击球策略建模 - 论文草稿

> 本文件用于保持论文正文与仓库证据链同步，正式排版可迁移到 LaTeX、Word 或竞赛模板。

## 摘要

本文基于 735 条高尔夫球实测击球记录，先分析输入击球参数与飞行输出之间的统计关联，再建立飞行距离和最高点高度的监督预测模型，并逐步构建三维动力学轨迹模型。第一问完成数据审计和影响因素分层解释：球速是飞行距离最稳定的关键关联因素，杆头速度与球速存在信息重叠，发射角呈结构性非线性贡献，攻击角不宜写作稳定关键因素。第二问当前完成第一阶段：固定 70%/30% 划分下，HistGradientBoosting 监督模型在飞行距离和最高点高度预测上显著优于 dummy 基线；真空和仅阻力 ODE 已通过单位换算、落地事件和真空解析解校验，但尚未完成最终 `C_D/C_L` 标定。

## 问题重述

题目要求围绕高尔夫球实测飞行数据完成三项任务：分析影响飞行距离的关键因素；预测飞行距离和最高点高度并建立三维轨迹模型；在 200 yd 目标约束下搜索最优击球参数。本文所有结论均以 `docs/evidence_chain.csv` 登记的脚本、数据和产物为准。

## 模型假设与符号

详见 `docs/assumptions.md` 与 `docs/symbols.md`。第一问只作统计关联和预测信息分析，不将相关性解释为因果效应。第二问第一阶段只声明真空/仅阻力 ODE 的数值正确性和预测误差，不声明最终空气动力参数。

## 第一问：落点影响因素分析

第一问使用 735 条记录，输入变量包括球速、发射角、发射方向、自旋速率、自旋轴偏角、后旋、侧旋、杆头速度和攻击角，输出变量包括飞行距离、最高点高度、总距离和横向偏移。`record_id=225,226,308` 的杆头速度和攻击角异常 0 值已按规则修正为缺失。修正后杆头速度缺失 66 条，攻击角缺失 68 条。

相关性和模型结果显示，球速与飞行距离 Pearson=0.758、Spearman=0.776，边际相关 Bootstrap 排名区间为 1-1，是最稳定的关键变量。杆头速度修正后与飞行距离 Pearson=0.581、Spearman=0.589，但在 669 条共同样本和相同 5x5 CV 折上，仅球速模型 RMSE=24.43 yd，同时加入杆头速度后 RMSE=24.42 yd，说明额外预测信息很小。发射角边际线性相关较弱，但二次项模型和非线性置换重要性显示其具有结构性贡献。攻击角边际相关弱且 Ridge 方向不稳定，不写作稳定关键因素。

主要证据：

- `questions/q1/artifacts/tables/q1_feature_summary.csv`
- `questions/q1/artifacts/tables/q1_invalid_zero_records.csv`
- `questions/q1/artifacts/tables/q1_speed_overlap_models.csv`
- `questions/q1/artifacts/tables/q1_launch_angle_quadratic.csv`
- `questions/q1/artifacts/figures/q1_raw_importance_comparison.png`

## 第二问：飞行轨迹预测第一阶段

第二问使用 q1 清洗后的 `data/processed/golf_shots_clean.csv`。固定主划分为 train=514、test=221，随机种子为 2026。监督模型比较 Dummy、线性回归、RidgeCV、ExtraTrees 和 HistGradientBoosting，并分别使用 `launch_state_model` 与 `full_shot_model` 两套特征。模型选择只依据训练集 5 折 CV RMSE，测试集只用于最终评估。

当前两个目标均由 `launch_state_model / hist_gradient_boosting` 在训练 CV 中胜出。飞行距离测试 RMSE=8.337 yd、MAPE=4.986%、MAE=5.248 yd、R2=0.947；最高点高度测试 RMSE=1.739 yd、MAPE=14.335%、MAE=1.253 yd、R2=0.948。相比 dummy 基线的 36.343 yd 和 7.706 yd RMSE，监督模型具备明显预测能力。

ODE 第一阶段使用题面物理常数：质量 0.0456 kg、直径 0.04267 m、空气密度 1.225 kg/m^3、重力加速度 9.80665 m/s^2。mph、rpm、yd 换算和真空解析解校验均通过，真空数值解与解析解最大差异为 0.000456。测试集上 vacuum carry RMSE=32.233 yd、drag-only carry RMSE=36.465 yd，二者积分失败率均为 0。drag-only 粗网格得到 `C_D=0.05`，但该值位于搜索下界且误差未优于 vacuum，因此只作为物理基线，不能作为最终阻力系数。

主要证据：

- `questions/q2/artifacts/tables/q2_supervised_metrics.csv`
- `questions/q2/artifacts/tables/q2_supervised_predictions.csv`
- `questions/q2/artifacts/tables/q2_ode_validation_checks.csv`
- `questions/q2/artifacts/tables/q2_ode_test_metrics.csv`
- `questions/q2/artifacts/figures/q2_prediction_scatter_carry.png`
- `questions/q2/artifacts/figures/q2_ode_model_comparison.png`

## 第三问：最优击球策略

待完成。第三问应复用 q2 已验证的数据划分、监督代理模型和 ODE 接口，但必须等待含升力 ODE 和最终参数标定完成后，再开展 200 yd 目标搜索。

## 模型评价与局限

第一问结果已通过 Bootstrap、重复交叉验证、缺失口径敏感性和自动验证检查。第二问第一阶段已通过固定划分、监督模型测试指标、ODE 单位换算和真空解析解验证。当前主要局限在于：数据是观察记录，不能直接支持因果判断；Q2 ODE 尚未包含升力和自旋衰减；drag-only 参数位于边界，不能解释为最终气动系数；Q3 尚未实现。

## 结论

第一问结论：球速是飞行距离最稳定的关键关联因素；杆头速度有边际关联但与球速重叠；发射角具有结构性非线性贡献；攻击角不作为稳定关键因素。第二问第一阶段结论：固定测试集上监督模型可有效预测飞行距离和最高点高度；真空/仅阻力 ODE 的基础数值接口已通过验证，但最终 `C_D/C_L` 标定、典型轨迹和灵敏度分析仍需后续完成。
