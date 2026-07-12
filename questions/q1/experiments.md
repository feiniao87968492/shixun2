# q1 实验记录

## 实验矩阵

| 实验 ID | 日期 | 目标 | 数据版本 | 模型 / 配置 | 指标 | 结果 | 决策 |
|---|---|---|---|---|---|---|---|
| q1-E01 | 2026-07-12 | 缺失与异常审计 | `data/raw_manifest.csv` | pandas 数据审计 | 缺失率、范围、重复数 | 735 条记录；杆头速度缺失 63，攻击角缺失 65；输出字段无缺失 | supported |
| q1-E02 | 2026-07-12 | 输入输出相关性基线 | `data/processed/golf_shots_clean.csv` | Pearson/Spearman/Kendall | 相关系数、Bootstrap 区间 | 球速对飞行距离最稳定；Pearson=0.758，Spearman=0.776 | supported |
| q1-E03 | 2026-07-12 | 飞行距离重要性排序 | `data/processed/golf_shots_clean.csv` | 岭回归 + ExtraTrees 置换重要性 + 综合排名 | 综合得分、Top-3 频率、排名区间 | 前五为球速、杆头速度、攻击角、发射角、自旋轴偏角 | supported |
| q1-E04 | 2026-07-12 | 敏感性与分组重要性 | `data/processed/golf_shots_clean.csv` | S1/S2/S3、自旋表示、极端值处理、分组置换 | 排名相关、Top-k、RMSE 增量 | 速度组最强，发射姿态组次之，自旋组中等，水平方向组最弱 | supported |
| q1-E05 | 2026-07-12 | 图表与产物验证 | q1 artifacts | `questions/q1/scripts/validate.py` | 26 个 artifact checks | 全部通过 | supported |

## 失败实验

| 日期 | 实验 | 失败现象 | 根因 | 处理 |
|---|---|---|---|---|
| 2026-07-12 | 首次完整 pipeline | 图表阶段缺少 `pearson_score` 等列 | 聚合排序输出裁掉了可视化需要的 rank-normalized score 列 | 增加回归测试并保留 score 列后重跑成功 |

## 参数搜索

| 参数 | 搜索范围 | 方法 | 最终值 | 选择依据 |
|---|---|---|---|---|
| 缺失处理策略 | pairwise / 中位数插补 / 完整样本 | S1/S2/S3 对照 | 主模型使用中位数插补 + 缺失指示变量，完整样本作为敏感性分析 | 保留样本量，同时显式记录缺失影响 |
| 自旋表示 | 自旋速率+自旋轴偏角 / 后旋+侧旋 | 两套模型分别建模 | 主排序聚合两套表示的条件贡献，不在单个主模型中同时使用四个自旋变量 | 避免重复表达导致共线性 |
| Bootstrap 次数 | 500 | 配置固定 | 500 | 满足 task1 相关系数和排名不确定性要求 |
| 交叉验证 | 5 折 x 5 次 | RepeatedKFold | 25 个验证折 | 满足 task1 重复交叉验证要求 |
| 置换次数 | 每折 5 次 | 验证集置换 | 5 | 控制运行成本并给出稳定误差增量 |
