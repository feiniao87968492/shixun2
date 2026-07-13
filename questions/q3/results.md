# q3 结果与结论

## 1. 当前状态

第三问已完成 `docs/plans/task5.md` 要求的稳健反设计流程。正式入口：

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

| 结果 | 球速 mph | 发射角 deg | 自旋 rpm | 自旋轴 deg | 预测 carry yd | 预测 lateral yd | 预测 apex yd | 目标函数 yd | 支持类别 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 名义最优 | 121.113 | 19.616 | 2627.708 | -0.366 | 199.992 | -0.007 | 28.764 | 0.010 | supported |
| 稳健推荐 | 120.751 | 19.482 | 2348.781 | 0.450 | 200.006 | -0.021 | 28.060 | 0.022 | supported |

20,000 点 LHS 基线、5 个随机种子的差分进化和每个 DE 解附近 5,000 点局部采样均完成。五次差分进化的最优目标函数分别为 0.010、0.031、0.020、0.031、0.012 yd，均位于训练支持区。

## 4. 稳健性与不确定性

稳健推荐解在 2,000 次参数扰动下：

- mean miss distance = 1.563 yd；
- median miss distance = 1.277 yd；
- p90 miss distance = 3.135 yd；
- probability within 3 yd = 0.887；
- probability within 5 yd = 0.992。

模型集合交叉检查显示两个最优点均为 `highly_model_sensitive`：稳健推荐解的 carry 预测标准差为 4.002 yd，lateral 预测标准差为 0.576 yd，目标函数预测标准差为 3.925 yd。因此论文推荐应写作“监督代理模型下的稳健推荐”，不能解释为真实物理最优或唯一全局策略。

目标距离 195/200/205 yd 灵敏度结果保存在 `q3_target_distance_sensitivity.csv`。不同目标距离下均重新计算目标函数并记录硬边界最优和支持区最优。

## 5. ODE 复核与轨迹

对最佳观测记录、名义最优和稳健推荐分别运行 q2 `constant_lift` 与 `spin_factor_lift` ODE，全部积分成功。稳健推荐的 ODE 复核结果：

| ODE | D_x carry yd | lateral yd | apex yd | 监督 carry - ODE carry yd |
|---|---:|---:|---:|---:|
| constant_lift | 193.187 | 0.557 | 31.068 | 6.819 |
| spin_factor_lift | 195.032 | 0.044 | 18.389 | 4.974 |

监督代理和简化 ODE 对最优区存在明显差异，因此 ODE 仅作为轨迹交叉检查和外推风险提示。三维、侧视和俯视轨迹图均标出起点、最高点、落点、洞口和落点到洞口误差线，图表数据与 meta.json 已生成。

## 6. 局限

- q3 主优化依赖 q2 监督代理模型；模型交叉检查显示最优区有较强模型分歧。
- 扰动范围是情景假设，不是球员测量误差的实测分布。
- ODE 使用简化空气动力学有效参数，不能把监督-ODE 交叉检查写成真实击球实验验证。
- 稳健推荐优先选择训练支持区内近优点；若实际球员可控范围更窄，需要重新设置边界并复跑 pipeline。
