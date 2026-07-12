# q2 实验记录

## 实验矩阵

| 实验 ID | 日期 | 目标 | 数据版本 | 模型 / 配置 | 指标 | 结果 | 决策 |
|---|---|---|---|---|---|---|---|
| q2-E01 | 2026-07-12 | 固定划分与监督预测 | `data/processed/golf_shots_clean.csv` | Dummy、Linear、Ridge、ExtraTrees、HistGradientBoosting；`random_seed=2026` | CV RMSE、测试 RMSE/MAPE/MAE/R2/MdAPE | carry 最优为 launch_state / HistGradientBoosting，RMSE=8.337 yd；apex 最优为 launch_state / HistGradientBoosting，RMSE=1.739 yd | 支持 Q2-C01 |
| q2-E02 | 2026-07-12 | 真空和仅阻力 ODE 第一阶段 | 同上固定划分 | `solve_ivp(DOP853)`；`C_D` 粗网格 `[0.05, 0.60]` | carry/apex RMSE、failure rate、解析解误差 | 真空解析解校验通过；drag-only `C_D=0.05` 位于下界且测试误差未优于 vacuum | 只作为物理基线，不宣称最终参数 |
| q2-E03 | 2026-07-12 | artifact 验证 | 生成产物 | `questions/q2/scripts/validate.py` | 45 项表格/图/模型/schema/numeric 检查 | 全部通过 | 可以提交第一阶段 |
| q2-E04 | planned | 含升力 ODE 标定 | 待定 | `C_D/C_L` 或自旋因子升力模型 | 典型轨迹误差、参数可识别性、灵敏度 | 未运行 | 下一阶段 |

## 参数搜索

| 参数 | 搜索范围 | 方法 | 当前值 | 选择依据 |
|---|---|---|---:|---|
| 监督模型 | 5 个模型 x 2 套特征 x 2 个目标 | 训练集 5 折 CV | 见 `q2_supervised_metrics.csv` | 每个目标选择最低 CV RMSE |
| `C_D` | `[0.05, 0.60]` | 36 条训练代表样本的一维粗网格 | 0.05 | 第一阶段 drag-only objective 最小；位于下界，需后续复核 |
| `C_L` | 待定 | 未运行 | 未确定 | 第一阶段明确不宣称 |

## 失败或未完成实验

- drag-only ODE 没有在测试集优于 vacuum；这不是代码失败，而是模型结构和参数边界需要下一阶段复核的证据。
- 尚未实现含升力 ODE、典型 100/150/200 yd 轨迹、ODE 灵敏度和重复划分稳定性。
