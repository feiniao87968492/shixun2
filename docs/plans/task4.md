# 第二问最终整改任务书：优化有效性与 Carry 口径统一

## 1. 任务范围

项目：

```text
https://github.com/feiniao87968492/shixun2
```

本轮只整改第二问 ODE 部分。

不得修改：

* 固定 70%/30% 数据划分；
* 监督模型训练和选模结果；
* 监督模型测试指标；
* 三条典型记录的样本编号；
* 当前物理坐标系统；
* 已经修正的顺逆风向量；
* drag/lift 代表样本配置；
* KMeans 代表样本选择方式。

必须解决：

1. 局部优化实际未运行；
2. 优化器失败被错误标记为成功；
3. Carry 最终选择 (D_x)，但标定和评价仍使用径向距离；
4. 积分失败样本被静默排除；
5. 第三问兼容 ODE 的可靠性不足；
6. 验证程序没有发现上述问题。

---

## 2. 当前状态标记

立即把以下文件中的 q2 状态从 `done` 改为：

```text
conditionally_passed
```

文件：

```text
README.md
questions/q2/README.md
questions/q2/manifest.yaml
```

完成全部验收后再改回 `done`。

---

# 3. P0：统一 Carry 定义

## 3.1 配置中声明主定义

在 `configs/default.yaml` 添加：

```yaml
q2:
  ode:
    carry_definition: forward_x
```

允许值：

```text
forward_x
radial
```

本项目最终主定义固定为：

```text
forward_x
```

---

## 3.2 修改轨迹输出字段

`simulate_shot()` 继续保留：

```text
predicted_x_carry_yd
predicted_radial_carry_yd
```

但禁止让含义模糊的 `predicted_carry_yd` 永久等于径向距离。

建议增加：

```python
def select_predicted_carry(
    prediction: dict[str, float],
    carry_definition: str,
) -> float:
    if carry_definition == "forward_x":
        return float(prediction["predicted_x_carry_yd"])
    if carry_definition == "radial":
        return float(prediction["predicted_radial_carry_yd"])
    raise ValueError(...)
```

然后设置：

```python
prediction["predicted_carry_yd"] = select_predicted_carry(
    prediction,
    carry_definition,
)
```

所有函数显式接收 `carry_definition`，不得依赖隐含默认值。

---

## 3.3 统一以下模块

全部改为使用配置中的主 Carry 定义：

```text
_objective()
evaluate_ode_models()
ode_metrics()
typical_errors_and_trajectories()
_scenario_means()
ode_sensitivity()
```

尤其是参数标定目标必须改为：

```python
carry_prediction = select_predicted_carry(
    pred,
    carry_definition="forward_x",
)

carry_error = (
    carry_prediction - float(row["carry_distance_yd"])
) / carry_scale
```

---

## 3.4 距离定义比较表

`q2_carry_definition_comparison.csv` 可以继续保留，但必须明确：

### 前向距离

```text
actual = carry_distance_yd
predicted = predicted_x_carry_yd
```

### 径向距离

若认为数据中的 carry 是前向距离，则：

```text
actual_radial = sqrt(carry_distance_yd² + lateral_offset_yd²)
predicted_radial = predicted_radial_carry_yd
```

表中增加：

```text
actual_definition
predicted_definition
is_primary_definition
```

主定义只有 `D_x` 的 `is_primary_definition=True`。

---

# 4. P0：实现真正的局部优化

## 4.1 删除当前限制

不得继续使用：

```python
options={
    "maxiter": 1,
    "maxfev": 4,
}
```

这些设置不能形成有效优化。

---

## 4.2 配置化优化参数

增加：

```yaml
q2:
  ode:
    local_optimization:
      method: Powell
      maxiter: 80
      maxfev: 250
      xtol: 1.0e-4
      ftol: 1.0e-6
      minimum_improvement: 1.0e-6
```

若运行时间过长，可以先使用：

```yaml
maxiter: 40
maxfev: 120
```

但不得低于足以完成至少一次完整搜索方向循环的水平。

---

## 4.3 正确定义优化状态

优化表至少增加：

```text
optimizer_success
objective_finite
accepted
initial_objective
final_objective
objective_improvement
termination_message
iterations
function_evaluations
```

定义：

```python
optimizer_success = bool(result.success)
objective_finite = bool(np.isfinite(final_objective))

accepted = (
    optimizer_success
    and objective_finite
    and final_failed_count == 0
)
```

不得继续使用：

```python
success = np.isfinite(objective)
```

---

## 4.4 选择规则

每个模型至少运行：

* 粗网格最优点；
* 粗网格第二优点；
* 粗网格第三优点；
* 参数区间中点。

最终选择顺序：

1. `accepted=True`；
2. `final_objective` 最小；
3. 参数距离边界更远；
4. 参数值较简单。

若没有任何 `accepted=True` 的运行：

* 标定失败；
* 流水线返回非零退出码；
* 不生成 `done` 状态。

---

# 5. P0：积分失败必须进入目标函数

当前不得再采用：

```python
if integration_failed:
    continue
```

建议方案：

```python
failure_fraction = failures / len(records)

objective = (
    mean_successful_loss
    + failure_penalty * failure_fraction
)
```

配置：

```yaml
q2:
  ode:
    calibration_failure_penalty: 100.0
```

也可以采用更严格规则：

```python
if failures > 0:
    return np.inf, failures
```

对于第三问兼容模型，最终选中参数必须满足：

```text
calibration_failed_count = 0
full_train_failed_count = 0
test_failed_count = 0
```

输出失败样本编号：

```text
q2_drag_calibration_failures.csv
q2_constant_lift_calibration_failures.csv
q2_spin_factor_calibration_failures.csv
```

---

# 6. 重新标定全部 ODE 参数

Carry 口径改为 (D_x) 后，必须重新运行：

1. drag 粗网格；
2. drag 局部优化；
3. constant-lift 粗网格；
4. constant-lift 局部优化；
5. spin-factor 粗网格；
6. spin-factor 局部优化；
7. 完整训练集复核；
8. 固定测试集评价。

不得沿用当前参数：

```text
drag C_D=0.05
constant_lift C_D=0.27, C_L=0.18
spin_factor C_D=0.49, k_L=1.6
```

这些参数只能作为新的优化初始值之一。

---

# 7. 第三问兼容模型验收

`spin_factor_lift` 在交给第三问之前必须满足：

```text
full_train_failed_count = 0
test_failed_count = 0
```

并检查：

* carry (R^2)；
* apex (R^2)；
* 最大飞行时间；
* 最大最高点；
* 最大横向距离；
* 是否出现异常超长轨迹；
* 输入变量在允许范围边界时是否稳定积分。

增加边界组合测试，例如：

```text
球速最小/最大
发射角最小/最大
自旋率最小/最大
自旋轴偏角最小/最大
```

不能只测试观测数据中的普通记录。

若 spin-factor 仍明显不稳定，则第三问暂时采用：

```text
监督代理模型作为主优化器
constant_lift 作为轨迹展示模型
spin_factor_lift 仅作为附加敏感性模型
```

不得为了形式上使用自旋 ODE，而让第三问优化器利用不真实的长飞行时间或异常升力。

---

# 8. 主 ODE 模型的自动确定

不要硬编码：

```python
q2_best_fit_ode = "constant_lift"
```

根据完整训练集目标确定：

```python
candidate_models = [
    "drag",
    "constant_lift",
    "spin_factor_lift",
]

q2_best_fit_ode = min(
    valid_models,
    key=lambda model: full_train_objective[model],
)
```

测试集只用于最终报告，不用于主模型选择。

第三问兼容模型可以继续明确指定：

```python
q3_compatible_ode = "spin_factor_lift"
```

但必须通过第三问接口验收。

---

# 9. 修正典型记录和灵敏度结果

重新生成：

```text
q2_ode_typical_errors.csv
q2_typical_trajectories_constant_lift.csv
q2_typical_trajectories_spin_factor.csv
q2_ode_sensitivity.csv
```

所有表增加：

```text
carry_definition
```

其值必须为：

```text
forward_x
```

灵敏度中的：

```text
carry_yd
baseline_value
scenario_value
delta
```

均必须基于前向距离。

---

# 10. 扩展验证程序

## 10.1 优化器检查

新增：

```text
optimizer_terminated_successfully
optimizer_message_not_max_evaluations
optimizer_iterations_positive
optimizer_function_evaluations_above_minimum
selected_run_accepted
selected_run_objective_finite
selected_run_zero_calibration_failures
selected_run_zero_full_train_failures
```

其中：

```text
message 包含 "Maximum number of function evaluations"
```

时必须失败。

---

## 10.2 参数改进检查

至少检查：

```text
final_objective <= initial_objective + tolerance
```

并记录：

```text
objective_improvement
```

不强制要求参数一定移动，因为粗网格点可能已经接近局部最优；但优化器必须正常终止，而不是因计算次数耗尽终止。

---

## 10.3 Carry 口径一致性

新增：

```text
configured_carry_definition_is_forward_x
ode_metrics_match_forward_x_predictions
typical_errors_match_forward_x_predictions
sensitivity_uses_forward_x
calibration_objective_uses_forward_x
```

从 `q2_ode_test_predictions.csv` 重新计算主指标，并确保与：

```text
q2_ode_test_metrics.csv
```

一致。

对 constant-lift 来说，修正前的 16.506 yd 不应继续作为主 RMSE。

---

## 10.4 失败样本检查

新增：

```text
selected_drag_zero_full_train_failures
selected_constant_lift_zero_full_train_failures
selected_spin_factor_zero_full_train_failures
all_models_zero_test_failures
```

若第三问兼容模型存在训练失败，q2 状态不得为 `done`。

---

# 11. 元数据路径跨平台处理

将所有路径改为：

```python
path.relative_to(root).as_posix()
```

禁止在提交的 JSON 中保存：

```text
questions\q2\...
```

统一为：

```text
questions/q2/...
```

---

# 12. 重新生成的文件

至少覆盖：

```text
q2_drag_optimization_runs.csv
q2_constant_lift_optimization_runs.csv
q2_spin_factor_optimization_runs.csv
q2_ode_parameter_surface.csv
q2_ode_parameters.csv
q2_ode_test_predictions.csv
q2_ode_test_metrics.csv
q2_ode_model_comparison.csv
q2_carry_definition_comparison.csv
q2_ode_typical_errors.csv
q2_typical_trajectories_constant_lift.csv
q2_typical_trajectories_spin_factor.csv
q2_ode_sensitivity.csv
q2_ode_validation_checks.csv
q2_validation_checks.csv
run_metadata.json
```

以及所有对应图片和生图数据。

---

# 13. 文档修改

更新：

```text
questions/q2/results.md
questions/q2/README.md
questions/q2/approach.md
questions/q2/experiments.md
questions/q2/manifest.yaml
README.md
docs/evidence_chain.csv
```

在真实局部优化完成前，不得使用：

```text
参数经粗网格 + 有界局部优化获得
```

必须写：

```text
当前参数来自粗网格搜索
```

最终文档中的 ODE carry 指标必须与配置中的 `forward_x` 定义一致。

---

# 14. 执行与验收

依次运行：

```bash
python questions/q2/scripts/pipeline.py \
  --config configs/default.yaml
```

```bash
python questions/q2/scripts/validate.py \
  --config configs/default.yaml
```

```bash
python -m pytest tests/test_q2_task3_recalibration.py -q
```

再次运行流水线，验证：

* 数据划分不变；
* 代表样本不变；
* 参数结果可复现；
* 主要 CSV 可复现；
* 所有选中优化运行正常结束；
* 所有选中参数全训练集积分失败数为 0；
* Carry 主指标完全按照 (D_x) 计算。

---

# 15. 完成标准

只有满足以下条件，q2 才能恢复为 `done`：

* Powell 或其他有界优化器正常终止；
* 不存在“超过最大函数计算次数”却标为成功的运行；
* `success` 使用真实优化器状态；
* 参数标定使用前向距离 (D_x)；
* 主 ODE 评价使用前向距离 (D_x)；
* 典型记录和灵敏度使用前向距离 (D_x)；
* 三种选中参数在完整训练集均无积分失败；
* 第三问兼容模型通过边界稳定性测试；
* 验证程序能够发现优化器失败和距离定义不一致；
* 元数据路径跨平台；
* 文档、表格和代码结论一致。

---

# 16. 建议提交顺序

```text
fix(q2): use forward carry consistently in ode workflow
```

```text
fix(q2): record real optimizer termination status
```

```text
feat(q2): run bounded local parameter refinement
```

```text
fix(q2): penalize ode integration failures
```

```text
test(q2): validate carry semantics and optimizer convergence
```

```text
docs(q2): publish consistently recalibrated ode results
```

---

# 17. 完成后返回

返回以下内容：

```text
1. 修改文件列表
2. Carry 定义在所有模块中的修改位置
3. 优化器配置
4. 每次优化的真实 termination status
5. 初始参数、最终参数和目标函数改进量
6. 新的 drag 参数
7. 新的 constant-lift 参数
8. 新的 spin-factor 参数
9. 完整训练集积分失败数量
10. 新的 D_x 测试集指标
11. 新的典型记录误差
12. 第三问兼容模型边界测试
13. 验证结果
14. Git commit
```
