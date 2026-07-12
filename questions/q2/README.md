# q2 — 飞行轨迹预测

- 状态：`planned`
- 负责人：建模团队
- 依赖小问：q1 数据审计与变量分析
- 正式入口：`python questions/q2/scripts/pipeline.py --config configs/default.yaml`

## 任务目标

建立飞行距离和最高点高度监督预测模型，并建立三维 ODE 轨迹模型完成典型击球记录误差分析。

## 输入

- 数据：`data/raw/problem/附件（实训题2）.xlsx`，后续使用 `data/processed/golf_shots_clean.csv`
- 上游结果：q1 变量口径、缺失处理和关键因素分析
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：监督模型 RMSE/MAPE、ODE 标定参数、典型记录相对误差。
- 结果表：`artifacts/tables/`
- 图：`artifacts/figures/`
- 生图数据：`artifacts/figure_data/`

## 完成条件

- [ ] 题意和数学目标明确
- [ ] 监督预测基线完成
- [ ] ODE 模型完成
- [ ] 验证与诊断完成
- [ ] 灵敏度或不确定性分析完成
- [ ] 图表和数据成对保存
- [ ] 证据链更新
- [ ] `results.md` 完成
