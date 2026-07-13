# Q3 最终整改任务书：稳健候选、模型不确定性与目标距离重优化

## 1. 任务目标

本轮不推翻现有 Q3 主流程，集中修复以下问题：

1. 稳健性只比较前 12 个近优候选；
2. 195/205 yd 灵敏度未重新优化；
3. 发射方向没有进入扰动分析；
4. 稳健推荐未纳入模型不确定性；
5. 参数精度和单点结论过强；
6. 验证程序没有覆盖上述问题。

完成前将 Q3 状态设置为：

```yaml
q3_status: conditionally_passed
```

完成全部验收后再恢复：

```yaml
q3_status: done
```

---

## 2. 不得修改的内容

保留：

* Q2 固定 train=514、test=221 划分；
* 当前 Q2 carry 和 apex 主模型；
* Q3 lateral 模型训练和固定测试集评价；
* 硬搜索边界；
* 200 yd 目标函数定义；
* 20,000 点 LHS 基线；
* 五个 DE 随机种子；
* kNN 数据支持度框架；
* Q2 ODE 调用接口；
* 当前名义最优作为比较基线。

不得通过重新划分测试集改善结果。

---

## 3. P0：扩大稳健候选集合

修改：

```text
questions/q3/scripts/robustness.py
```

当前逻辑：

```python
selected = pd.concat([
    near.head(1),
    supported.sort_values(...).head(12),
])
```

必须删除固定 `head(12)` 限制。

### 推荐方案 A：全部计算

如果 supported 近优候选数不超过 500：

```python
selected = near[
    near["support_category"] == "supported"
].copy()
```

对全部候选执行扰动。

### 推荐方案 B：多样化抽样

如果候选数过多：

1. 始终保留名义最优；
2. 对四个决策变量标准化；
3. 使用 KMeans 或 farthest-point sampling；
4. 选择 50–100 个覆盖整个近优空间的代表候选；
5. 保存候选选择理由。

生成：

```text
q3_robust_candidate_pool.csv
```

至少包含：

```text
candidate_id
nominal_rank
objective_yd
support_category
selection_method
cluster_id
selected_for_robustness
```

验证：

* `selected_for_robustness` 数量不得被硬编码为 12；
* 所有 selected 候选必须属于 supported 近优集合；
* 稳健推荐必须来自该表。

---

## 4. P0：使用共同随机数比较候选

当前每个候选依次从同一个 RNG 获取不同噪声，不同候选并未接受完全相同的扰动情景。

改为先生成标准化噪声矩阵：

```python
noise = generate_noise(
    simulations=...,
    seed=...,
)
```

所有候选共用同一套噪声：

```python
perturbed_values = candidate_values + noise
```

这样可以降低候选 p90 差异中的 Monte Carlo 噪声。

同时对 p90 进行 Bootstrap，输出：

```text
p90_miss_distance_yd
p90_ci_low
p90_ci_high
```

若两个候选的区间高度重叠，应标记为：

```text
robustness_statistical_tie
```

---

## 5. P0：加入发射方向扰动

保持名义输入：

```yaml
launch_direction_deg: 0.0
```

但在稳健性配置中增加：

```yaml
q3:
  perturbation:
    launch_direction_scenarios:
      ideal:
        sd_deg: 0.0
      stable_player:
        sd_deg: 0.5
      ordinary_player:
        sd_deg: 1.0
```

`candidate_frame()` 必须允许逐行传入不同发射方向，不能继续把整批候选强制设置为同一个标量。

扰动模型：

[
\phi^{(s)}
==========

0+\varepsilon_\phi^{(s)}
]

每种场景分别输出：

```text
mean_miss_distance_yd
median_miss_distance_yd
p90_miss_distance_yd
probability_within_3yd
probability_within_5yd
```

最终推荐优先依据：

```text
stable_player / sd=0.5°
```

`ideal / sd=0°` 仅作为理论情景。

论文必须明确这些标准差是情景假设，不是实测球员误差。

---

## 6. P0：将模型不确定性纳入稳健推荐

当前模型集合只用于事后检查。改为进入候选选择。

对每个稳健候选同时使用：

```text
5 个 carry ensemble members
5 个 lateral ensemble members
```

推荐使用对应成员组合，也可以使用所有 (5\times5) 组合，但必须记录组合规则。

对每个候选、每个模型成员、每个扰动样本计算：

[
J_{b,s}(u)
==========

\sqrt{
[\hat D_b(u+\varepsilon_s)-200]^2+
[\hat L_b(u+\varepsilon_s)]^2
}
]

输出：

```text
q3_joint_robustness_detail.csv
q3_joint_robustness_summary.csv
```

汇总字段：

```text
candidate_id
parameter_scenario
model_member_count
simulation_count
mean_miss_distance_yd
median_miss_distance_yd
p90_miss_distance_yd
p95_miss_distance_yd
worst_model_mean_miss_yd
probability_within_3yd
probability_within_5yd
objective_prediction_std
```

新的稳健推荐规则：

1. `support_category == supported`；
2. 名义目标不超过最优值加 0.5 yd；
3. 使用 `stable_player` 发射方向场景；
4. 以联合模型—参数扰动的 p90 最小为主；
5. p90 接近时，以支持距离更小者优先。

保留旧结果并重命名为：

```text
single_surrogate_parameter_robustness
```

不得再把它作为最终稳健推荐依据。

---

## 7. P0：对 195/200/205 yd 分别重新优化

不要再把 200 yd 的 `q3_top_candidates.csv` 直接重新计分。

新增：

```python
def optimize_for_target(
    target_distance_yd: float,
    ...
) -> TargetOptimizationResult:
```

对每个目标分别执行：

```text
LHS baseline
至少 3 个 DE seeds
局部 refinement
supported candidate selection
```

保存：

```text
q3_target_optimization_runs.csv
q3_target_optimal_parameters.csv
```

字段至少包括：

```text
target_distance_yd
seed
candidate_id
ball_speed_mph
launch_angle_deg
spin_rate_rpm
spin_axis_deg
predicted_carry_yd
predicted_lateral_yd
objective_yd
support_category
```

验证要求：

* 195、200、205 yd 均有独立优化运行；
* 三个目标的候选 ID 不得全部来自原 200 yd 候选池；
* 每个目标至少有一个 supported 解；
* 每个目标的最优结果优于该目标对应的重新生成 LHS 基线。

---

## 8. P1：处理代理模型平台和参数非唯一性

生成近优区间表：

```text
q3_near_optimal_parameter_ranges.csv
```

对联合稳健性前 10% 或：

[
J\le J_{\min}+0.5\ \mathrm{yd}
]

的 supported 候选，报告：

```text
variable
min
q10
median
q90
max
```

最终论文主结果改为：

```text
球速约 120–122 mph
发射角约 19–20°
自旋速率约 2300–2700 rpm
自旋轴偏角接近 0°
```

具体区间以重跑结果为准。

CSV 中可以保留完整浮点数用于复现，但 Markdown 和论文不要报告 9–12 位小数。

增加检查：

```text
distinct_parameter_count
distinct_prediction_pair_count
largest_prediction_plateau_size
```

若多个参数共享同一预测结果，应明确标记：

```text
solution_non_unique_under_surrogate
```

---

## 9. P1：完善支持度检查

当前支持度仅使用四个决策变量。增加完整模型输入支持度：

```text
ball_speed_mph
launch_angle_deg
launch_direction_deg
spin_rate_rpm
spin_axis_deg
```

输出两种支持分类：

```text
decision_space_support
full_model_input_support
```

最终候选要求两者均不为 `out_of_support`。

扰动样本中报告：

```text
supported_fraction
borderline_fraction
out_of_support_fraction
```

若某候选超过 5% 的扰动样本落在 `out_of_support`，不能作为最终推荐。

---

## 10. P1：修正 DE 成功状态验证

在 `optimize.py` 中：

```python
success = bool(result.success)
objective_finite = np.isfinite(result.fun)
accepted = success and objective_finite
```

不要继续把 `success` 定义为仅目标函数有限。

验证程序检查：

```text
scipy_success == True
message 不包含失败或达到异常限制
objective_yd 可复算
```

当前五次运行均成功，但仍需修正代码语义。

---

## 11. 扩展验证程序

修改：

```text
questions/q3/scripts/validate.py
```

新增至少以下检查：

```text
all_supported_near_candidates_accounted_for
robust_candidate_pool_not_hardcoded_to_12
common_random_numbers_used
launch_direction_perturbation_present
joint_model_parameter_robustness_complete
robust_recommendation_matches_joint_p90_minimum
target_195_independently_optimized
target_200_independently_optimized
target_205_independently_optimized
target_specific_solution_beats_target_lhs
full_input_support_checked
perturbation_out_of_support_fraction_reported
scipy_success_all_true
near_optimal_parameter_ranges_generated
solution_non_uniqueness_reported
```

验证失败时返回非零退出码。

---

## 12. 结果文件调整

保留现有文件，但新增：

```text
q3_robust_candidate_pool.csv
q3_joint_robustness_detail.csv
q3_joint_robustness_summary.csv
q3_target_optimization_runs.csv
q3_target_optimal_parameters.csv
q3_near_optimal_parameter_ranges.csv
q3_support_comparison.csv
```

更新：

```text
q3_optimal_parameters.csv
```

至少包含：

```text
nominal_optimum
single_surrogate_robust_optimum
joint_robust_recommended_optimum
```

论文只推荐第三行。

---

## 13. 文档更新

修改：

```text
questions/q3/approach.md
questions/q3/results.md
questions/q3/experiments.md
questions/q3/evidence.md
questions/q3/README.md
questions/q3/manifest.yaml
README.md
docs/evidence_chain.csv
```

禁止继续无条件写：

```text
距洞 0.010 yd 的最优击球策略
```

应改为：

```text
选定监督代理模型内部的名义目标残差为 0.010 yd；
考虑模型分歧后，真实策略不确定性明显更大。
```

对于命中概率，必须加限定：

```text
在指定参数误差分布、发射方向误差场景和代理模型集合下的模拟比例
```

不能称为真实球员命中概率。

---

## 14. 执行命令

```bash
python questions/q3/scripts/pipeline.py \
  --config configs/default.yaml
```

```bash
python questions/q3/scripts/validate.py \
  --config configs/default.yaml
```

```bash
python -m pytest tests/test_q3_task5_inverse_design.py -q
```

建议新增：

```bash
python -m pytest tests/test_q3_final_robustness.py -q
```

再次运行流水线，检查：

* 最终稳健候选一致；
* 联合 p90 在浮点容差内一致；
* 三个目标距离结果一致；
* 输出文件哈希一致。

---

## 15. 完成标准

满足以下条件后 Q3 才能恢复为 `done`：

* 稳健候选不再固定限制为前 12 个；
* 使用共同随机数；
* 发射方向扰动已纳入；
* 模型不确定性已进入稳健推荐；
* 195/200/205 yd 均独立重新优化；
* 参数非唯一性和近优范围已报告；
* 完整五维模型输入支持度已检查；
* 扰动样本外推比例已报告；
* 验证程序检查真实方法逻辑；
* 文档不再把 0.010 yd 解释成实际击球精度；
* 最终推荐参数以合理精度和区间报告。

---

## 16. 推荐提交顺序

```text
fix(q3): evaluate the full supported near-optimal pool
```

```text
feat(q3): add launch-direction perturbation scenarios
```

```text
feat(q3): optimize joint model and parameter robustness
```

```text
fix(q3): rerun optimization for target-distance sensitivity
```

```text
feat(q3): report near-optimal parameter ranges
```

```text
test(q3): expand final robustness validation
```

```text
docs(q3): publish uncertainty-aware hitting strategy
```

---

## 17. 完成后返回内容

返回：

```text
1. 修改文件列表
2. 近优 supported 候选总数
3. 实际参与稳健性分析的候选数
4. 发射方向三种扰动场景结果
5. 单代理稳健解
6. 联合模型—参数稳健解
7. 联合 p90 和置信区间
8. 195/200/205 yd 独立优化结果
9. 近优参数范围
10. 扰动样本支持域比例
11. 参数非唯一性诊断
12. 新增验证结果
13. Git commit
```
