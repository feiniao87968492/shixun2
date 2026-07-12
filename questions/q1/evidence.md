# q1 证据链

| Claim ID | 主张 | 关键产物 | 验证 | 限制 | 状态 |
|---|---|---|---|---|---|
| Q1-C01 | 飞行距离关键因素应分层解释：球速为稳定首要因素，杆头速度为次要但与球速重叠，发射角为结构性非线性因素，攻击角不稳定 | `q1_feature_summary.csv`、`q1_ridge_coefficients.csv`、`q1_permutation_importance.csv`、`q1_group_importance.csv` | 1000 次 Bootstrap、5x5 CV、验证集置换重要性、62 项 validate 检查 | 观测数据不能支持因果解释 | supported |
| Q1-C02 | 杆头速度和攻击角存在 3 条异常零值，应修正为缺失并重新计算样本口径 | `q1_invalid_zero_records.csv`、`q1_data_audit.csv`、`q1_missing_audit.csv`、`q1_sample_definition_comparison.csv` | `record_id=225,226,308` 审计；修正后缺失 66/68；S1/S2/S3 对照 | 缺失机制未知；插补不能恢复真实测量 | supported |
| Q1-C03 | 杆头速度与球速存在信息重叠，不能把边际相关解释成完全独立贡献 | `q1_speed_overlap_models.csv`、`q1_correlation_confidence_intervals.csv` | 仅球速/仅杆头速度/两者同时模型 5x5 CV | 只说明预测信息重叠，不说明挥杆机制因果 | supported |
| Q1-C04 | 发射角存在非线性结构，二次项模型优于单线性项模型 | `q1_launch_angle_quadratic.csv`、`q1_top_feature_relationships.png` | 线性 vs 二次项 5x5 CV；经验最优角 17.89 度在观测范围内 | 样本内统计最优，不是全局物理最优 | supported |
