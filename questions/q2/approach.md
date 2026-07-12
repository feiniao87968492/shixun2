# q2 解法方案：飞行轨迹预测

## 1. 题意解释

第二问要求预测飞行距离和最高点高度，并建立三维轨迹模型。当前阶段先完成可复现的基础层：

- 监督预测：按 70%/30% 固定划分训练集和测试集，报告 RMSE、MAPE、MAE、R2、MdAPE。
- 物理模型：实现真空抛体和仅阻力 ODE，完成单位换算、落地事件和真空解析解验证。
- 暂不宣称：最终 `C_D`、`C_L`、含升力轨迹、100/150/200 yd 典型轨迹和灵敏度分析。

## 2. 输入、输出和单位

输入数据为 q1 清洗后的 `data/processed/golf_shots_clean.csv`。Q2 在加载层把 q1 的 `max_height_yd` 显式映射为本题术语 `apex_height_yd`，不修改 q1 产物。

监督模型特征集：

| 特征集 | 字段 | 用途 |
|---|---|---|
| `launch_state_model` | `ball_speed_mph`、`launch_angle_deg`、`launch_direction_deg`、`spin_rate_rpm`、`spin_axis_deg` | 主模型；与 ODE 初始状态一致 |
| `full_shot_model` | launch state + `club_speed_mph`、`attack_angle_deg` | 精度对照；缺失值只在训练流水线内部插补 |

目标变量：

- `carry_distance_yd`
- `apex_height_yd`

ODE 内部统一使用 SI 单位：m、s、kg、rad；输出再换算回 yd。

## 3. 固定划分与防泄漏规则

使用 `random_seed=2026` 和 `test_size=0.30` 建立主划分，保存到 `q2_data_split.csv`。当前样本数为 train=514、test=221。

规则：

- 超参数和模型选择只使用训练集 5 折交叉验证。
- 测试集只用于最终指标报告和图表诊断。
- 插补、标准化、模型拟合均封装在 sklearn pipeline 内，避免测试集泄漏。
- 所有监督模型和 ODE 测试评估使用同一主划分。

## 4. 监督预测模型

候选模型：

- `DummyRegressor(strategy="mean")`
- `LinearRegression`
- `RidgeCV`
- `ExtraTreesRegressor`
- `HistGradientBoostingRegressor`

每个目标分别在两套特征集上比较候选模型，以训练集 CV RMSE 最低者作为选中模型。测试集输出 RMSE、MAPE、MAE、R2、MdAPE，并用 1000 次测试集 bootstrap 给出 RMSE/MAPE/MAE 区间。

## 5. ODE 第一阶段

坐标定义：

- `x`：目标方向，向前为正；
- `y`：横向方向，向右为正；
- `z`：竖直方向，向上为正。

初速度由球速、发射角和发射方向分解：

```text
v_x(0)=v0 cos(theta) cos(phi)
v_y(0)=v0 cos(theta) sin(phi)
v_z(0)=v0 sin(theta)
```

第一阶段模型：

| 模型 | 力项 | 目的 |
|---|---|---|
| vacuum | 重力 | 校验单位、初速度分解、落地事件和解析解 |
| drag | 重力 + 二次阻力 | 建立阻力接口和参数扫描基线 |

仅阻力模型使用一维粗网格扫描 `C_D in [0.05, 0.60]`。当前得到 `C_D=0.05` 且位于下界，因此只登记为 `preliminary_drag_only`，后续必须进入含升力和参数可识别性检查后才能形成最终物理结论。

## 6. 产物

| 产物 | 路径 |
|---|---|
| 数据划分 | `questions/q2/artifacts/tables/q2_data_split.csv` |
| 监督模型指标 | `questions/q2/artifacts/tables/q2_supervised_metrics.csv` |
| 监督预测明细 | `questions/q2/artifacts/tables/q2_supervised_predictions.csv` |
| ODE 参数 | `questions/q2/artifacts/tables/q2_ode_parameters.csv` |
| ODE 测试指标 | `questions/q2/artifacts/tables/q2_ode_test_metrics.csv` |
| ODE 验证检查 | `questions/q2/artifacts/tables/q2_ode_validation_checks.csv` |
| 图表 | `questions/q2/artifacts/figures/` |
| 生图数据和 meta | `questions/q2/artifacts/figure_data/` |
| 模型文件 | `questions/q2/artifacts/models/` |

## 7. 后续工作

下一阶段需要完成：

- 含升力 ODE；
- `C_D/C_L` 或自旋因子升力参数标定；
- 参数曲面和边界复核；
- 100/150/200 yd 典型轨迹；
- 监督模型重复划分稳定性和 ODE 灵敏度分析。
