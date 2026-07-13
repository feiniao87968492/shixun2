# 第二问整改、重标定与最终验收任务书

## 1. 任务目标

对第二问现有代码和结果进行定向整改，不重构已经通过的监督预测部分。

本轮必须解决：

1. 阻力标定配置未生效；
2. ODE 参数只经过粗网格搜索；
3. 典型轨迹和灵敏度模型选择不一致；
4. 顺风、逆风向量方向写反；
5. 飞行距离定义未经验证；
6. 参数、验证和运行元数据不足；
7. 第二问状态文件不同步。

完成后重新生成全部 ODE 参数、预测、典型轨迹、灵敏度和验证产物。

---

## 2. 不得修改的内容

以下内容已经通过，除非发现明确错误，不要重新设计：

* 固定训练集和测试集样本编号；
* 70%/30% 主划分；
* 监督模型特征集；
* 监督模型训练流水线；
* 测试集预测结果计算方式；
* 约 100、150、200 yd 典型记录的选择规则；
* 当前测试集编号和典型记录编号。

禁止为了改善指标重新划分测试集或更换随机种子。

---

## 3. P0：修复 ODE 标定配置接线

检查：

```text
questions/q2/scripts/pipeline.py
configs/default.yaml
```

当前阻力标定错误读取：

```python
config["q2"]["ode"]["lift_calibration"]["representative_count"]
config["q2"]["ode"]["lift_calibration"]["grid_size"]
```

改为分别读取：

```python
drag_count = config["q2"]["ode"]["drag_calibration"]["representative_count"]
drag_grid_size = config["q2"]["ode"]["drag_calibration"]["grid_size"]

lift_count = config["q2"]["ode"]["lift_calibration"]["representative_count"]
lift_grid_size = config["q2"]["ode"]["lift_calibration"]["grid_size"]
```

分别生成：

```text
drag_representative_records
lift_representative_records
```

不得继续让三个标定模型无条件共用一个代表样本集合。

输出：

```text
questions/q2/artifacts/tables/q2_drag_calibration_records.csv
questions/q2/artifacts/tables/q2_lift_calibration_records.csv
```

验证：

* 阻力标定记录数等于配置中的 `drag_calibration.representative_count`；
* 升力标定记录数等于配置中的 `lift_calibration.representative_count`；
* 阻力网格点数与配置一致；
* 升力网格点数与配置一致。

---

## 4. P0：改进代表样本抽取

当前仅按照飞行距离排序后等距抽样，覆盖不足。

新方案至少考虑：

```text
ball_speed_mph
launch_angle_deg
spin_rate_rpm
carry_distance_yd
```

推荐方案：

1. 对上述变量标准化；
2. 使用 MiniBatchKMeans 或 KMeans；
3. 聚类数等于代表样本数量；
4. 每个聚类选距离聚类中心最近的实际记录；
5. 若出现重复记录，补选未选记录中距离对应中心最近者；
6. 固定随机种子。

也可采用多维分箱分层抽样，但必须保证不同球速、发射角和自旋区域均有覆盖。

输出每条记录的：

```text
record_id
calibration_type
cluster_or_stratum
ball_speed_mph
launch_angle_deg
spin_rate_rpm
spin_axis_deg
carry_distance_yd
apex_height_yd
```

---

## 5. P0：将参数标定改为“粗搜索＋局部优化”

### 5.1 阻力模型

先按配置进行粗网格搜索：

[
C_D\in[C_{D,\min},C_{D,\max}]
]

然后以粗网格最优值为初值，使用：

```python
scipy.optimize.minimize
```

或：

```python
scipy.optimize.least_squares
```

进行有界局部优化。

至少使用三个初值：

```text
粗网格最优值
参数区间中点
粗网格次优值
```

保存所有优化尝试：

```text
q2_drag_optimization_runs.csv
```

字段：

```text
initial_cd
final_cd
objective
success
message
iterations
```

### 5.2 常数升力模型

参数：

[
(C_D,C_L)
]

流程：

1. 二维粗网格；
2. 选择最优的前 3～5 个网格点；
3. 分别进行有界局部优化；
4. 选择训练目标最小且成功收敛的结果。

### 5.3 自旋因子升力模型

参数：

[
(C_D,k_L)
]

采用相同流程。

### 5.4 完整训练集复核

代表样本上得到参数后，在完整训练集上计算目标函数。

若代表样本最优参数在完整训练集上明显变差：

* 在完整训练集上做一次有限次数局部精调；
* 不得使用测试集精调。

---

## 6. 参数边界和边界告警

新增验证字段：

```text
at_lower_bound
at_upper_bound
distance_to_lower_bound
distance_to_upper_bound
```

若最优参数距离边界小于参数范围的 1%，验证结果至少产生警告。

对于仅阻力模型，若 (C_D) 仍位于下界且误差高于真空模型：

* 不再将它解释为可信阻力系数；
* 标记为 `boundary_solution`；
* 文档解释为模型结构不充分或参数不可识别。

禁止为了让参数不在边界而任意扩大参数范围。

---

## 7. P0：修复顺风和逆风方向

坐标中 (x) 轴向前为正。

修改为：

```python
wind_scenarios = {
    "no_wind": (0.0, 0.0, 0.0),
    "tailwind_1mps": (1.0, 0.0, 0.0),
    "headwind_1mps": (-1.0, 0.0, 0.0),
}
```

增加自动验证：

在正常轨迹和小风速下，应通常满足：

```text
tailwind carry > no-wind carry
headwind carry < no-wind carry
```

若某些极端样本不满足，不直接判定程序失败，但总体平均方向必须合理。

重新生成：

```text
q2_ode_sensitivity.csv
q2_ode_sensitivity.png
```

旧灵敏度结果必须覆盖或移入 archive，不能继续供论文引用。

---

## 8. P0：区分两种 ODE 的用途

定义：

```python
q2_best_fit_ode = "constant_lift"
q3_compatible_ode = "spin_factor_lift"
```

不要再使用没有语义的硬编码：

```python
trajectory_model = "spin_factor_lift"
```

### 第二问主结果

使用测试集误差最低的 ODE：

```text
constant_lift
```

生成：

```text
q2_typical_trajectories_constant_lift.csv
q2_typical_trajectories_constant_lift_3d.png
q2_typical_trajectories_constant_lift_side.png
q2_typical_trajectories_constant_lift_top.png
```

### 第三问接口验证

使用：

```text
spin_factor_lift
```

生成：

```text
q2_typical_trajectories_spin_factor.csv
q2_typical_trajectories_spin_factor_3d.png
q2_typical_trajectories_spin_factor_side.png
q2_typical_trajectories_spin_factor_top.png
```

灵敏度分析也分别运行两种模型，至少包括：

```text
parameter perturbation
wind
spin decay
solver tolerance
initial height
```

所有图片标题、CSV 和元数据必须写明模型名称。

---

## 9. P1：验证飞行距离定义

对每个 ODE 模型同时计算：

[
D_x=x_{\mathrm{land}}
]

和：

[
D_r=\sqrt{x_{\mathrm{land}}^2+y_{\mathrm{land}}^2}.
]

在固定测试集上分别计算：

```text
RMSE
MAE
MAPE
bias
```

生成：

```text
q2_carry_definition_comparison.csv
```

字段：

```text
model
carry_definition
rmse
mae
mape
bias
```

选择规则：

* 以测试前已经明确的题面或设备定义优先；
* 若题面不能确认，则以训练集拟合和物理定义为主要依据；
* 测试集比较仅作为结果诊断，不允许通过反复尝试复杂定义来调参。

`results.md` 必须明确说明最终采用前向距离还是水平欧氏距离。

---

## 10. P1：初始高度说明与敏感性

将配置中的：

```yaml
initial_height_m: 0.01
```

明确标记为：

```yaml
initial_height_m: 0.01
initial_height_type: numerical_convention
```

运行：

```text
0.001 m
0.01 m
0.05 m
```

比较对以下结果的影响：

```text
carry
apex
lateral offset
flight time
```

若影响很小，在论文中说明它只是避免初始落地事件的数值设置。

不得把 0.01 m 写成题面给定或实测击球高度。

---

## 11. P1：监督模型表述修正

保留通过训练集 CV 选择出的 HistGradientBoosting，不得根据固定测试集结果改选 ExtraTrees。

但在 `results.md` 中补充：

* 最高点任务中 HGB 和 ExtraTrees 性能接近；
* 固定测试集上 ExtraTrees 误差略低；
* 重复划分平均表现几乎相同；
* 最终根据预先规定的训练集 CV 规则选择 HGB。

将重复划分中的：

```text
win_frequency
```

表述为：

```text
split_comparison_win_frequency
```

不要称为嵌套模型选择胜率。

---

## 12. P1：扩展验证程序

修改：

```text
questions/q2/scripts/validate.py
```

新增检查。

### 配置接线

* 阻力代表样本数符合 drag 配置；
* 升力代表样本数符合 lift 配置；
* 实际网格点数与配置一致；
* 不允许读取错误配置段。

### 参数标定

* 局部优化至少有一次成功；
* 参数均位于边界内；
* 边界解产生明确警告；
* 训练参数标定不读取测试集；
* 完整训练集目标函数已记录。

### 模型用途

* 第二问主轨迹模型等于测试集表现最好的 ODE；
* 第三问兼容模型单独输出；
* 每个轨迹文件的模型字段唯一且正确；
* 图表元数据中的模型名与 CSV 一致。

### 风速

* 顺风向量的 (x) 分量大于 0；
* 逆风向量的 (x) 分量小于 0；
* 总体平均距离变化方向合理。

### 指标复算

从预测明细重新计算：

```text
RMSE
MAE
MAPE
R²
```

并与汇总表比较，允许浮点容差。

### 状态同步

检查：

```text
questions/q2/README.md
questions/q2/manifest.yaml
README.md
```

三处状态一致。

验证失败时返回非零退出码。

---

## 13. P1：补充运行元数据

`run_metadata.json` 至少增加：

```json
{
  "git_commit": "",
  "data_path": "",
  "data_sha256": "",
  "config_path": "",
  "config_sha256": "",
  "python_version": "",
  "package_versions": {},
  "train_ids_sha256": "",
  "test_ids_sha256": "",
  "drag_calibration_record_ids": [],
  "lift_calibration_record_ids": [],
  "best_fit_ode_model": "",
  "q3_compatible_ode_model": "",
  "optimization_runs": {}
}
```

所有参数结果必须能够追溯到：

* 数据版本；
* 配置版本；
* Git commit；
* 代表样本；
* 优化算法和初值。

---

## 14. 重新生成的主要产物

至少重新生成：

```text
q2_drag_calibration_records.csv
q2_lift_calibration_records.csv
q2_drag_optimization_runs.csv
q2_constant_lift_optimization_runs.csv
q2_spin_factor_optimization_runs.csv
q2_ode_parameters.csv
q2_ode_model_comparison.csv
q2_ode_test_predictions.csv
q2_ode_test_metrics.csv
q2_carry_definition_comparison.csv
q2_ode_sensitivity.csv
q2_validation_checks.csv
run_metadata.json
```

典型轨迹分别生成 constant-lift 和 spin-factor 两套。

旧结果若保留，必须移入：

```text
questions/q2/artifacts/archive/
```

不得让旧文件和新文件具有相同的“最终结果”含义。

---

## 15. 执行命令

```bash
python questions/q2/scripts/pipeline.py \
  --config configs/default.yaml
```

然后：

```bash
python questions/q2/scripts/validate.py \
  --config configs/default.yaml
```

再次运行完整流水线：

```bash
python questions/q2/scripts/pipeline.py \
  --config configs/default.yaml
```

验证相同随机种子下：

* 固定测试集不变；
* 代表样本编号不变；
* 参数结果在数值容差内一致；
* 主要 CSV 哈希一致。

---

## 16. 完成标准

以下条件全部满足后，第二问才能标记为 `done`：

* drag 配置确实被阻力标定读取；
* 阻力和升力使用各自的代表样本数及网格设置；
* ODE 参数经过粗搜索和局部优化；
* 参数边界状态明确；
* 顺风和逆风方向已经修正；
* 灵敏度产物已经重跑；
* constant-lift 和 spin-factor 的角色分开；
* 第二问主轨迹使用最佳拟合 ODE；
* 第三问兼容轨迹单独输出；
* 两种飞行距离定义已经比较；
* 初始高度性质和敏感性已经说明；
* 验证程序能够发现配置接线错误和风向错误；
* 指标可以从预测明细复算；
* Git、数据和配置哈希已记录；
* 根 README、q2 README 和 manifest 状态一致；
* 同一配置重复运行结果可复现。

---

## 17. 推荐提交顺序

```text
fix(q2): wire drag calibration configuration correctly
```

```text
feat(q2): refine ode parameters with bounded optimization
```

```text
fix(q2): correct headwind and tailwind directions
```

```text
feat(q2): separate best-fit and q3-compatible trajectories
```

```text
feat(q2): validate carry definitions and initial height
```

```text
test(q2): expand calibration and sensitivity validation
```

```text
docs(q2): publish recalibrated results and sync status
```

---

## 18. 完成后返回内容

向上级 Agent 返回：

```text
1. 修改文件列表
2. 修复的配置接线问题
3. 阻力和升力代表样本数量
4. 粗搜索与局部优化方法
5. 修正前后的 ODE 参数
6. 修正前后的测试集指标
7. 参数是否仍位于边界
8. 两种飞行距离定义比较
9. constant-lift 与 spin-factor 的用途
10. 修正后的顺逆风灵敏度
11. 验证结果
12. 尚未解决的模型局限
13. Git commit
```
