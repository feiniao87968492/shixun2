# q3 — 最优击球策略

- 状态：`planned`
- 负责人：建模团队
- 依赖小问：q2 监督预测模型或 ODE 模型
- 正式入口：`python questions/q3/scripts/pipeline.py --config configs/default.yaml`

## 任务目标

在给定击球参数边界内，求解 200 yd 目标下使落点到洞口欧氏距离最小的最优击球参数组合。

## 输入

- 数据：q2 模型产物和 `data/processed/golf_shots_clean.csv`
- 上游结果：q2 预测模型、ODE 参数、单位换算规则
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：最优球速、发射角、自旋速率、自旋轴偏角、预测飞行距离、横向偏移和目标函数值。
- 结果表：`artifacts/tables/`
- 图：`artifacts/figures/`
- 生图数据：`artifacts/figure_data/`

## 完成条件

- [ ] 题意和数学目标明确
- [ ] 优化基线完成
- [ ] 主优化模型完成
- [ ] 验证与诊断完成
- [ ] 灵敏度或不确定性分析完成
- [ ] 图表和数据成对保存
- [ ] 证据链更新
- [ ] `results.md` 完成
