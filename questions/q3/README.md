# q3 — 最优击球策略

- 状态：`done`
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

## 主结果

- q2 依赖审计全部通过：固定划分 train=514、test=221，q2 carry/apex 模型、ODE 参数、q2 validation 和特征顺序均可追溯。
- 横向偏移代理模型由 `hist_gradient_boosting` 胜出，测试 RMSE=5.475 yd，MAE=3.870 yd，R2=0.958。
- 最佳观测训练记录为 `record_id=609`，实测距洞口 5.351 yd。
- 名义最优：球速 121.113 mph、发射角 19.616 度、自旋速率 2627.708 rpm、自旋轴偏角 -0.366 度，监督目标函数 0.010 yd。
- 稳健推荐：球速 120.751 mph、发射角 19.482 度、自旋速率 2348.781 rpm、自旋轴偏角 0.450 度，监督目标函数 0.022 yd，扰动 p90 距洞 3.135 yd。
- ODE 复核均积分成功；但监督模型和简化 ODE 对最优区存在数 yd 级差异，因此只作为物理轨迹交叉检查，不作为真实击球验证。

## 完成条件

- [x] 题意和数学目标明确
- [x] 优化基线完成
- [x] 主优化模型完成
- [x] 验证与诊断完成
- [x] 灵敏度或不确定性分析完成
- [x] 图表和数据成对保存
- [x] 证据链更新
- [x] `results.md` 完成
