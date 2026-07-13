# 第三问最优击球策略建模执行任务书

## 1. 项目范围

项目仓库：

```text
https://github.com/feiniao87968492/shixun2
```

本次处理：

```text
questions/q3/
```

正式入口：

```bash
python questions/q3/scripts/pipeline.py \
  --config configs/default.yaml
```

建议将本文保存为：

```text
questions/q3/IMPLEMENTATION_TASK.md
```

---

# 2. 任务目标

假设洞口位于目标线前方 200 yd，寻找最优击球参数：

[
u=(v,\theta,\omega,\alpha)
]

其中：

* (v)：球速，mph；
* (\theta)：发射角，degree；
* (\omega)：自旋速率，rpm；
* (\alpha)：自旋轴偏角，degree。

发射方向固定为：

[
\phi=0^\circ
]

模型预测落地点：

[
P(u)=\left(D(u),L(u)\right)
]

其中：

* (D(u))：目标线方向飞行距离；
* (L(u))：横向偏移。

洞口坐标为：

[
P_{\mathrm{hole}}=(200,0)
]

名义目标函数为：

[
J_0(u)
======

\sqrt{
\left[D(u)-200\right]^2+
L(u)^2
}
]

求解：

[
u^*=\arg\min_{u\in\Omega}J_0(u)
]

最终必须输出：

* 最优球速；
* 最优发射角；
* 最优自旋速率；
* 最优自旋轴偏角；
* 预测前向飞行距离；
* 预测横向偏移；
* 距洞口距离；
* 预测最高点；
* 三维飞行轨迹；
* 参数扰动后的稳健性。

---

# 3. 当前必须修正的依赖

## 3.1 修正 manifest

当前 q3 manifest 中的：

```text
questions/q2/artifacts/models/q2_prediction_model.joblib
```

应替换为实际文件：

```text
questions/q2/artifacts/models/q2_carry_model.joblib
questions/q2/artifacts/models/q2_apex_model.joblib
questions/q2/artifacts/models/q2_ode_parameters.json
questions/q2/artifacts/run_metadata.json
questions/q2/artifacts/tables/q2_data_split.csv
questions/q2/artifacts/tables/q2_validation_checks.csv
```

第三问还需要：

```text
data/processed/golf_shots_clean.csv
```

---

## 3.2 建立依赖审计

生成：

```text
questions/q3/artifacts/tables/q3_dependency_audit.csv
```

至少检查：

| 检查项         | 要求              |
| ----------- | --------------- |
| q2 carry 模型 | 文件存在且可加载        |
| q2 apex 模型  | 文件存在且可加载        |
| q2 固定划分     | 存在且无训练测试重叠      |
| q2 元数据      | 可读取             |
| q2 验证       | 没有阻断性失败         |
| ODE 参数      | 文件存在、参数合法       |
| 输入数据        | 735 条记录、关键字段完整  |
| 特征顺序        | 与 q2 carry 模型一致 |

若 q2 ODE 仍未通过最终整改：

```text
q3_supervised_ready = true
q3_ode_verified = false
```

第三问可以完成监督优化，但状态只能设为：

```text
conditionally_passed
```

---

# 4. 建模架构

第三问采用三层结构。

## 第一层：监督主优化

使用：

```text
q2_carry_model.joblib
```

预测飞行距离。

第三问另外训练横向偏移模型：

[
\hat L=f_L(v,\theta,\phi,\omega,\alpha)
]

主优化器使用：

[
\hat J_0(u)
===========

\sqrt{
\left[\hat D(u)-200\right]^2+
\hat L(u)^2
}
]

这是第三问的主结果。

---

## 第二层：模型交叉验证

使用多个代理模型判断最优点是否依赖单一模型：

* q2 选中的 HistGradientBoosting carry 模型；
* ExtraTrees carry 备选模型；
* HistGradientBoosting lateral 模型；
* ExtraTrees lateral 备选模型。

对同一个候选参数分别计算预测结果。

若不同模型对最优点的预测差异过大，应将该点标记为：

```text
model_sensitive
```

---

## 第三层：ODE 物理复核

使用第二问 ODE：

* `constant_lift`：第二问拟合和轨迹展示模型；
* `spin_factor_lift`：自旋速率敏感性的探索模型。

ODE 不作为当前主优化器，除非第二问最终满足：

* 参数标定正常终止；
* carry 定义全流程一致；
* 完整训练集积分失败数为 0；
* 边界输入稳定性测试通过。

---

# 5. 数据划分和防止泄漏

读取：

```text
questions/q2/artifacts/tables/q2_data_split.csv
```

严格复用第二问的固定划分：

* train：514 条；
* test：221 条。

规则：

1. 横向偏移模型只使用 q2 训练集训练；
2. 横向模型的超参数只在训练集内部交叉验证选择；
3. q2 测试集仅用于评价横向模型；
4. 参数优化不能使用测试集实测结果；
5. 搜索空间支持度只能根据训练集计算；
6. “最佳观测记录基线”只能从训练集选择。

不得重新随机划分数据。

---

# 6. 横向偏移代理模型

## 6.1 输入特征

使用与 q2 launch-state 模型一致的特征：

```text
ball_speed_mph
launch_angle_deg
launch_direction_deg
spin_rate_rpm
spin_axis_deg
```

目标：

```text
lateral_offset_yd
```

优化时固定：

```text
launch_direction_deg = 0
```

---

## 6.2 候选模型

至少训练：

```text
DummyRegressor
LinearRegression
RidgeCV
HistGradientBoostingRegressor
ExtraTreesRegressor
```

模型选择使用训练集五折交叉验证 RMSE。

测试集报告：

```text
RMSE
MAE
R²
bias
```

横向偏移可能接近 0，因此不得使用普通 MAPE 作为主要指标。

---

## 6.3 保存产物

```text
questions/q3/artifacts/models/q3_lateral_model.joblib
questions/q3/artifacts/tables/q3_lateral_model_metrics.csv
questions/q3/artifacts/tables/q3_lateral_predictions.csv
```

保存模型时记录：

* 特征顺序；
* 模型类别；
* 训练记录编号；
* 训练数据哈希；
* Git commit；
* 随机种子。

---

# 7. 搜索边界和数据支持区域

当前 q3 方案使用：

```text
球速：80–140 mph
发射角：5–30°
自旋速率：1000–10000 rpm
自旋轴偏角：−30–30°
```

这些边界可以作为题目允许的硬边界，但必须再次从原始题面确认。

完整数据实际观测范围更宽，例如球速约为 65.25–141.67 mph、发射角约为 1.85–41.82°、自旋速率约为 526–15368 rpm、自旋轴偏角约为 −80.49–81.10°。这些全样本范围不能直接用于构造优化支持区域，支持区域必须只根据 q2 训练集计算。

---

## 7.1 硬约束

[
80\le v\le140
]

[
5\le\theta\le30
]

[
1000\le\omega\le10000
]

[
-30\le\alpha\le30
]

---

## 7.2 数据支持度

不能只检查每个变量是否在上下界内，因为某些变量组合可能从未在训练数据中出现。

在训练集四维空间中：

```text
ball_speed_mph
launch_angle_deg
spin_rate_rpm
spin_axis_deg
```

进行标准化，计算候选点到最近 (k) 个训练样本的平均距离：

[
d_{\mathrm{knn}}(u)
===================

\frac1k
\sum_{i=1}^{k}
\left|
z(u)-z(u_i)
\right|_2
]

建议：

```text
k = 5
```

以训练样本留一法 kNN 距离的 95% 分位数作为支持阈值。

分类：

```text
supported
borderline
out_of_support
```

最终必须分别报告：

1. 全题面边界最优解；
2. 训练数据支持区域内最优解。

论文优先推荐第二种。

---

# 8. 优化基线

## 8.1 最佳观测击球基线

从 q2 训练集中计算：

[
J_i=
\sqrt{
(D_i-200)^2+L_i^2
}
]

选择最小值。

输出：

```text
q3_best_observed_baseline.csv
```

该基线表示：

> 训练数据中实际出现过的最佳 200 yd 击球记录。

---

## 8.2 Sobol 或 Latin Hypercube 基线

在四维硬边界内生成至少：

```text
20000
```

个低差异样本。

计算所有候选点的：

* carry；
* lateral；
* 目标函数；
* kNN 支持距离。

保存排名前 100 个候选点。

---

# 9. 主优化算法

使用：

```python
scipy.optimize.differential_evolution
```

建议配置：

```yaml
strategy: best1bin
population_size: 20
max_iterations: 300
tolerance: 1.0e-7
workers: 1
polish: false
seeds:
  - 2026
  - 2027
  - 2028
  - 2029
  - 2030
```

由于树模型目标函数可能分段常数，不依赖梯度局部优化。

全局搜索完成后，对每次最优点周围进行局部低差异采样：

```text
球速 ±2 mph
发射角 ±1°
自旋速率 ±300 rpm
自旋轴偏角 ±2°
```

每个邻域至少采样 5000 点，寻找更优或更稳健的候选。

不得将 Powell 或 SLSQP 的“正常结束”作为树模型全局最优的证明。

---

# 10. 名义最优与稳健最优

必须区分两个结果。

## 10.1 数学名义最优

直接最小化：

[
J_0(u)
]

得到：

```text
nominal_optimum
```

---

## 10.2 实际稳健最优

先构造近优候选集合：

[
\mathcal C=
\left{
u:
J_0(u)\le J_{\min}+\delta
\right}
]

建议：

```text
δ = 0.5 yd
```

对每个候选进行击球扰动模拟。

初始扰动方案：

```text
球速：±1 mph
发射角：±0.5°
自旋速率：±150 rpm
自旋轴偏角：±1°
```

这些是情景假设，不得写成已知球员测量误差。

采用固定随机种子生成至少 2000 个扰动样本，计算：

```text
mean_miss_distance
median_miss_distance
p90_miss_distance
maximum_miss_distance
probability_within_3yd
probability_within_5yd
```

稳健最优定义为：

1. 位于训练数据支持区域；
2. 名义目标在近优集合内；
3. `p90_miss_distance` 最小。

最终同时报告：

```text
nominal_optimum
robust_recommended_optimum
```

---

# 11. 预测不确定性

训练若干个 Bootstrap 或不同随机种子的模型：

```text
5 个 carry 代理模型
5 个 lateral 代理模型
```

对候选点计算模型间预测标准差：

```text
carry_prediction_std
lateral_prediction_std
objective_prediction_std
```

若名义最优点具有明显高于训练样本区域的模型分歧，不应作为最终推荐策略。

候选分类：

```text
stable_across_models
moderately_model_sensitive
highly_model_sensitive
```

---

# 12. ODE 轨迹复核

对以下参数分别运行 ODE：

1. 最佳观测击球；
2. 监督名义最优；
3. 监督稳健最优。

至少使用：

```text
constant_lift
```

如果第二问 `spin_factor_lift` 已通过最终验收，再增加：

```text
spin_factor_lift
```

输出：

```text
predicted_x_carry_yd
predicted_radial_carry_yd
predicted_lateral_yd
predicted_apex_yd
flight_time_s
integration_status
```

监督模型与 ODE 的预测差异定义为：

[
\Delta_D=
\hat D_{\mathrm{sup}}-\hat D_{\mathrm{ODE}}
]

[
\Delta_L=
\hat L_{\mathrm{sup}}-\hat L_{\mathrm{ODE}}
]

差异较大时不能声称结果得到物理模型一致验证，只能写：

> 监督模型给出了数据驱动最优解，而简化 ODE 对该区域的外推存在明显差异。

---

# 13. 轨迹绘制

对最终稳健最优参数生成：

```text
q3_optimal_trajectory.csv
```

字段：

```text
model
time_s
x_m
y_m
z_m
x_yd
y_yd
z_yd
```

生成：

```text
q3_optimal_trajectory_3d.png
q3_optimal_trajectory_side.png
q3_optimal_trajectory_top.png
```

图中标出：

* 起点；
* 最高点；
* 首次落地点；
* 洞口位置 ((200,0))；
* 落点到洞口的连线；
* 距洞口误差。

不能只画轨迹，不显示洞口和最终误差。

---

# 14. 目标函数可视化

以稳健最优点为中心，固定另外两个变量，分别绘制：

## 图 1

```text
球速—发射角目标函数等高线
```

## 图 2

```text
自旋速率—自旋轴偏角目标函数等高线
```

每张图同时标出：

* 名义最优点；
* 稳健最优点；
* 数据训练样本；
* 数据支持边界；
* 目标函数等高线。

生成数据：

```text
q3_objective_slice_speed_angle.csv
q3_objective_slice_spin.csv
```

---

# 15. 推荐代码结构

```text
questions/q3/scripts/
├── pipeline.py
├── dependencies.py
├── surrogate.py
├── support.py
├── objective.py
├── optimize.py
├── robustness.py
├── ode_verify.py
├── validate.py
└── visualize.py
```

## `dependencies.py`

负责：

* 加载 q2 模型；
* 读取 q2 固定划分；
* 检查 q2 状态；
* 审计模型特征接口；
* 输出依赖审计。

## `surrogate.py`

负责：

* 训练 lateral 模型；
* 训练备选 carry/lateral 模型；
* 测试评价；
* 模型保存和加载。

## `support.py`

负责：

* 训练变量标准化；
* kNN 支持距离；
* 支持阈值；
* 支持分类。

## `objective.py`

统一实现：

```python
predict_landing(...)
nominal_objective(...)
support_penalty(...)
evaluate_candidate(...)
```

所有算法必须调用同一目标函数，禁止在不同脚本中重复实现距离公式。

## `optimize.py`

负责：

* 最佳观测基线；
* Sobol/LHS 基线；
* 差分进化；
* 多随机种子；
* 邻域细化；
* 候选汇总。

## `robustness.py`

负责：

* 参数扰动；
* 模型集合预测；
* 稳健最优选择；
* 目标距离变化场景。

## `ode_verify.py`

负责调用 q2 ODE，不复制第二问动力学方程。

## `validate.py`

负责所有质量门槛。

---

# 16. 配置文件

在 `configs/default.yaml` 中增加：

```yaml
q3:
  random_seed: 2026
  target:
    forward_distance_yd: 200.0
    lateral_yd: 0.0

  fixed_inputs:
    launch_direction_deg: 0.0

  variables:
    ball_speed_mph:
      lower: 80.0
      upper: 140.0
    launch_angle_deg:
      lower: 5.0
      upper: 30.0
    spin_rate_rpm:
      lower: 1000.0
      upper: 10000.0
    spin_axis_deg:
      lower: -30.0
      upper: 30.0

  support:
    neighbors: 5
    threshold_quantile: 0.95

  baseline:
    sample_count: 20000
    method: sobol

  differential_evolution:
    strategy: best1bin
    population_size: 20
    max_iterations: 300
    tolerance: 1.0e-7
    seeds:
      - 2026
      - 2027
      - 2028
      - 2029
      - 2030

  near_optimal_tolerance_yd: 0.5

  perturbation:
    simulations: 2000
    ball_speed_sd_mph: 1.0
    launch_angle_sd_deg: 0.5
    spin_rate_sd_rpm: 150.0
    spin_axis_sd_deg: 1.0

  ode_verification:
    required: false
    models:
      - constant_lift
      - spin_factor_lift

  plotting:
    dpi: 300
```

所有扰动值在论文中标记为情景假设。

---

# 17. 输出文件

## 模型评价

```text
q3_dependency_audit.csv
q3_lateral_model_metrics.csv
q3_lateral_predictions.csv
q3_surrogate_ensemble_metrics.csv
```

## 支持区域

```text
q3_search_bounds.csv
q3_support_threshold.csv
q3_training_support.csv
```

## 优化

```text
q3_best_observed_baseline.csv
q3_sampling_baseline.csv
q3_optimization_runs.csv
q3_top_candidates.csv
q3_optimal_parameters.csv
```

`q3_optimal_parameters.csv` 至少包含两行：

```text
nominal_optimum
robust_recommended_optimum
```

## 稳健性

```text
q3_parameter_robustness.csv
q3_model_crosscheck.csv
q3_target_distance_sensitivity.csv
```

目标距离敏感性至少分析：

```text
195 yd
200 yd
205 yd
```

## ODE

```text
q3_ode_crosscheck.csv
q3_optimal_trajectory.csv
```

## 验证

```text
q3_validation_checks.csv
run_metadata.json
```

---

# 18. 验证要求

## 依赖验证

* q2 carry 模型可以加载；
* lateral 模型可以加载；
* 特征名称和顺序正确；
* q2 训练测试划分无重叠；
* q3 未使用 q2 测试集调参；
* manifest 中不存在失效文件。

## 目标函数验证

对任意候选点手工复算：

[
\sqrt{(D-200)^2+L^2}
]

结果必须与 CSV 一致。

## 约束验证

* 所有变量位于硬边界；
* 发射方向严格为 0；
* 最优点支持类别已记录；
* 边界最优解产生警告；
* out-of-support 候选不能静默成为推荐方案。

## 优化验证

* 差分进化至少运行五个随机种子；
* 每次运行结果完整保存；
* 主结果优于最佳观测基线或说明未能超越；
* 主结果不差于大规模采样基线；
* 名义目标重新调用模型后可复现；
* 不允许仅保存最后一次优化结果。

## 稳健性验证

* 扰动模拟数量满足配置；
* 所有扰动参数裁剪到硬边界；
* 近优集合非空；
* 稳健最优属于近优集合；
* 稳健性指标可以从扰动明细复算。

## ODE 验证

* 模块直接复用 q2 ODE；
* ODE 积分成功；
* 使用的 q2 参数版本和 Git commit 已记录；
* 若 ODE 未通过依赖检查，结果明确标记为 provisional；
* 不得把监督—ODE 一致性当作真实击球实验验证。

---

# 19. 第一阶段停止点

本轮先完成：

1. 修正 q3 manifest；
2. 加载 q2 carry 模型；
3. 训练并评价 lateral 模型；
4. 构建训练数据支持度；
5. 完成最佳观测基线；
6. 完成 Sobol/LHS 基线；
7. 完成五次差分进化；
8. 输出名义最优和稳健最优；
9. 完成参数扰动分析；
10. 暂不把 ODE 结果作为最终验证结论。

第一阶段完成后，q3 状态设置为：

```text
supervised_optimization_done
```

第二问 ODE 最终整改完成后，再执行 ODE 轨迹复核并将 q3 设置为：

```text
done
```

---

# 20. 完成标准

第三问只有满足以下条件才能标记为完成：

* q3 正式入口可运行；
* q2 carry 模型依赖路径正确；
* lateral 模型通过固定测试集评价；
* 目标函数同时包含前向误差和横向误差；
* 最佳观测基线完成；
* 大规模采样基线完成；
* 多种子差分进化完成；
* 名义最优与稳健最优分开报告；
* 搜索结果经过训练支持度检查；
* 参数扰动和模型分歧分析完成；
* 目标距离 195/200/205 yd 灵敏度完成；
* 三维、侧视、俯视轨迹完成；
* 所有图具有对应 CSV 和元数据；
* 验证脚本检查真实数值；
* 结果可由固定随机种子复现；
* 文档、表格和代码中的最优参数完全一致；
* 证据链已更新。

---

# 21. 推荐提交顺序

```text
docs(q3): finalize robust inverse-design plan
```

```text
fix(q3): update q2 model dependencies
```

```text
feat(q3): train lateral landing surrogate
```

```text
feat(q3): add empirical support diagnostics
```

```text
feat(q3): implement baseline and global optimization
```

```text
feat(q3): add robust candidate selection
```

```text
feat(q3): add ode trajectory crosscheck
```

```text
test(q3): validate constraints and reproducibility
```

```text
docs(q3): publish optimal hitting strategy
```

---

# 22. 完成后返回内容

本地 Agent 完成第一阶段后返回：

```text
1. 修改文件列表
2. q2 依赖审计结果
3. lateral 模型测试指标
4. 题面硬边界和训练支持边界
5. 最佳观测基线
6. Sobol/LHS 基线
7. 每次差分进化结果
8. 名义最优参数
9. 稳健推荐参数
10. 预测 carry、lateral 和距洞误差
11. 参数扰动结果
12. 模型分歧结果
13. 是否位于训练支持区域
14. ODE 是否满足复核条件
15. 验证结果
16. Git commit
```
