# q3 实验记录

## 实验矩阵

| 实验 ID | 日期 | 目标 | 数据版本 | 模型 / 配置 | 指标 | 结果 | 决策 |
|---|---|---|---|---|---|---|---|
| q3-E01 | 2026-07-13 | 依赖审计 | q2 task4 final | q2 carry/apex/ODE artifacts | 13 项依赖检查 | 全部通过 | adopt |
| q3-E02 | 2026-07-13 | lateral 代理模型 | q2 fixed split | Dummy/Linear/Ridge/HGB/ExtraTrees | train CV RMSE, test RMSE | HGB test RMSE=5.475 yd | adopt HGB |
| q3-E03 | 2026-07-13 | 支持区诊断 | q2 train only | kNN k=5, 95% LOO 阈值 | support_category | 最优点均 supported | adopt |
| q3-E04 | 2026-07-13 | 采样基线 | q2 final models | 20,000 点 LHS | best objective | top 100 保存 | adopt baseline |
| q3-E05 | 2026-07-13 | 主优化求解 | q2 final models | 5 seed DE + local LHS | objective_yd | 名义最优 0.010 yd | adopt |
| q3-E06 | 2026-07-13 | task5 单代理稳健推荐 | q2 final models | 2,000 次扰动/候选 | p90 miss | p90=3.135 yd，后续被 task6 取代 | superseded |
| q3-E07 | 2026-07-13 | 模型分歧 | q2 train bootstrap | 5 carry + 5 lateral ensembles | prediction std | 最优区 highly_model_sensitive | report risk |
| q3-E08 | 2026-07-13 | ODE 轨迹复核 | q2 final ODE | constant_lift + spin_factor_lift | integration_status, delta | 全部成功但有数 yd 差异 | crosscheck only |
| q3-E09 | 2026-07-13 | task6 RED 测试 | current q3 task5 | `tests/test_q3_final_robustness.py` | missing artifact/config checks | 5 项预期失败 | drive remediation |
| q3-E10 | 2026-07-13 | 稳健候选池扩展 | q3 top candidates | supported near-optimal pool | selected count | 482 个候选全部纳入 | adopt |
| q3-E11 | 2026-07-13 | 共同随机数和方向扰动 | q3 robust pool | ideal/stable_player/ordinary_player | p90 CI, support fraction | 3 场景均输出 p90/CI/support | adopt |
| q3-E12 | 2026-07-13 | 联合模型-参数稳健推荐 | q3 robust pool | paired 5 carry + 5 lateral members | stable_player joint p90 | 联合 p90=7.133 yd | final recommendation |
| q3-E13 | 2026-07-13 | 目标距离独立重优化 | q2 final models | LHS + 3 DE seeds + local refinement | objective_yd | 195/200/205 yd 均有 supported best | adopt |
| q3-E14 | 2026-07-13 | 近优非唯一性诊断 | q3 robust pool | parameter range summary | distinct counts, plateau | 482 参数组、256 落点组、最大平台 20 | report range |
| q3-E15 | 2026-07-14 | Q2/Q3 联合复现发布 | q2/q3 当前 artifacts | metadata SHA256 + release manifest + integration pytest | hash consistency / ODE crosscheck | q3 dependency audit=16 项；release manifest 已生成 | adopt |

## 失败与修正

| 现象 | 根因 | 修正 | 结果 |
|---|---|---|---|
| RED 测试 6 项失败 | q3 仍为 scaffold，缺 q3 config 和 task5 artifact | 添加 `tests/test_q3_task5_inverse_design.py` 后实现 q3 pipeline | 6 项 q3 task5 测试最终通过 |
| 首次 pipeline 在最终验证处失败 | `ode_verify.py` 将 q2 scripts 放到 `sys.path` 首位，导致 q3 pipeline 导入 q2 `validate.py` | q2 scripts 改为 append，避免遮蔽 q3 validator | q3 validation 通过 |
| 第二次 pipeline 超时 | SciPy DE 对 sklearn 代理模型逐点调用，单行预测开销过高 | 使用 `vectorized=True` 批量评价 DE population，并显式 `updating=deferred` | 完整 task5 pipeline 约 89 秒完成 |
| task6 RED 测试 5 项失败 | 缺方向扰动、完整稳健候选池、联合稳健表、目标重优化表和近优范围表 | 扩展 config、robustness、support、optimize、pipeline 和 validate | task6 validator 扩展至 31 项检查 |
| 稳健性明细首次导出约 941 MB | 全候选全模拟明细全部落盘，不适合版本管理和审阅 | 仅导出报告候选明细，汇总仍覆盖 482 个候选 | `q3_parameter_robustness.csv` 降至约 5.8 MB |

## 参数搜索结果

| 参数 | 搜索范围 | 名义最优 | 单代理参数稳健解 | 联合模型-参数稳健推荐 | 选择依据 |
|---|---:|---:|---:|---:|---|
| $v_0$ | 80-140 mph | 121.113 | 120.868 | 122.958 | stable_player 联合 p90 |
| $\theta_0$ | 5-30 degree | 19.616 | 18.978 | 20.437 | stable_player 联合 p90 |
| $\omega_0$ | 1000-10000 rpm | 2627.708 | 2344.294 | 2720.784 | stable_player 联合 p90 |
| $\alpha$ | -30 到 30 degree | -0.366 | 0.118 | -1.255 | stable_player 联合 p90 |

## 验证命令

```bash
python questions/q3/scripts/pipeline.py --config configs/default.yaml
python questions/q3/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_q3_integration.py -q
python -m pytest tests/test_q3_final_robustness.py -q
python -m pytest tests/test_q3_task5_inverse_design.py -q
```
