# q1 — 影响落点的关键因素分析

- 状态：`planned`
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

- 核心数值或决策：相关性矩阵、飞行距离影响因素排序、缺失字段影响说明。
- 结果表：`artifacts/tables/`
- 图：`artifacts/figures/`
- 生图数据：`artifacts/figure_data/`

## 完成条件

- [ ] 题意和数学目标明确
- [ ] 基线完成
- [ ] 主分析完成
- [ ] 验证与诊断完成
- [ ] 灵敏度或不确定性分析完成
- [ ] 图表和数据成对保存
- [ ] 证据链更新
- [ ] `results.md` 完成
