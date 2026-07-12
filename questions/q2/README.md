# q2 - 飞行轨迹预测

- 状态：`first_stage_done`
- 负责人：建模团队
- 依赖小问：q1 数据审计、清洗数据和变量口径
- 正式入口：`python questions/q2/scripts/pipeline.py --config configs/default.yaml`

## 任务目标

建立飞行距离和最高点高度监督预测模型，并逐步建立三维 ODE 轨迹模型。当前只完成第一阶段：固定 70%/30% 划分、监督模型、真空/仅阻力 ODE 和基础验证。

## 输入

- 数据：`data/processed/golf_shots_clean.csv`
- 上游结果：`q1_feature_summary.csv`、`q1_data_audit.csv`、`q1_invalid_zero_records.csv`
- 配置：`configs/default.yaml`
- 物理常数来源：题面 raw OCR 第 9 行；`docs/references.md`

## 输出

- 结果表：`questions/q2/artifacts/tables/`
- 图：`questions/q2/artifacts/figures/`
- 生图数据与元信息：`questions/q2/artifacts/figure_data/`
- 模型文件：`questions/q2/artifacts/models/q2_carry_model.joblib`、`q2_apex_model.joblib`

## 第一阶段完成项

- [x] q2 配置和 manifest 修正
- [x] 固定 70%/30% 数据划分并保存样本编号
- [x] Dummy、线性、Ridge、ExtraTrees、HistGradientBoosting 监督模型
- [x] 测试集 RMSE/MAPE/MAE/R2/MdAPE 和 Bootstrap 区间
- [x] 真空和仅阻力 ODE
- [x] mph/rpm/yd 单位换算与真空解析解验证
- [x] 图、表、生图数据、meta.json 和模型文件成对保存
- [ ] 含升力 ODE 和最终 `C_D/C_L` 标定
- [ ] 100/150/200 yd 典型轨迹与灵敏度分析
