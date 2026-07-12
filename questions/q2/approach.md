# q2 解法方案：监督预测与三维 ODE 轨迹

## 1. 输入与输出

输入数据为 q1 清洗后的 `data/processed/golf_shots_clean.csv`。Q2 在加载层把 q1 的 `max_height_yd` 显式映射为本题术语 `apex_height_yd`，不修改 q1 产物。

监督模型目标：

- `carry_distance_yd`
- `apex_height_yd`

ODE 输出：

- 飞行距离
- 最高点高度
- 横向偏移
- 飞行时间
- 完整三维轨迹

## 2. 固定划分与防泄漏

使用 `random_seed=2026` 和 `test_size=0.30` 建立主划分，保存到 `q2_data_split.csv`。当前样本数为 train=514、test=221。

规则：

- 监督模型选择只使用训练集 5 折交叉验证。
- ODE 参数标定只使用训练集代表样本。
- 固定测试集只用于最终评估、典型记录选择和图表报告。
- 插补、标准化和模型拟合均封装在 sklearn pipeline 内，避免测试集泄漏。

## 3. 监督预测模型

主特征集 `launch_state_model` 包含：

- `ball_speed_mph`
- `launch_angle_deg`
- `launch_direction_deg`
- `spin_rate_rpm`
- `spin_axis_deg`

扩展特征集 `full_shot_model` 额外包含：

- `club_speed_mph`
- `attack_angle_deg`

候选模型包括 Dummy、Linear、Ridge、ExtraTrees、HistGradientBoosting。每个目标独立选模，选择规则为训练集 CV RMSE 最低。

## 4. ODE 坐标与自旋

坐标定义：

- `x`：目标方向，向前为正
- `y`：横向方向，向右为正
- `z`：竖直方向，向上为正

初速度由球速、发射角和发射方向分解；ODE 内部统一使用 SI 单位。

自旋向量由 `spin_rate_rpm` 和 `spin_axis_deg` 构造。根据 `q2_spin_geometry_check.csv`，侧旋符号采用数据重构误差更小的符号；在当前坐标下，正后旋沿局部横向正轴，使 `u x omega` 产生向上升力。

## 5. ODE 层级

| 模型 | 力项 | 作用 |
|---|---|---|
| `vacuum` | 重力 | 验证初速度、单位换算和落地事件 |
| `drag` | 重力 + 二次阻力 | 建立阻力基线 |
| `constant_lift` | 重力 + 阻力 + 常数升力 | 直接估计 `C_D` 与 `C_L` |
| `spin_factor_lift` | 重力 + 阻力 + `C_L(S)=k_L S` | 比较自旋因子升力改进 |

参数用训练集代表样本粗网格标定。标定阶段采用 `max_step=0.05` 加速；最终测试集评估使用配置中的正式求解器参数。

## 6. 典型轨迹与灵敏度

典型记录只从固定测试集、ODE 必需字段完整的样本中选择，目标距离为 100/150/200 yd，选择规则为实际 carry 距目标最近且不按模型误差挑选。

灵敏度覆盖：

- 监督模型 30 次重复 70/30 划分稳定性。
- ODE 参数 `C_D`、`k_L` 的 ±10%、±20% 扰动。
- 积分器 `rtol`、`atol`、`max_step`、RK45/DOP853 对比。
- 小风速和自旋衰减假设对输出的影响。

## 7. 局限

常数升力模型在当前测试集上误差最低，但 ODE 仍使用全局常数参数、无完整风场、无精细自旋衰减和球面姿态模型。参数结果应解释为该数据与简化模型下的有效参数，不应外推为通用空气动力系数。
