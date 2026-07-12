# Development Log

## 使用规则

仅记录有决策价值的工作节点。每次记录包含目标、发现、决策、产物、未解决问题和下一步。

---

## 2026-07-12 - q2 第一阶段监督预测与 ODE 基线完成

- **目标**：完成 `docs/plans/task2.md` 第 26 节停止点，形成可复现的固定划分、监督预测模型、真空/仅阻力 ODE 和验证证据。
- **完成**：
  - 修正 `configs/default.yaml` 的 q2 配置和 `questions/q2/manifest.yaml` 上游依赖。
  - 新增 `questions/q2/scripts/preprocessing.py`、`supervised.py`、`ode_model.py`，并接入 `pipeline.py`、`validate.py`、`visualize.py`。
  - 保存固定 70/30 划分：train=514，test=221，随机种子 2026。
  - 比较 Dummy、Linear、Ridge、ExtraTrees、HistGradientBoosting 两套特征模型。
  - 实现真空和仅阻力 ODE，完成 mph/rpm/yd 单位换算、落地事件和真空解析解校验。
  - 生成 q2 表格、图、同名生图数据、meta.json、模型文件和运行元数据。
  - 更新 q2 文档、全局证据链、图表登记、README 和论文草稿。
- **关键发现**：
  - carry 最优监督模型为 `launch_state_model / hist_gradient_boosting`，测试 RMSE=8.337 yd，MAPE=4.986%。
  - apex 最优监督模型为 `launch_state_model / hist_gradient_boosting`，测试 RMSE=1.739 yd，MAPE=14.335%。
  - 真空数值解与解析解最大差异为 0.000456；ODE 测试样本积分失败率为 0。
  - drag-only 粗网格得到 `C_D=0.05`，但位于搜索下界且测试误差未优于 vacuum，因此只作为 `preliminary_drag_only`，不得宣称最终 `C_D/C_L`。
- **验证**：
  - `python questions\q2\scripts\pipeline.py --config configs/default.yaml` 通过。
  - `python questions\q2\scripts\validate.py --config configs/default.yaml` 通过 45 项检查。
  - `python -m pytest tests\test_q2_first_stage.py -q` 通过 4 项测试。
- **未解决问题**：
  - 含升力 ODE、最终 `C_D/C_L` 标定、100/150/200 yd 典型轨迹、重复划分稳定性和 ODE 灵敏度仍未完成。
- **下一步**：
  - 进入含升力模型和参数可识别性检查，再生成典型轨迹与 q3 可复用接口。

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
  - 旧口径综合前五为球速、杆头速度、攻击角、发射角、自旋轴偏角；该单一综合排序已由后续 review1 分层结论取代。
  - 分组重要性排序为速度组、发射姿态组、自旋状态组、水平方向组。
  - 初版仅记录杆头速度和攻击角 63/65 条原始缺失；后续 review1 已补充 3 条异常 0 值修正，修正后缺失为 66/68。
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

---

## 2026-07-12 — q1 review1 整改与复现审计完成

- **目标**：完成 `questions/q1/review1.md` 中第一问整改要求，使正式入口可重新生成全部结果，并让文档结论与 CSV 证据一致。
- **完成**：
  - 新增 `questions/q1/scripts/preprocessing.py`，将 `record_id=225,226,308` 的杆头速度和攻击角异常 0 值修正为缺失，其他字段的 0 不作泛化处理。
  - 重构 `questions/q1/scripts/analysis.py`，保留 S1/S2/S3 样本口径；S3 的中位数插补通过 sklearn pipeline 在交叉验证训练折内拟合，避免全局预插补泄漏。
  - 将飞行距离结论拆分为边际关联、条件线性贡献、非线性预测贡献和稳定性分类，不再使用单一四项等权综合排名作为最终解释。
  - 新增 `q1_invalid_zero_records.csv`、`q1_outlier_audit.csv`、`q1_model_performance.csv`、`q1_ridge_coefficients.csv`、`q1_permutation_importance.csv`、`q1_spin_representation_comparison.csv`、`q1_sample_definition_comparison.csv`、`q1_feature_summary.csv`、`q1_speed_overlap_models.csv` 和 `q1_launch_angle_quadratic.csv`。
  - 新增运行级元数据 `questions/q1/artifacts/run_metadata.json`，记录数据/config hash、随机种子、包版本、样本口径、异常零值修正和结果表 hash。
  - 更新 q1 文档、论文草稿、全局证据链和图表登记表；补充 review1 回归测试。
- **关键发现**：
  - 杆头速度原始缺失 63 条，异常 0 值 3 条，修正后缺失 66 条；攻击角原始缺失 65 条，异常 0 值 3 条，修正后缺失 68 条。
  - 球速与飞行距离 Pearson=0.758、Spearman=0.776，是稳定首要因素；杆头速度修正后 Pearson=0.581，但与球速存在信息重叠。
  - 发射角边际线性相关弱，但二次项模型和非线性置换重要性显示结构性贡献，经验最优发射角约 17.89 度。
  - 攻击角仅弱边际正相关，岭回归系数为负，置换重要性靠后，不再写为稳定关键因素。
- **决策**：
  - q1 最终解释以 `q1_feature_summary.csv` 为主表，`q1_feature_ranking.csv` 仅保留兼容旧图表和审计。
  - 自旋表示 A（自旋速率 + 自旋轴偏角）作为主解释，表示 B（后旋 + 侧旋）作为敏感性对照。
- **验证**：
  - `python questions\q1\scripts\pipeline.py --config configs/default.yaml` 可重新生成结果。
  - `python questions\q1\scripts\validate.py --config configs/default.yaml` 通过 62 项 artifact/schema/numeric/reproducibility 检查。
  - `python -m pytest tests\test_q1_review1.py tests\test_q1_analysis.py -q` 通过。
  - `python scripts\check_repo.py` 通过，仅保留 q2/q3 pipeline 未实现的预期 warning；`python scripts\snapshot_raw.py --verify` 通过。
- **产物**：
  - `questions/q1/artifacts/tables/q1_feature_summary.csv`
  - `questions/q1/artifacts/tables/q1_invalid_zero_records.csv`
  - `questions/q1/artifacts/tables/q1_permutation_importance.csv`
  - `questions/q1/artifacts/tables/q1_group_importance.csv`
  - `questions/q1/artifacts/run_metadata.json`
- **未解决问题**：
  - q2/q3 仍为后续小问，当前仓库检查会保留预期 scaffold warning。
- **下一步**：
  - 在 q2 开始前继续以 `data/processed/golf_shots_clean.csv` 和 q1 元数据作为共享数据入口。

---

## 2026-07-12 — q1 review2 方法审查整改

- **目标**：修复 `questions/q1/review2.md` 指出的 S3 样本口径、速度重叠实验、分组重要性、排名稳定性和旧排名文件冲突问题。
- **完成**：
  - 新增 `tests/test_q1_review2.py`，先在旧产物上确认 8 项方法不变量失败，再用实现修复转绿。
  - 将 S3 敏感性表改为明确标记的 `descriptive_imputed_marginal`，新增 `ranked_n`，避免 735 条报告样本与实际排名样本不一致。
  - 将球速/杆头速度重叠实验统一到 669 条共同非缺失样本和相同 25 个 CV 折，并新增 `q1_speed_overlap_fold_scores.csv`。
  - 将分组重要性改为 5x5 CV + block permutation，输出 `importance_std`、`positive_frequency`、`fold_count` 和 `permutation_repeats`。
  - 将边际相关 Bootstrap 排名稳定性字段统一为 `marginal_*`，并写入 `stability_scope=marginal_correlation_bootstrap`。
  - 将 Ridge 系数改为训练折重复估计，输出真实的系数标准差和正/负方向频率。
  - 标记旧 `q1_feature_ranking.csv` 为 `deprecated` 与 `not_for_final_conclusion`，最终解释以 `q1_feature_summary.csv` 为准。
  - 更新 q1 文档、论文草稿、证据链、图表登记表和 README 的 review2 口径。
- **关键发现**：
  - 同样本配对 CV 下，仅球速 RMSE=24.43 yd，同时加入杆头速度 RMSE=24.42 yd，杆头速度额外预测信息很小。
  - 分组重要性排序仍为速度组、发射姿态组、自旋状态组、水平方向组，但现在有重复 CV 标准差和正贡献频率支撑。
  - 自动验证检查从 62 项扩展到 71 项，新增 review2 方法不变量。
- **决策**：
  - `q1_rank_stability.csv` 只解释为边际相关排名稳定性，不作为综合方法稳定性。
  - 自旋表示 A 用于主解释，表示 B 作为纯预测略优的敏感性对照。
- **产物**：
  - `questions/q1/artifacts/tables/q1_speed_overlap_fold_scores.csv`
  - `questions/q1/artifacts/tables/q1_group_importance.csv`
  - `questions/q1/artifacts/tables/q1_rank_stability.csv`
  - `questions/q1/artifacts/tables/q1_validation_checks.csv`
- **未解决问题**：
  - q2/q3 仍为后续小问，当前仓库检查保留预期 scaffold warning。
- **下一步**：
  - 进入 q2 前以 review2 后的 q1 artifacts 和 `data/processed/golf_shots_clean.csv` 为共享入口。
