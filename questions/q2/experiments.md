# q2 实验记录

| 实验 ID | 日期 | 目标 | 方法 | 指标 | 结果 | 状态 |
|---|---|---|---|---|---|---|
| q2-E01 | 2026-07-12 | 固定划分与监督预测 | Dummy/Linear/Ridge/ExtraTrees/HistGradientBoosting；训练 CV 选模 | RMSE/MAPE/MAE/R2/MdAPE | carry RMSE=8.337 yd；apex RMSE=1.739 yd | supported |
| q2-E02 | 2026-07-12 | 真空和仅阻力 ODE | `solve_ivp(DOP853)`；训练代表样本标定 | carry/apex RMSE；failure rate；解析解误差 | vacuum/drag 均无积分失败；drag `C_D=0.05` 位于下界 | supported |
| q2-E03 | 2026-07-12 | 含升力 ODE 标定 | 训练集代表样本 2D 粗网格 | objective；测试 RMSE | constant_lift `C_D=0.27,C_L=0.18`；spin_factor_lift `C_D=0.27,k_L=0.8` | supported |
| q2-E04 | 2026-07-12 | ODE 测试集比较 | 固定测试集 221 条 | carry/apex RMSE；lateral MAE；failure rate | constant_lift carry RMSE=16.506 yd，优于 vacuum/drag/spin_factor | supported |
| q2-E05 | 2026-07-12 | 典型轨迹 | 测试集按实际 carry 近 100/150/200 yd 选择 | 典型误差；3D/side/top 轨迹 | sample_id=683/713/623；轨迹图和轨迹点已保存 | supported |
| q2-E06 | 2026-07-12 | 灵敏度分析 | 30 次重复划分；ODE 参数/积分/假设扰动 | 均值/标准差；输出 delta | 监督模型稳定性和 ODE 敏感性表已生成 | supported |
| q2-E07 | 2026-07-12 | artifact 验证 | `questions/q2/scripts/validate.py` | 自动检查项 | 69 项检查通过 | supported |

## 参数边界说明

`drag` 的 `C_D=0.05` 位于下界，不能单独解释为真实阻力系数。含升力模型使用训练代表样本粗网格标定，参数应解释为当前简化 ODE 的有效参数。
