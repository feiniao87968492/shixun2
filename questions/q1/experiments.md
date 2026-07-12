# q1 实验记录

## 实验矩阵

| 实验 ID | 日期 | Git commit | 数据版本 | 配置 | 样本口径 | 自旋表示 | 模型 | 主要指标 | 结论 | 是否保留 |
|---|---|---|---|---|---|---|---|---|---|---|
| q1-E01 | 2026-07-12 | `aa71df4` 前 | `data/raw_manifest.csv` | `configs/default.yaml` | raw | 全变量展示 | pandas 审计 | 缺失率、范围、重复数 | 初版发现杆头速度缺失 63、攻击角缺失 65，但未修正异常零值 | superseded |
| q1-E02 | 2026-07-12 | current | `data/raw_manifest.csv` | `configs/default.yaml` | corrected raw | 全变量展示 | `preprocessing.py` | 异常零值数、修正后缺失数 | `record_id=225,226,308` 的杆头速度和攻击角 0 值修正为 NaN；修正后缺失 66/68 | supported |
| q1-E03 | 2026-07-12 | current | `data/processed/golf_shots_clean.csv` | `q1.bootstrap.iterations=1000` | pairwise | 全变量展示 | Pearson/Spearman/Kendall + Bootstrap | 相关系数、95% CI、有效 n | 球速 Pearson=0.758；杆头速度 Pearson=0.581；攻击角仅弱正相关 | supported |
| q1-E04 | 2026-07-12 | current | `data/processed/golf_shots_clean.csv` | 5x5 CV | S3 | A/B 分开 | 岭回归 + ExtraTrees 验证集置换 | RMSE、MAE、R²、置换 RMSE 增量 | 球速三类证据均最强；发射角呈结构性非线性贡献；攻击角独立贡献弱 | supported |
| q1-E05 | 2026-07-12 | current | `data/processed/golf_shots_clean.csv` | 5x5 CV | S3 | A/B 比较 | 自旋表示对照 | CV RMSE/MAE/R² | B（后旋+侧旋）RMSE=8.23，A（自旋率+轴角）RMSE=8.48；A 为主解释，B 为敏感性 | supported |
| q1-E06 | 2026-07-12 | current | `data/processed/golf_shots_clean.csv` | 5x5 CV | 完整可用样本 | 不适用 | 球速/杆头速度重叠模型 | RMSE、MAE、R² | 仅球速 RMSE=24.32，仅杆头速度 30.34，两者同时 24.42；杆头速度与球速信息重叠明显 | supported |
| q1-E07 | 2026-07-12 | current | `data/processed/golf_shots_clean.csv` | 5x5 CV | 735 条 | 不适用 | 发射角线性 vs 二次项 | RMSE、经验最优角 | 二次项 RMSE=34.64，优于线性 RMSE=37.24；经验最优发射角约 17.89 度 | supported |
| q1-E08 | 2026-07-12 | current | q1 artifacts | `configs/default.yaml` | 全部 | 全部 | `validate.py` | 62 项检查 | 文件、schema、数值范围、异常零值、元数据、表哈希均通过 | supported |

## 失败与修正

| 日期 | 实验 | 失败现象 | 根因 | 处理 |
|---|---|---|---|---|
| 2026-07-12 | 初版 q1 pipeline | 图表阶段缺少 `pearson_score` 等列 | 聚合排序输出裁掉了可视化需要的 score 列 | 增加回归测试并保留兼容字段 |
| 2026-07-12 | review1 审计 | 异常零值未被修正，攻击角被写为稳定关键因素 | 初版只做文件存在验证，综合排名重复加权边际相关 | 新增 `preprocessing.py`、分层 `q1_feature_summary.csv` 和真实数值验证 |
| 2026-07-12 | artifact 复跑 | CSV 浮点和 CRLF 导致无意义 diff | 默认 CSV/JSON 写出不稳定 | 固定 12 位有效数字和 LF 换行 |

## 参数

| 参数 | 当前值 | 来源 |
|---|---|---|
| 随机种子 | 2026 | `configs/default.yaml:q1.random_seed` |
| Bootstrap 次数 | 1000 | `configs/default.yaml:q1.bootstrap.iterations` |
| 交叉验证 | 5 折 x 5 次 | `configs/default.yaml:q1.cross_validation` |
| 置换重复次数 | 10 | `configs/default.yaml:q1.permutation_importance.repeats` |
| 非线性模型 | ExtraTreesRegressor, 120 trees, min leaf 3 | `configs/default.yaml:q1.nonlinear_model` |
| 异常零值规则 | 仅 `club_speed_mph` 和 `attack_angle_deg` 的 0 值 | `questions/q1/scripts/preprocessing.py` |
