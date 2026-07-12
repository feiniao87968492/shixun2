# q1 证据说明

本文件解释本小问关键主张的证据。机器可读索引仍以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q1-C01 | 飞行距离的关键关联因素可由相关性和模型重要性交叉验证得到 | `q1_feature_ranking.csv`、`q1_method_importance.csv`、`q1_group_importance.csv`、Pearson/Spearman 热力图 | Bootstrap 500 次、5x5 交叉验证置换重要性、S1/S2/S3 与自旋表示敏感性 | 观测数据不能支持因果解释；部分变量共线 | supported |
| Q1-C02 | 杆头速度和攻击角缺失会影响全字段模型口径 | `q1_missing_audit.csv`、`q1_data_audit.csv`、`q1_sensitivity_comparison.csv` | 缺失率审计、完整样本与插补样本对照、artifact 验证 | 缺失机制未知；插补不能恢复真实观测 | supported |
