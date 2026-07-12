# q1 — 影响落点的关键因素分析

- 状态：`done_review2`
- 负责人：建模团队
- 依赖小问：无
- 正式入口：`python questions/q1/scripts/pipeline.py --config configs/default.yaml`

## 任务目标

计算输入击球参数与输出飞行结果之间的关联强度，并给出飞行距离的关键影响因素排序。

## 输入

- 数据：`data/raw/problem/附件（实训题2）.xlsx`
- 上游结果：无
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：球速是唯一稳定首要因素；杆头速度边际相关较强但与球速信息重叠；发射角属于结构性非线性因素；攻击角不再写作稳定关键因素，而是独立贡献有限且不稳定。
- 数据清洗变化：`record_id=225,226,308` 的杆头速度和攻击角异常 0 值已修正为缺失，修正后缺失数为 66/68。
- 结果表：`artifacts/tables/`
- 图：`artifacts/figures/`
- 生图数据：`artifacts/figure_data/`
- 运行元数据：`artifacts/run_metadata.json`

## 关键产物

- `q1_feature_summary.csv`：边际关联、条件线性贡献、非线性贡献和稳定性分类。
- `q1_invalid_zero_records.csv`：异常零值修正记录。
- `q1_speed_overlap_models.csv`、`q1_speed_overlap_fold_scores.csv`：球速/杆头速度同样本配对 CV 信息重叠对照。
- `q1_launch_angle_quadratic.csv`：发射角线性与二次项模型对照。
- `q1_raw_importance_comparison.png`、`q1_group_importance.png`、`q1_sensitivity_comparison.png`：review1/review2 图表。

## 完成条件

- [x] 题意和数学目标明确
- [x] 基线完成
- [x] 主分析完成
- [x] 验证与诊断完成
- [x] 灵敏度或不确定性分析完成
- [x] 图表和数据成对保存
- [x] 证据链更新
- [x] `results.md` 完成
