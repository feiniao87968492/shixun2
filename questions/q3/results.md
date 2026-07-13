# q3 结果与结论

## 1. 当前状态

第三问已完成 `docs/plans/task6.md` 要求的最终稳健性整改。正式入口：

```bash
python questions/q3/scripts/pipeline.py --config configs/default.yaml
python questions/q3/scripts/validate.py --config configs/default.yaml
```

## 2. 依赖与数据

q3 复用 q2 固定划分，train=514、test=221，未重新划分数据。依赖审计见 `questions/q3/artifacts/tables/q3_dependency_audit.csv`，q2 carry/apex 模型、q2 ODE 参数、q2 元数据和 q2 validation 均通过检查；q3 ODE 复核条件为 `q3_ode_verified=true`。

横向偏移模型只在 q2 train 上训练，用 q2 test 评价。`hist_gradient_boosting` 按训练集 5 折 CV RMSE 胜出：

| 模型 | CV RMSE | 测试 RMSE | 测试 MAE | R2 | bias |
|---|---:|---:|---:|---:|---:|
| hist_gradient_boosting | 5.369 | 5.475 | 3.870 | 0.958 | 0.939 |
| extra_trees | 5.648 | 5.773 | 3.914 | 0.953 | 0.348 |
| ridge | 9.370 | 11.472 | 7.343 | 0.813 | 1.849 |

横向偏移可能接近 0，因此未使用 MAPE 作为主指标。

## 3. 优化结果

最佳观测训练记录为 `record_id=609`，实测 carry=198.403 yd、lateral=-5.107 yd，距洞口 5.351 yd。

| 结果 | 球速 mph | 发射角 deg | 自旋 rpm | 自旋轴 deg | 预测 carry yd | 预测 lateral yd | 目标函数 yd | 支持类别 | 用途 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 名义最优 | 121.113 | 19.616 | 2627.708 | -0.366 | 199.992 | -0.007 | 0.010 | supported | 单一监督代理内的名义残差基线 |
| 单代理参数稳健解 | 120.868 | 18.978 | 2344.294 | 0.118 | 199.874 | 0.092 | 0.156 | supported | 仅参数扰动下的比较解 |
| 联合模型-参数稳健推荐 | 122.958 | 20.437 | 2720.784 | -1.255 | 199.810 | 0.073 | 0.204 | supported | 最终论文推荐 |

20,000 点 LHS 基线、5 个随机种子的差分进化和每个 DE 解附近 5,000 点局部采样均完成。五次差分进化的结果均记录 `scipy_success`、`objective_finite` 和 `accepted`，避免把有限目标值误写成求解器成功状态。

## 4. 稳健性与不确定性

task6 不再只比较前 12 个候选，而是将支持区近优候选全部纳入稳健分析。`q3_robust_candidate_pool.csv` 中 `selected_for_robustness=true` 的候选共 482 个，selection_method 均为 `all_supported_near_optimal`。

扰动场景包括：

| 场景 | 发射方向标准差 |
|---|---:|
| ideal | 0.0 deg |
| stable_player | 0.5 deg |
| ordinary_player | 1.0 deg |

所有候选在同一场景内使用共同随机数，并输出 p90 bootstrap 区间和统计并列标记。单代理参数稳健解在 stable_player 场景下 p90 距洞为 4.932 yd。

最终推荐按 stable_player 场景下的联合模型-参数 p90 选择。联合稳健推荐的结果为：

- mean miss distance = 3.825 yd；
- median miss distance = 3.266 yd；
- p90 miss distance = 7.133 yd；
- p95 miss distance = 8.332 yd；
- probability within 3 yd = 0.451；
- probability within 5 yd = 0.724；
- objective prediction std = 1.487 yd。

上述概率仅是在指定参数误差分布、发射方向误差情景和代理模型集合下的模拟比例，不是真实球员命中概率。考虑模型分歧后，真实策略不确定性明显大于 0.010 yd 的名义代理残差。

## 5. 目标距离重优化与非唯一性

195/200/205 yd 不再复用 200 yd 候选池，而是分别执行 LHS、至少 3 个 DE seed 和局部 refinement。支持区最优如下：

| 目标距离 yd | 候选 ID | 球速 mph | 发射角 deg | 自旋 rpm | 自旋轴 deg | 预测 carry yd | 预测 lateral yd | 目标函数 yd |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 195 | target_195_local_2028_03426 | 121.195 | 23.636 | 2825.663 | -2.282 | 194.990 | -0.005 | 0.011 |
| 200 | target_200_de_seed_2026 | 121.113 | 19.616 | 2627.708 | -0.366 | 199.992 | -0.007 | 0.010 |
| 205 | target_205_local_2027_01757 | 127.912 | 17.657 | 6447.625 | -0.903 | 205.005 | -0.015 | 0.016 |

近优解并非唯一。482 个支持区近优候选对应 256 个不同预测落点组合，最大预测平台规模为 20。近优参数范围保存于 `q3_near_optimal_parameter_ranges.csv`，说明论文不应把单点参数写成唯一可执行策略。

## 6. ODE 复核与轨迹

对最佳观测记录、名义最优、单代理稳健解和联合稳健推荐分别运行 q2 `constant_lift` 与 `spin_factor_lift` ODE，全部积分成功。联合稳健推荐的 ODE 复核结果显示监督代理和简化 ODE 对最优区仍存在数 yd 级差异，因此 ODE 仅作为轨迹交叉检查和外推风险提示。三维、侧视和俯视轨迹图均标出起点、最高点、落点、洞口和落点到洞口误差线，图表数据与 meta.json 已生成。

## 7. 局限

- q3 主优化依赖 q2 监督代理模型；模型交叉检查显示最优区有较强模型分歧。
- 扰动范围是情景假设，不是球员测量误差的实测分布。
- ODE 使用简化空气动力学有效参数，不能把监督-ODE 交叉检查写成真实击球实验验证。
- 稳健推荐优先选择训练支持区内近优点；若实际球员可控范围更窄，需要重新设置边界并复跑 pipeline。
