# q3 实验记录

## 实验矩阵

| 实验 ID | 日期 | 目标 | 数据版本 | 模型 / 配置 | 指标 | 结果 | 决策 |
|---|---|---|---|---|---|---|---|
| q3-E01 | 2026-07-13 | 依赖审计 | q2 task4 final | q2 carry/apex/ODE artifacts | 13 项依赖检查 | 全部通过 | adopt |
| q3-E02 | 2026-07-13 | lateral 代理模型 | q2 fixed split | Dummy/Linear/Ridge/HGB/ExtraTrees | train CV RMSE, test RMSE | HGB test RMSE=5.475 yd | adopt HGB |
| q3-E03 | 2026-07-13 | 支持区诊断 | q2 train only | kNN k=5, 95% LOO 阈值 | support_category | 最优点均 supported | adopt |
| q3-E04 | 2026-07-13 | 采样基线 | q2 final models | 20,000 点 LHS | best objective | top 100 保存 | adopt baseline |
| q3-E05 | 2026-07-13 | 主优化求解 | q2 final models | 5 seed differential_evolution + local LHS | objective_yd | 最优 0.010 yd | adopt |
| q3-E06 | 2026-07-13 | 稳健推荐 | q2 final models | 2,000 次扰动/候选 | p90 miss | 稳健推荐 p90=3.135 yd | adopt robust |
| q3-E07 | 2026-07-13 | 模型分歧 | q2 train bootstrap | 5 carry + 5 lateral ensembles | prediction std | 两个最优点 highly_model_sensitive | report risk |
| q3-E08 | 2026-07-13 | ODE 轨迹复核 | q2 final ODE | constant_lift + spin_factor_lift | integration_status, delta | 全部成功但有数 yd 差异 | crosscheck only |

## 失败与修正

| 现象 | 根因 | 修正 | 结果 |
|---|---|---|---|
| RED 测试 6 项失败 | q3 仍为 scaffold，缺 q3 config 和所有 task5 artifact | 添加 `tests/test_q3_task5_inverse_design.py` 后实现 q3 pipeline | 6 项 q3 task5 测试最终通过 |
| 首次 pipeline 在最终验证处失败 | `ode_verify.py` 将 q2 scripts 放到 `sys.path` 首位，导致 q3 pipeline 导入了 q2 `validate.py` | q2 scripts 改为 append，避免遮蔽 q3 validator | q3 validation 通过 |
| 第二次 pipeline 超时 | SciPy DE 对 sklearn 代理模型逐点调用，单行预测开销过高 | 使用 `vectorized=True` 批量评价 DE population，并显式 `updating=deferred` | 完整 pipeline 约 89 秒完成 |

## 参数搜索结果

| 参数 | 搜索范围 | 方法 | 名义最优 | 稳健推荐 | 选择依据 |
|---|---:|---|---:|---:|---|
| $v_0$ | 80-140 mph | LHS + 5 seed DE + local LHS | 121.113 | 120.751 | 目标函数与扰动 p90 |
| $\theta_0$ | 5-30 degree | LHS + 5 seed DE + local LHS | 19.616 | 19.482 | 目标函数与扰动 p90 |
| $\omega_0$ | 1000-10000 rpm | LHS + 5 seed DE + local LHS | 2627.708 | 2348.781 | 目标函数与扰动 p90 |
| $\alpha$ | -30 到 30 degree | LHS + 5 seed DE + local LHS | -0.366 | 0.450 | 目标函数与扰动 p90 |

## 验证命令

```bash
python questions/q3/scripts/pipeline.py --config configs/default.yaml
python questions/q3/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q3_task5_inverse_design.py -q
```
