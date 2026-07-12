# q1 — 影响落点的关键因素分析

- 状态：`done`
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

- 核心数值或决策：球速是最稳定关键因素；速度组重要性最高，发射姿态组次之，自旋状态组中等，水平方向组最弱。
- 结果表：`artifacts/tables/`
- 图：`artifacts/figures/`
- 生图数据：`artifacts/figure_data/`

## 完成条件

- [x] 题意和数学目标明确
- [x] 基线完成
- [x] 主分析完成
- [x] 验证与诊断完成
- [x] 灵敏度或不确定性分析完成
- [x] 图表和数据成对保存
- [x] 证据链更新
- [x] `results.md` 完成
