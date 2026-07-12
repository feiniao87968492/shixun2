# Development Log

## 使用规则

仅记录有决策价值的工作节点。每次记录包含目标、发现、决策、产物、未解决问题和下一步。

---

## 2026-07-12 — 仓库初始化与前期问题拆分

- **目标**：建立 2026年实训题2 高尔夫球飞行轨迹预测与最优击球策略建模 的可复现建模仓库，并完成题目接收阶段的拆解文档。
- **完成**：
  - 使用 `math-modeling-repo-init` 模板生成标准仓库结构、q1-q3 文档与脚本骨架。
  - 将题面 PDF、OCR Markdown 和 Excel 附件复制到 `data/raw/problem/`。
  - 生成 `data/raw_manifest.csv`，记录 3 个 raw 文件的 SHA-256。
  - 完成 `docs/problem_statement.md`、`docs/symbols.md`、`docs/assumptions.md`、`docs/data_dictionary.md`、`docs/project_plan.md`。
  - 完成 q1-q3 `approach.md`、计划结果、manifest、证据链和图表登记表。
- **关键发现**：
  - 题面共有 3 个主问题：q1 相关性与排序，q2 监督预测与 ODE 轨迹，q3 200 yd 最优击球策略。
  - Excel `高尔夫球实测数据` 工作表第 3 行为字段名，读取后共有 735 条记录。
  - `杆头速度(mph)` 缺失 63 条，`攻击角(度)` 缺失 65 条；其余核心输入和输出字段无缺失。
  - OCR 题面中附件说明“约 30 条有效记录”与实际 Excel 735 条记录不一致，后续以 Excel 实际数据为准，并在论文中谨慎表述数据规模。
- **决策**：
  - 当前目录作为仓库根目录。
  - 原始资料复制归档而不移动原目录；原目录加入 `.gitignore`，raw data 也按模板默认不入 Git。
  - q3 主目标使用首次落点飞行距离与横向偏移到 200 yd 洞口的欧氏距离。
- **产物**：
  - 标准仓库结构、项目级文档、q1-q3 方案文档、raw manifest。
- **未解决问题**：
  - 尚未实现数据清洗脚本和 q1-q3 流水线。
  - 尚未验证 ODE 常数 $C_D,C_L$ 假设是否足够。
  - 尚未生成任何 `supported` 证据链主张。
- **下一步**：
  - 实现 `src/modeling_common/data.py` 和 q1 数据审计/相关性流水线。
  - 运行 q1 基线后更新证据链、图表登记表和结果文档。

---

## 2026-07-12 — q1 相关性分析与因素排序完成

- **目标**：完成 `docs/plans/task1.md` 中第一问计划，形成可复现的 q1 数据审计、相关性、重要性排序、敏感性分析和图表产物。
- **完成**：
  - 新增 `questions/q1/scripts/analysis.py`，实现 raw Excel 读取、清洗、S1/S2/S3 样本口径、两套自旋表示、相关性、Bootstrap、岭回归、ExtraTrees 置换重要性、综合排序、分组重要性和图表生成。
  - 接通 `questions/q1/scripts/pipeline.py`、`validate.py`、`visualize.py`。
  - 生成 `data/processed/golf_shots_clean.csv`。
  - 生成 q1 表格：数据审计、缺失审计、异常标记、Pearson/Spearman/Kendall 相关性、相关系数置信区间、方法重要性、综合排序、分组重要性、敏感性比较、排名稳定性。
  - 生成 q1 图：Pearson/Spearman 热力图、前四变量关系图、多方法重要性对比图、排名稳定性图；每张图均有同名 CSV 和 meta.json。
  - 更新 q1 `README.md`、`manifest.yaml`、`results.md`、`experiments.md`、`evidence.md`、`docs/evidence_chain.csv` 和 `docs/figure_table_registry.csv`。
- **关键发现**：
  - 球速是最稳定关键因素，Pearson=0.758，Spearman=0.776，Bootstrap 排名区间 1-1。
  - 综合前五为球速、杆头速度、攻击角、发射角、自旋轴偏角。
  - 分组重要性排序为速度组、发射姿态组、自旋状态组、水平方向组。
  - 杆头速度和攻击角有 63/65 条缺失，必须保留口径说明。
- **决策**：
  - 主结论表述为统计关联和预测信息，不写成因果结论。
  - 主排序聚合两套自旋表示的条件贡献，但单个主模型中不同时使用四个自旋变量。
- **产物**：
  - `questions/q1/artifacts/tables/q1_feature_ranking.csv`
  - `questions/q1/artifacts/tables/q1_group_importance.csv`
  - `questions/q1/artifacts/figures/q1_pearson_heatmap.png`
  - `questions/q1/artifacts/figures/q1_importance_comparison.png`
  - `questions/q1/artifacts/figures/q1_rank_stability.png`
- **未解决问题**：
  - q2 尚未基于 q1 清洗数据实现监督预测和 ODE 建模。
  - q3 尚未实现最优击球策略。
- **下一步**：
  - 进入 q2：基于 `data/processed/golf_shots_clean.csv` 建立飞行距离和最高点高度预测模型。
