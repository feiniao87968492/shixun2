# q2 结果与结论

## 1. 数据划分与监督预测

第二问使用 `data/processed/golf_shots_clean.csv`。固定主划分仍为 train=514、test=221，`random_seed=2026`；监督模型选择和 ODE 参数标定均不读取测试集。

监督预测保留训练集 CV 选模规则：`carry_distance_yd` 与 `apex_height_yd` 均选择 `launch_state_model / hist_gradient_boosting`。固定测试集指标为：

| 目标 | RMSE (yd) | MAPE (%) | MAE (yd) | R2 |
|---|---:|---:|---:|---:|
| carry_distance_yd | 8.337 | 4.986 | 5.248 | 0.947 |
| apex_height_yd | 1.739 | 14.335 | 1.253 | 0.948 |

最高点任务中 HGB 与 ExtraTrees 表现接近；ExtraTrees 在固定测试集上可略低，但重复划分均值几乎相同。最终仍按预先规定的训练集 CV 规则选择 HGB。重复划分表中的胜出频率字段为 `split_comparison_win_frequency`，仅用于拆分稳定性比较，不解释为嵌套选模胜率。

## 2. ODE 标定整改

本轮按 `docs/plans/task4.md` 对 ODE 部分完成最终整改：

- drag 标定读取 `ode.drag_calibration`：代表样本 36 条，粗网格 10 点。
- lift 标定读取 `ode.lift_calibration`：代表样本 24 条，粗网格 6x6。
- 代表样本由球速、发射角、自旋率、carry 的多维 KMeans 覆盖抽取，分别保存为 `q2_drag_calibration_records.csv` 与 `q2_lift_calibration_records.csv`。
- 参数标定采用粗网格搜索后接有界 Powell 局部优化；优化尝试分别保存到三张 `q2_*_optimization_runs.csv`。
- 优化运行表记录 `optimizer_success`、`objective_finite`、`accepted`、初始/最终目标函数、真实终止信息、迭代数和函数评估数。
- 正式 ODE 求解器增加 `max_flight_time_s=20.0`，未触地但达到时间上限的样本记录为 `time_horizon_exceeded`，在标定目标中按失败惩罚处理。
- 目标函数统一使用配置中的 `carry_definition=forward_x`，积分失败不再静默丢弃，而是计入失败惩罚；选中运行均满足标定失败数、完整训练集失败数和测试失败率为 0。

重标定参数为：

| 模型 | 参数 |
|---|---|
| drag | `C_D=0.05` |
| constant_lift | `C_D=0.238654, C_L=0.203952` |
| spin_factor_lift | `C_D=0.050059, k_L=0.151837` |

`drag` 的 `C_D=0.05` 位于下界，且测试误差劣于 vacuum，因此标记为 `boundary_solution`，不能解释为可信阻力系数。含升力模型参数仅解释为当前简化 ODE 下的有效参数。

## 3. ODE 测试集表现

| ODE 模型 | D_x carry RMSE (yd) | carry MAPE (%) | apex RMSE (yd) | apex R2 | failure rate |
|---|---:|---:|---:|---:|---:|
| vacuum | 32.502 | 18.557 | 7.196 | 0.118 | 0.000 |
| drag | 36.830 | 21.448 | 7.591 | 0.019 | 0.000 |
| constant_lift | 7.157 | 4.412 | 2.173 | 0.920 | 0.000 |
| spin_factor_lift | 30.530 | 17.674 | 6.410 | 0.300 | 0.000 |

第二问 best-fit ODE 由完整训练集目标自动确定为 `constant_lift`。`spin_factor_lift` 作为第三问兼容 ODE 接口单独保留，不再混写为无语义的 `trajectory_model`；该模型通过 16 个边界组合稳定性检查，最大飞行时间 8.611 s、最大最高点 93.551 yd、最大横向距离 152.335 yd。

## 4. 距离定义与典型轨迹

本轮同时比较两种飞行距离定义：

- `D_x=x_land`：前向落点距离。
- `D_r=sqrt(x_land^2+y_land^2)`：水平欧氏落点距离。

`q2_carry_definition_comparison.csv` 明确记录实际与预测口径：主定义 `D_x` 使用 `actual=carry_distance_yd`、`predicted=predicted_x_carry_yd`；径向对照 `D_r` 使用 `actual=sqrt(carry_distance_yd^2+lateral_offset_yd^2)`、`predicted=predicted_radial_carry_yd`。最终采用前向距离 `D_x` 作为论文主距离定义。测试集比较仅作为诊断，不用于反复调参。

典型 100/150/200 yd 记录仍为固定测试集中的 sample_id 683、713、623。轨迹产物分两套：

- 第二问主轨迹：`q2_typical_trajectories_constant_lift.csv` 与同名 3D/side/top 图。
- 第三问接口轨迹：`q2_typical_trajectories_spin_factor.csv` 与同名 3D/side/top 图。

## 5. 灵敏度与初始高度

灵敏度分析同时覆盖 `constant_lift` 与 `spin_factor_lift`，包括参数扰动、顺/逆风、spin decay、solver tolerance 和初始高度。坐标系中 x 轴向前为正，因此：

- `tailwind_1mps=(1,0,0)`；
- `headwind_1mps=(-1,0,0)`。

平均 carry 在 0.01 yd 数值容差内满足顺风不低于无风、无风不低于逆风。初始高度 `initial_height_m=0.01` 的类型标记为 `numerical_convention`，仅用于避免积分初始时刻立即触发落地事件，不是题面给定或实测击球高度；0.001、0.01、0.05 m 的扰动已写入 `q2_ode_sensitivity.csv`。

## 6. 验证与元数据

`questions/q2/scripts/validate.py` 已扩展到 166 项检查，覆盖配置接线、优化运行、边界字段、训练/测试无泄漏、风向、forward_x 指标复算、失败样本表、Q3 边界稳定性、状态同步、metadata 和 task7 的 `max_flight_time_s` 配置。`run_metadata.json` 记录 Git commit、数据与配置 SHA256、包版本、固定 split 哈希、drag/lift 代表样本 ID、ODE 角色、完整训练集目标、Q3 边界检查结论、求解器配置和优化运行表路径，且路径统一为 POSIX 风格。

重复运行 `python questions/q2/scripts/pipeline.py --config configs/default.yaml` 后，主要 CSV 哈希一致，说明固定测试集、代表样本、参数和主要结果可复现。

## 7. 局限

ODE 使用全局有效气动参数、简化 Magnus 力、无完整风场与球面姿态模型；因此其价值主要在于生成可解释轨迹、敏感性分析和第三问可搜索接口。若目标是单点预测，监督模型精度更高。
