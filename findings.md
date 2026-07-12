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
- 缺失情况：`杆头速度(mph)` 缺失 63 条，`攻击角(度)` 缺失 65 条，其余核心字段未发现缺失。
- q1 pipeline 结果：球速是飞行距离最稳定关键因素，Pearson=0.758，Spearman=0.776，Bootstrap 排名区间 1-1。
- q1 综合排序前五：球速、杆头速度、攻击角、发射角、自旋轴偏角。
- q1 分组重要性：速度组第一，发射姿态组第二，自旋状态组中等，水平方向组最弱。
- q1 artifact 验证：`python questions/q1/scripts/validate.py` 通过 26 个检查。

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
- q1 ranking: `questions/q1/artifacts/tables/q1_feature_ranking.csv`
- q1 validation checks: `questions/q1/artifacts/tables/q1_validation_checks.csv`
- q1 paper draft: `report/paper.md`

## Visual/Browser Findings
- q1 生成的 Pearson/Spearman 热力图、前四变量关系图、多方法重要性图和排名稳定性图均非空且可读。
