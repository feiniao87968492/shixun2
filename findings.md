# Findings & Decisions

## Requirements
- 完成 `docs/plans/task1.md` 第一问计划。
- 生成 q1 数据审计、缺失审计、异常标记和 processed 数据。
- 生成 Pearson/Spearman/Kendall 相关性、相关系数 Bootstrap 区间。
- 生成岭回归、非线性置换重要性、综合排序、排名稳定性、敏感性比较和分组重要性。
- 生成 5 张图，且每张图必须有同名 CSV 和 `.meta.json`。
- 更新 q1 文档、证据链、图表登记表、论文草稿和开发日志。

## Research Findings
- 当前目录：`D:\Users\zty\数学建模\赛题集\实训2`。
- `docs/plans/task1.md` 要求第一问分为相关性分析和飞行距离影响因素排序两个子任务。
- 实际 Excel 读取结果为 735 条记录；`高尔夫球实测数据` 工作表第 3 行为表头。
- 原始缺失情况：`杆头速度(mph)` 缺失 63 条，`攻击角(度)` 缺失 65 条，其余核心字段未发现原始缺失。
- review1 修正后缺失情况：`record_id=225,226,308` 的杆头速度和攻击角异常 0 值修正为缺失，修正后缺失数为 66/68。
- q1 review1 结果：球速是飞行距离最稳定关键因素，Pearson=0.758，Spearman=0.776，Bootstrap 排名区间 1-1。
- q1 初版“单一综合排序前五：球速、杆头速度、攻击角、发射角、自旋轴偏角”已被 review1 废弃；当前以 `q1_feature_summary.csv` 的分层分类为准。
- q1 分组重要性：速度组第一，发射姿态组第二，自旋状态组中等，水平方向组最弱；review2 后使用 5x5 CV + block permutation。
- q1 artifact 验证：`python questions/q1/scripts/validate.py --config configs/default.yaml` 通过 71 项 artifact/schema/numeric/reproducibility/method-invariant 检查。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| q1 分析核心放在 `questions/q1/scripts/analysis.py` | 第一问逻辑较专用，避免过早抽象；q2/q3 复用 `data/processed/golf_shots_clean.csv` |
| 使用 S1/S2/S3 三种样本口径 | 满足 task1 对缺失处理稳定性比较的要求 |
| 使用两套自旋表示分别建模 | 避免自旋变量重复表达和共线性 |
| 使用 ExtraTrees + 验证集置换重要性 | 捕捉非线性贡献且避免使用树模型纯度重要性 |
| 主结论表述为“统计关联/预测信息” | 避免相关性被误写成因果 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| q1 pipeline 首次运行在图表阶段缺少 score 列 | 增加回归测试并修复 `aggregate_rankings` 输出契约 |
| PowerShell `python -c` 嵌入换行触发 SyntaxError | 改为单行 Python 表达式 |

## Resources
- q1 plan: `docs/plans/task1.md`
- q1 analysis: `questions/q1/scripts/analysis.py`
- q1 final summary: `questions/q1/artifacts/tables/q1_feature_summary.csv`
- q1 legacy equal-weight ranking: `questions/q1/artifacts/tables/q1_feature_ranking.csv`，已标记 `deprecated` 和 `not_for_final_conclusion`
- q1 validation checks: `questions/q1/artifacts/tables/q1_validation_checks.csv`
- q1 paper draft: `report/paper.md`

## Visual/Browser Findings
- q1 生成的 Pearson/Spearman 热力图、前四变量关系图、多方法重要性图和排名稳定性图均非空且可读。

## Review1 Findings
- `questions/q1/review1.md` 的完成标准要求正式入口可重跑全部结果、异常零值修正、S1/S2/S3 样本口径、自旋 A/B 表示比较、Bootstrap 置信区间、岭回归 CV、验证集置换重要性、分组重要性、稳定性/敏感性、真实数值验证、同种子可复现、图表数据/配置/元数据完整、文档与 CSV 一致、README 同步且无未实现占位。
- 当前 review1 口径下，`record_id=225,226,308` 的杆头速度和攻击角异常 0 值已修正为缺失；杆头速度缺失数从 63 变为 66，攻击角缺失数从 65 变为 68。
- `q1_feature_summary.csv` 是最终解释主表：球速为 `stable_key`，杆头速度为 `secondary`，发射角和后旋为 `structural_nonlinear`，攻击角为 `unstable`，不再写作稳定关键因素。
- 修正后核心结果：球速与飞行距离 Pearson=0.758、Spearman=0.776；杆头速度 Pearson=0.581、Spearman=0.589；攻击角 Pearson=0.156、Spearman=0.206。
- 验证升级为 62 项 artifact/schema/numeric/reproducibility 检查；新增 `tests/test_q1_review1.py` 覆盖异常零值、review1 表、分层结论和 standalone 绘图入口依赖。
- `visualize.py` standalone 入口此前只加载旧 4 张表，已补齐 `q1_feature_summary`、`q1_group_importance`、`q1_sensitivity_comparison`，与 `create_visualizations` 的 review1 图表依赖一致。

## Review2 Findings
- `questions/q1/review2.md` 判定第一问主体通过但不能最终定稿，P0 问题为：S3 插补敏感性样本错标、速度重叠实验样本不一致、分组重要性未做重复 CV 且组内联合结构被破坏、排名稳定性字段容易误导为综合稳定性。
- P1 问题为：Ridge `ridge_coef_std=0` 只是单次拟合副产物，旧等权 `q1_feature_ranking.csv` 与新 `q1_feature_summary.csv` 冲突，自旋方案选择需强调 A 是物理解释主表而非纯预测最优，联合 1% 截断混入缺失删除。
- 新增 `tests/test_q1_review2.py` 作为 RED 测试，旧产物上 8 项全部失败，覆盖 review2 的核心方法不变量。
- 选定整改策略：S3 敏感性保留为明确标记的描述性中位数插补边际排名；正式模型仍使用交叉验证训练折内插补。
- 速度重叠实验统一到 `ball_speed_mph`、`club_speed_mph`、`carry_distance_yd` 同时非缺失的 669 条样本，并输出 `q1_speed_overlap_fold_scores.csv` 支持配对 fold 比较。
- 分组重要性改为 5x5 CV，组置换使用同一个行索引整体打乱组内列，保留组内联合关系。
- Bootstrap 排名稳定性只保留 `marginal_*` 字段和 `stability_scope=marginal_correlation_bootstrap`，避免误解为综合稳定性。
- 当前 review2 口径下，速度重叠实验在同一 669 条样本和相同 25 个 CV 折上比较；仅球速 RMSE=24.43，同时加入杆头速度 RMSE=24.42，额外信息很小。
- Ridge 系数改为 25 个训练折重复估计，`ridge_coef_std` 和正/负方向频率均来自实际重复估计。
- `validate.py` 增至 71 项检查，新增 S3 样本口径、速度重叠配对折、分组重复 CV/block permutation、边际稳定性字段、Ridge 重复估计和旧排名弃用检查。
