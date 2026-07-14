# Q2 与 Q3 联合整改及最终复现任务书

## 1. 总目标

修复 Q2 ODE 与 Q3 稳健优化中的实现和版本一致性问题，使公开仓库能够从正式脚本完整复现文档中的全部结论。

本轮不得只修改 Markdown。必须修改代码、重新运行流水线、覆盖结果并提交全部产物。

在整改完成前：

```yaml
q2_status: conditionally_passed
q3_status: conditionally_passed
```

---

## 2. 第一阶段：仓库版本同步

检查本地工作区是否存在尚未推送的 Q2/Q3 新代码。

必须确保以下内容属于同一 Git commit：

```text
configs/default.yaml

questions/q2/scripts/
questions/q2/artifacts/
questions/q2/results.md
questions/q2/README.md
questions/q2/manifest.yaml

questions/q3/scripts/
questions/q3/artifacts/
questions/q3/results.md
questions/q3/README.md
questions/q3/manifest.yaml

README.md
docs/evidence_chain.csv
```

删除或归档无法由当前脚本生成的旧结果。

新增：

```text
docs/reproducibility/q2_q3_release_manifest.json
```

记录：

```text
git_commit
config_sha256
data_sha256
q2_run_metadata_sha256
q3_run_metadata_sha256
所有核心 CSV 的 SHA256
```

---

## 3. Q2 P0 整改

### 3.1 修复标定配置

阻力标定必须读取：

```python
config["ode"]["drag_calibration"]["representative_count"]
config["ode"]["drag_calibration"]["grid_size"]
```

升力标定读取：

```python
config["ode"]["lift_calibration"]["representative_count"]
config["ode"]["lift_calibration"]["grid_size"]
```

分别输出：

```text
q2_drag_calibration_records.csv
q2_lift_calibration_records.csv
```

---

### 3.2 改进代表样本

不再只按 carry 排序等距抽取。

基于以下变量标准化后 KMeans 或分层抽样：

```text
ball_speed_mph
launch_angle_deg
spin_rate_rpm
spin_axis_deg
carry_distance_yd
apex_height_yd
```

固定随机种子，保存每条代表记录和所属聚类。

---

### 3.3 统一 Carry 定义

在配置中增加：

```yaml
q2:
  ode:
    carry_definition: forward_x
```

保留字段：

```text
predicted_x_carry_yd
predicted_radial_carry_yd
```

主字段：

```text
predicted_carry_yd
```

必须根据配置选择，当前主定义使用：

```text
forward_x
```

以下模块必须统一：

```text
标定目标函数
测试集评价
典型记录误差
灵敏度分析
Q3 ODE 复核
```

---

### 3.4 实现粗搜索与局部优化

流程：

1. 粗网格确定初始区域；
2. 选择最优的前 3–5 个网格点；
3. 使用有界 `scipy.optimize.minimize` 或 `least_squares`；
4. 多初值运行；
5. 在完整训练集复核目标函数。

输出：

```text
q2_drag_optimization_runs.csv
q2_constant_lift_optimization_runs.csv
q2_spin_factor_optimization_runs.csv
```

字段：

```text
initial_parameters
final_parameters
initial_objective
final_objective
result_success
termination_message
iterations
function_evaluations
calibration_failed_count
full_train_failed_count
at_parameter_boundary
```

---

### 3.5 惩罚积分失败

禁止：

```python
if integration_failed:
    continue
```

采用：

```python
if integration_failed:
    return np.inf
```

或加入高额失败比例惩罚。

最终选中参数必须满足：

```text
calibration_failed_count = 0
full_train_failed_count = 0
test_failed_count = 0
```

---

### 3.6 配置积分时间上限

增加：

```yaml
q2:
  ode:
    solver:
      max_flight_time_s: 20.0
```

超过上限但未触地时：

```text
integration_status = time_horizon_exceeded
```

对 Q3 参数边界组合进行积分稳定性测试。

---

### 3.7 分开 Q2 主模型与 Q3 接口

自动根据完整训练集目标选择：

```text
q2_best_fit_ode
```

预计为 `constant_lift`，但不得硬编码。

单独定义：

```text
q3_compatible_ode = spin_factor_lift
```

分别输出两套典型轨迹和灵敏度。

---

### 3.8 补充典型记录横向误差

典型记录表增加：

```text
lateral_absolute_error_yd
lateral_smape_pct
```

当实测横向偏移绝对值较小时，不使用普通 MAPE。

---

## 4. Q3 P0 整改

### 4.1 使用完整近优候选池

稳健候选必须从以下全部原始候选中形成：

```text
LHS 候选
所有 DE 解
所有局部细化候选
最佳观测记录
```

先构造近优集合，再决定是否降采样。

禁止在构造近优集合前执行：

```python
top_candidates(..., limit=...)
```

若 supported 近优候选不超过 500，全部进入稳健分析；超过 500 时使用聚类或最远点抽样选取 50–100 个覆盖候选。

输出：

```text
q3_robust_candidate_pool.csv
```

---

### 4.2 使用共同随机数

一次性生成扰动矩阵，所有候选共享：

```text
ball speed noise
launch angle noise
spin rate noise
spin axis noise
launch direction noise
```

不得在候选循环内部重新生成不同噪声。

---

### 4.3 加入发射方向场景

配置：

```yaml
launch_direction_scenarios:
  ideal:
    sd_deg: 0.0
  stable_player:
    sd_deg: 0.5
  ordinary_player:
    sd_deg: 1.0
```

最终推荐以 `stable_player` 为主场景。

修改 `candidate_frame()`，允许每一行具有不同的：

```text
launch_direction_deg
```

---

### 4.4 联合模型与参数不确定性

对稳健候选同时使用：

```text
至少 5 个 carry 模型成员
至少 5 个 lateral 模型成员
共同参数扰动
```

计算：

```text
mean miss
median miss
p90
p95
worst-model mean
P(within 3 yd)
P(within 5 yd)
model prediction std
```

最终推荐规则：

1. supported；
2. 名义目标不超过最优值加 0.5 yd；
3. stable-player 场景；
4. 联合 p90 最小；
5. p90 接近时，支持距离更小者优先。

输出：

```text
q3_joint_robustness_detail.csv
q3_joint_robustness_summary.csv
```

---

### 4.5 对三个目标独立优化

分别对：

```text
195 yd
200 yd
205 yd
```

执行：

```text
LHS
至少 3 个 DE 随机种子
局部细化
支持域检查
```

禁止只对 200 yd 候选重新计分。

输出：

```text
q3_target_optimization_runs.csv
q3_target_optimal_parameters.csv
```

---

### 4.6 修正优化成功状态

定义：

```python
success = bool(result.success)
objective_finite = bool(np.isfinite(result.fun))
accepted = success and objective_finite
```

验证必须检查：

```text
scipy_success
termination_message
iterations
function_evaluations
objective recomputation
```

---

### 4.7 完整输入支持度

支持域同时报告：

```text
decision_space_support
full_model_input_support
```

完整模型输入包括：

```text
ball_speed
launch_angle
launch_direction
spin_rate
spin_axis
```

扰动明细中统计：

```text
supported_fraction
borderline_fraction
out_of_support_fraction
```

超过 5% 扰动样本处于 `out_of_support` 的候选不得作为最终推荐。

---

### 4.8 报告参数区间而非伪精确单点

生成：

```text
q3_near_optimal_parameter_ranges.csv
```

报告：

```text
min
q10
median
q90
max
```

论文参数保留合理精度：

```text
球速：约 1 mph
发射角：约 0.5°
自旋率：约 50–100 rpm
自旋轴：约 0.5°
```

名义残差不得解释成真实击球精度。

---

## 5. 验证程序新增检查

### Q2

```text
drag 配置实际生效
carry 定义全流程一致
优化器真实成功
失败样本受到惩罚
选中参数全训练集零失败
典型横向 SMAPE 存在
主轨迹模型由训练结果决定
```

### Q3

```text
近优集合在截断前生成
稳健候选数不固定为 12
共同随机数已使用
发射方向扰动存在
联合模型—参数稳健性完整
195/200/205 独立优化
scipy_success 全部通过
五维支持度已检查
最终推荐等于联合 p90 最优
```

验证失败时返回非零退出码。

---

## 6. 执行顺序

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
python questions/q2/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_full_task2.py -q

python questions/q3/scripts/pipeline.py --config configs/default.yaml
python questions/q3/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q3_task5_inverse_design.py -q
```

增加：

```bash
python -m pytest tests/test_q2_q3_integration.py -q
```

检查：

```text
Q3 使用的 Q2 参数哈希与当前 Q2 run_metadata 一致
Q3 使用的 carry 定义与 Q2 一致
Q3 ODE 全部候选积分成功
Q3 文档中的参数可从 CSV 复算
```

---

## 7. 完成标准

全部满足后才能设置：

```yaml
q2_status: done
q3_status: done
```

要求：

* 公开仓库中的代码、结果和文档属于同一 commit；
* Q2 ODE 配置真实生效；
* Carry 语义统一；
* 参数经过真实局部优化；
* 积分失败不会被静默忽略；
* Q3 稳健推荐覆盖完整近优候选；
* 发射方向和模型不确定性已纳入；
* 三个目标距离均独立优化；
* Q3 三维轨迹使用当前 Q2 参数；
* 所有 README、manifest、results、artifacts 与 metadata 一致。

---

## 8. 完成后返回

```text
1. 最终 Git commit
2. 修改文件清单
3. Q2 修复前后参数
4. Q2 修复前后 ODE 测试指标
5. Q2 Carry 定义
6. Q2 全训练集积分失败数
7. Q3 稳健候选池规模
8. Q3 发射方向三场景结果
9. Q3 联合模型—参数稳健推荐
10. 195/200/205 yd 独立优化结果
11. 近优参数区间
12. Q2-Q3 集成验证结果
13. 尚未解决的物理模型局限
```
