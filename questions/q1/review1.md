# 数学建模项目第一问整改与复现任务书

## 1. 项目位置

项目仓库：

```text
https://github.com/feiniao87968492/shixun2
```

本次仅处理第一问：

```text
questions/q1/
```

重点文件：

```text
questions/q1/approach.md
questions/q1/results.md
questions/q1/scripts/pipeline.py
questions/q1/scripts/validate.py
questions/q1/scripts/visualize.py

questions/q1/artifacts/tables/
questions/q1/artifacts/figures/

data/processed/golf_shots_clean.csv
configs/default.yaml
```

---

# 2. 总体目标

对第一问现有结果进行整改，使其满足以下要求：

1. 所有结果都能够由仓库中的正式代码重新生成；
2. 修正杆头速度和攻击角中的异常零值；
3. 统一数据处理、模型训练、验证和绘图流程；
4. 重新计算相关性、回归重要性和非线性模型重要性；
5. 修正当前综合排名方法存在的偏差；
6. 明确区分边际相关性、条件贡献和非线性预测贡献；
7. 生成完整、可审计、可复现的结果文件；
8. 更新第一问文档，使文档结论与实际结果严格一致。

不得只修改 Markdown 结论，必须真正修改代码并重跑结果。

---

# 3. 当前已知问题

## 3.1 正式脚本没有实现

当前以下文件仍为脚手架或占位程序：

```text
questions/q1/scripts/pipeline.py
questions/q1/scripts/validate.py
questions/q1/scripts/visualize.py
```

但 `results.md` 中已经声称完成分析。

必须将真实分析逻辑整理并提交到正式脚本中，不能依赖仓库外的临时代码、Notebook 或人工生成结果。

---

## 3.2 三条明显异常零值

数据中存在三条记录同时满足：

```text
杆头速度 = 0
攻击角 = 0
球速约为 108–113 mph
飞行距离约为 126–163 yd
```

这种记录不可能表示真实击球。

处理原则：

```python
club_head_speed == 0  -> NaN
attack_angle == 0     -> NaN
```

但不能把所有变量中的 0 都当成缺失，只处理经过明确确认的这两个字段。

需要在数据审计结果中记录：

* 原始缺失数；
* 异常零值数量；
* 修正后的缺失数；
* 受影响的样本编号。

预计修正后：

```text
杆头速度有效样本数：672 -> 669
杆头速度缺失数：63 -> 66

攻击角有效样本数：670 -> 667
攻击角缺失数：65 -> 68
```

具体数值以程序重新计算结果为准。

---

## 3.3 当前“验证通过”只检查文件存在

现有验证结果主要检查 CSV、PNG 和 JSON 是否存在，没有真正验证数值。

新的验证程序必须检查：

* 样本数是否正确；
* 输入输出字段是否完整；
* 是否存在 NaN、Inf 或非法字符串；
* 相关系数是否在 ([-1,1])；
* 排名是否连续且与排序结果一致；
* 图表对应的数据文件是否存在；
* 配置参数是否记录；
* 同一随机种子运行结果是否一致；
* 结果文件是否由当前代码生成；
* 输出表之间的样本数是否一致。

---

## 3.4 当前综合排名方法偏向边际相关性

当前聚合使用：

```text
Pearson
Spearman
岭回归
置换重要性
```

四项等权。

Pearson 和 Spearman 本质上都属于边际关联，因此这相当于让边际相关性占综合排名的一半，容易高估攻击角等变量。

必须修改为分层结论，不得将所有指标简单混成一个唯一排名。

---

# 4. 必须实现的代码结构

建议第一问脚本调整为：

```text
questions/q1/scripts/
├── pipeline.py
├── analysis.py
├── preprocessing.py
├── validate.py
└── visualize.py
```

如果不新增文件，也必须保证职责清晰。

---

## 4.1 `preprocessing.py`

职责：

1. 读取原始或处理后数据；
2. 检查必需字段；
3. 修正杆头速度和攻击角的异常零值；
4. 标记缺失值；
5. 检查重复样本；
6. 检查无穷值和非数值；
7. 生成不同分析样本口径；
8. 输出审计结果。

至少提供以下函数：

```python
load_data(...)
validate_schema(...)
replace_invalid_zero_values(...)
build_analysis_datasets(...)
generate_data_audit(...)
```

---

## 4.2 `analysis.py`

职责：

1. Pearson 相关性；
2. Spearman 相关性；
3. Bootstrap 置信区间；
4. 标准化岭回归；
5. 非线性模型；
6. 验证集置换重要性；
7. 排名稳定性；
8. 分组重要性；
9. 敏感性分析。

至少提供以下函数：

```python
compute_correlations(...)
bootstrap_correlations(...)
fit_ridge_cv(...)
fit_nonlinear_model(...)
compute_cv_permutation_importance(...)
compute_group_permutation_importance(...)
compute_rank_stability(...)
run_sensitivity_analysis(...)
```

---

## 4.3 `pipeline.py`

作为正式统一入口。

推荐运行方式：

```bash
python questions/q1/scripts/pipeline.py \
  --config configs/default.yaml
```

执行顺序：

1. 加载配置；
2. 加载数据；
3. 数据审计；
4. 修正异常零值；
5. 生成不同样本口径；
6. 计算相关性；
7. 计算 Bootstrap 区间；
8. 训练岭回归；
9. 训练非线性模型；
10. 计算置换重要性；
11. 计算分组重要性；
12. 执行敏感性分析；
13. 生成结论表；
14. 调用绘图程序；
15. 调用验证程序；
16. 写入运行元数据。

程序运行失败时必须返回非零退出码。

不得保留：

```python
IMPLEMENTED = False
```

或任何“当前仅为 scaffold”的逻辑。

---

## 4.4 `visualize.py`

正式生成以下图表：

```text
q1_pearson_heatmap.png
q1_spearman_heatmap.png
q1_top_feature_relationships.png
q1_raw_importance_comparison.png
q1_rank_stability.png
q1_group_importance.png
q1_sensitivity_comparison.png
```

每张图必须对应一个生图数据 CSV。

例如：

```text
q1_raw_importance_comparison.csv
q1_rank_stability_plot_data.csv
```

不得只保存 PNG 而不保存原始生图数据。

---

## 4.5 `validate.py`

提供独立入口：

```bash
python questions/q1/scripts/validate.py \
  --config configs/default.yaml
```

验证失败时：

* 输出失败原因；
* 返回非零退出码；
* 不允许仍然写“validation passed”。

---

# 5. 数据样本口径

必须至少建立三套样本。

## S1：核心变量样本

不包含缺失严重的：

```text
杆头速度
攻击角
```

使用其他核心变量和全部可用记录。

用途：

* 主相关性分析；
* 核心变量模型；
* 避免由于两列缺失导致大量样本损失。

---

## S2：完整样本

仅使用所有输入变量均非缺失的记录。

用途：

* 在统一样本上比较所有变量；
* 作为综合判断的重要依据。

禁止在这里保留杆头速度和攻击角的异常零值。

---

## S3：插补样本

对杆头速度和攻击角进行中位数插补。

要求：

* 插补必须在每一个交叉验证训练折内完成；
* 不得在划分训练集之前对全体数据插补；
* 增加缺失指示变量：

```text
club_head_speed_missing
attack_angle_missing
```

用途：

* 全样本建模；
* 敏感性分析。

---

# 6. 自旋变量处理

以下变量存在结构性重复：

```text
自旋速率
自旋轴偏角
后旋
侧旋
```

相关性矩阵中可以同时展示四个变量。

多变量模型中不得将四个变量全部同时作为主模型输入。

必须分别建立：

## 表示方案 A

```text
自旋速率
自旋轴偏角
```

## 表示方案 B

```text
后旋
侧旋
```

比较：

* 交叉验证 RMSE；
* 交叉验证 MAE；
* (R^2)；
* 各变量重要性稳定性；
* 两套方案排名差异。

最终选择表现更稳定的一套作为主模型，另一套作为敏感性分析。

---

# 7. 相关性分析要求

目标输出变量：

```text
飞行距离
最高点高度
总距离
横向偏移
```

输入变量：

```text
球速
发射角
发射方向
自旋速率
自旋轴偏角
后旋
侧旋
杆头速度
攻击角
```

对每一组输入—输出组合计算：

* Pearson 系数；
* Spearman 系数；
* 有效样本数；
* Bootstrap 95% 置信区间。

Bootstrap 建议：

```yaml
bootstrap_iterations: 1000
confidence_level: 0.95
random_seed: 固定读取配置
```

最终表格至少包含：

```text
feature
target
n
pearson
pearson_ci_low
pearson_ci_high
spearman
spearman_ci_low
spearman_ci_high
```

---

# 8. 飞行距离影响分析

必须区分以下三类结果。

## 8.1 边际关联

回答：

> 单独观察该变量时，它和飞行距离的关系有多强？

使用：

```text
Pearson
Spearman
```

这里可以给出边际关联排名。

---

## 8.2 条件线性贡献

回答：

> 控制其他变量后，该变量在线性模型中还保留多少贡献？

使用标准化岭回归。

要求：

* 所有连续输入标准化；
* 通过交叉验证选择正则化参数；
* 报告系数方向和绝对值；
* 报告交叉验证均值和标准差；
* 不得直接使用普通最小二乘回归作为主排序依据。

输出至少包括：

```text
feature
ridge_coef_mean
ridge_coef_std
ridge_abs_rank
direction
```

---

## 8.3 非线性预测贡献

建立至少一个非线性模型。

推荐：

```text
ExtraTreesRegressor
```

可以增加：

```text
RandomForestRegressor
HistGradientBoostingRegressor
```

但不要为了增加模型而增加模型。

模型比较指标：

```text
RMSE
MAE
R²
```

使用重复交叉验证：

```yaml
cv_folds: 5
cv_repeats: 5
```

变量重要性必须使用验证集置换重要性，禁止直接使用：

```python
model.feature_importances_
```

作为最终重要性。

输出：

```text
feature
permutation_importance_mean
permutation_importance_std
permutation_rank
positive_frequency
```

---

# 9. 综合结论规则

不要再使用单一四项等权综合排名作为唯一结论。

应分别输出三个榜单：

```text
边际关联排名
条件线性贡献排名
非线性预测贡献排名
```

另外输出一个“稳定性分类”，而不是强行得到唯一顺序。

建议规则：

## 稳定关键因素

满足多数条件：

* 边际关联排名靠前；
* 岭回归排名靠前；
* 置换重要性排名靠前；
* Bootstrap 排名区间较窄；
* 多种样本口径下排名稳定。

## 结构性重要因素

满足：

* Pearson 或 Spearman 不高；
* 但非线性置换重要性明显较高；
* 散点趋势存在 U 型、倒 U 型或其他非线性结构。

发射角很可能属于这一类。

## 次要因素

* 有一定相关性；
* 但控制其他变量后贡献减弱；
* 或只在部分模型中重要。

## 不稳定因素

* 方向在不同方法中发生变化；
* 排名区间较宽；
* 对缺失处理或样本口径敏感。

攻击角可能属于这一类，必须以重跑结果确认。

## 弱关联因素

* 多数方法中均靠后；
* 置信区间接近 0；
* 打乱后模型误差变化很小。

---

# 10. 攻击角结论特别要求

不能直接把攻击角写成“稳定关键因素”。

当前已观察到的现象是：

```text
Pearson：弱正相关
Spearman：弱正相关
岭回归：可能为负
置换重要性：较低
```

重跑后需要检查：

1. 修正异常零值后结果是否变化；
2. 条件系数方向是否仍然为负；
3. 置换重要性是否仍处于后列；
4. 不同样本口径下是否稳定。

若上述现象仍成立，应表述为：

> 攻击角与飞行距离存在弱边际正相关，但在控制其他变量后，其独立贡献较弱，效应方向和排名具有一定不稳定性。

---

# 11. 杆头速度结论特别要求

修正异常零值后，重新计算：

```text
Pearson
Spearman
Bootstrap 区间
岭回归系数
置换重要性
```

需要重点解释杆头速度与球速之间的信息重叠。

建议增加：

```text
球速与杆头速度相关系数
只使用杆头速度的模型
只使用球速的模型
同时使用二者的模型
```

比较三种模型的交叉验证表现。

结论应区分：

* 杆头速度的边际关联较强；
* 控制球速后，额外预测贡献可能下降；
* 不能把边际相关直接解释为完全独立作用。

---

# 12. 发射角非线性分析

必须为发射角生成：

```text
发射角—飞行距离散点图
LOWESS 趋势线或分箱均值曲线
```

如果呈倒 U 型，应补充一个简单可解释模型：

[
D=\beta_0+\beta_1\theta+\beta_2\theta^2+\varepsilon
]

其中：

```text
D：飞行距离
θ：发射角
```

比较：

```text
仅线性项模型
包含二次项模型
```

使用交叉验证判断二次项是否明显改善预测。

如果二次项有效，可以估计样本范围内的经验最优发射角：

[
\theta^\ast=-\frac{\beta_1}{2\beta_2}
]

但必须说明：

* 这是数据样本中的统计最优位置；
* 不是严格的物理最优值；
* 不代表对所有球速和自旋条件都适用。

---

# 13. 分组重要性

增加物理变量组分析。

建议分组：

| 分组    | 变量           |
| ----- | ------------ |
| 速度组   | 球速、杆头速度      |
| 发射姿态组 | 发射角、攻击角      |
| 水平方向组 | 发射方向         |
| 自旋组   | 自旋方案 A 或方案 B |

使用整组置换重要性。

输出：

```text
group
importance_mean
importance_std
rank
```

分组重要性用于解释：

> 飞行距离主要依赖速度、发射姿态还是自旋状态。

不能用分组排名替代题目要求的单变量分析。

---

# 14. 异常值敏感性

现有 `trim_1pct` 从 735 条降至约 559 条，删除比例约 24%，不能再简单称为“去除上下 1%”。

必须明确记录：

```text
原样本数
处理后样本数
删除比例
每项规则导致的删除数
```

建议使用以下场景：

## 场景 A：原始样本

不删除极端值，只修正明确错误零值。

## 场景 B：Winsorize

对连续变量按 1% 和 99% 分位缩尾，不删除整行。

## 场景 C：目标变量缩尾

只对飞行距离进行缩尾或排除极端值。

## 场景 D：多变量联合截断

保留现有联合规则，但明确说明它删除了多少样本。

不允许把场景 D 当作唯一异常值方案。

---

# 15. 结果输出文件

重新生成以下文件。

## 数据审计

```text
questions/q1/artifacts/tables/q1_data_audit.csv
questions/q1/artifacts/tables/q1_missing_audit.csv
questions/q1/artifacts/tables/q1_invalid_zero_records.csv
questions/q1/artifacts/tables/q1_outlier_audit.csv
```

## 相关性

```text
questions/q1/artifacts/tables/q1_pearson_correlation.csv
questions/q1/artifacts/tables/q1_spearman_correlation.csv
questions/q1/artifacts/tables/q1_correlation_confidence_intervals.csv
```

## 模型

```text
questions/q1/artifacts/tables/q1_model_performance.csv
questions/q1/artifacts/tables/q1_ridge_coefficients.csv
questions/q1/artifacts/tables/q1_permutation_importance.csv
questions/q1/artifacts/tables/q1_group_importance.csv
```

## 稳定性

```text
questions/q1/artifacts/tables/q1_rank_stability.csv
questions/q1/artifacts/tables/q1_sensitivity_comparison.csv
questions/q1/artifacts/tables/q1_spin_representation_comparison.csv
questions/q1/artifacts/tables/q1_sample_definition_comparison.csv
```

## 总结

```text
questions/q1/artifacts/tables/q1_feature_summary.csv
questions/q1/artifacts/tables/q1_validation_checks.csv
```

---

# 16. 元数据要求

每次运行生成：

```text
questions/q1/artifacts/run_metadata.json
```

至少记录：

```json
{
  "timestamp": "",
  "git_commit": "",
  "data_path": "",
  "data_hash": "",
  "config_path": "",
  "config_hash": "",
  "random_seed": 0,
  "python_version": "",
  "package_versions": {},
  "sample_sizes": {},
  "invalid_zero_corrections": {},
  "selected_spin_representation": "",
  "selected_nonlinear_model": ""
}
```

所有图表可以各自有 `.meta.json`，但至少要有一个完整运行级元数据文件。

---

# 17. 配置文件要求

将以下参数放入：

```text
configs/default.yaml
```

建议结构：

```yaml
q1:
  input_path: data/processed/golf_shots_clean.csv
  output_dir: questions/q1/artifacts

  random_seed: 42

  invalid_zero_rules:
    club_head_speed: true
    attack_angle: true

  bootstrap:
    iterations: 1000
    confidence_level: 0.95

  cross_validation:
    folds: 5
    repeats: 5

  ridge:
    alphas:
      - 0.001
      - 0.01
      - 0.1
      - 1
      - 10
      - 100

  permutation_importance:
    repeats: 30

  outlier_analysis:
    lower_quantile: 0.01
    upper_quantile: 0.99

  plotting:
    dpi: 300
```

不得在脚本中散落大量魔法数字。

---

# 18. 验收测试

本地 Agent 完成后必须执行以下命令。

```bash
python questions/q1/scripts/pipeline.py \
  --config configs/default.yaml
```

然后执行：

```bash
python questions/q1/scripts/validate.py \
  --config configs/default.yaml
```

最后再次运行：

```bash
python questions/q1/scripts/pipeline.py \
  --config configs/default.yaml
```

检查相同随机种子下关键 CSV 是否一致。

至少验证：

## 数据测试

* 原始行数正确；
* 样本编号唯一；
* 两个异常零值字段得到正确处理；
* 没有无穷值；
* 主要结果中没有无法解释的 NaN；
* S1、S2、S3 样本数记录完整。

## 相关性测试

* 所有相关系数位于 ([-1,1])；
* 每项结果有有效样本数；
* Bootstrap 下界不大于上界；
* 球速与飞行距离应保持明显正相关；
* 修正零值后杆头速度 Pearson 应显著高于修正前约 0.469 的结果。

最后一项只作为合理性检查，不得将约 0.581 写死成单元测试精确值。

## 模型测试

* 岭回归交叉验证正常完成；
* 插补和标准化只在训练折内拟合；
* 模型指标不是 NaN；
* 置换重要性来自验证集；
* 同一随机种子结果可复现。

## 排名测试

* 排名与对应指标排序一致；
* 并列结果不得被强制写成虚假顺序；
* 稳定性等级必须由明确规则产生；
* 文档中的 Top 因素与 CSV 保持一致。

## 文件测试

* 所有预期 CSV 存在且非空；
* 所有 PNG 存在且可读取；
* 每张图对应生图数据；
* 元数据文件存在；
* 文档中的文件名全部真实存在。

---

# 19. 文档修改要求

完成代码和结果重跑后，更新：

```text
questions/q1/approach.md
questions/q1/results.md
questions/q1/experiments.md
questions/q1/README.md
项目根目录 README.md
```

---

## 19.1 `approach.md`

补充：

* 异常零值处理规则；
* S1、S2、S3 样本定义；
* 两套自旋表示；
* 数据泄漏防止方式；
* 三类重要性定义；
* 稳定性分类规则；
* 异常值敏感性方案。

---

## 19.2 `results.md`

必须基于重新生成的结果编写。

结构建议：

```text
1. 数据质量与异常修正
2. 输入与输出相关性
3. 飞行距离边际关联
4. 条件线性贡献
5. 非线性预测贡献
6. 分组重要性
7. 排名稳定性
8. 敏感性分析
9. 第一问最终结论
10. 局限性
```

禁止继续写：

```text
攻击角是稳定关键因素
```

除非重新运行后有充分结果支持。

禁止把并列第三写成明确的第三、第四、第五。

---

## 19.3 `experiments.md`

记录每次实验：

```text
实验编号
时间
Git commit
数据版本
配置
样本口径
自旋表示
模型
主要指标
结论
是否保留
```

---

# 20. 建议最终结论形式

第一问最终不要只给一个简单 Top 5。

建议使用下表：

| 变量     | 边际关联  | 条件线性贡献 | 非线性贡献 | 稳定性 | 最终解释           |
| ------ | ----- | ------ | ----- | --- | -------------- |
| 球速     | 强     | 强      | 强     | 高   | 最稳定的首要因素       |
| 杆头速度   | 较强    | 中等或偏弱  | 中等    | 中高  | 与球速存在信息重叠      |
| 发射角    | 弱线性   | 中等     | 较强    | 中高  | 具有明显非线性结构      |
| 攻击角    | 弱     | 不稳定    | 较弱    | 中低  | 边际相关但独立贡献有限    |
| 自旋相关变量 | 因指标而异 | 因表示而异  | 中等    | 需检验 | 对高度、方向或偏移可能更重要 |

表中具体等级必须由重跑结果填写，不能直接照抄。

---

# 21. 提交要求

建议拆分为以下提交。

```text
fix(q1): treat invalid zero measurements as missing
```

```text
feat(q1): implement reproducible analysis pipeline
```

```text
feat(q1): add correlation and model validation
```

```text
feat(q1): add stability and sensitivity analysis
```

```text
docs(q1): update results from reproducible pipeline
```

每次提交后应保证项目仍可运行。

---

# 22. 禁止事项

本次整改过程中禁止：

1. 只改结果文档，不改正式代码；
2. 继续保留不可执行的脚手架；
3. 使用仓库外未提交脚本生成最终结果；
4. 在全体数据上先插补、再交叉验证；
5. 将训练集置换重要性当作验证集重要性；
6. 将树模型原生 `feature_importances_` 作为最终结论；
7. 将 Pearson 和 Spearman 当作两个完全独立证据重复加权；
8. 将相关性解释成因果关系；
9. 隐藏异常值处理后实际删除的样本比例；
10. 人为打破并列排名；
11. 输出没有对应 CSV 数据的图；
12. 在验证失败的情况下生成“验证通过”结论。

---

# 23. 完成标准

只有满足以下全部条件，第一问才能标记为完成：

* 正式入口可以从数据重新生成全部结果；
* 两个异常零值字段已经修正；
* 数据审计结果完整；
* 三种样本口径均已运行；
* 两套自旋表示均已比较；
* 相关性带有有效样本数和 Bootstrap 区间；
* 岭回归通过交叉验证；
* 非线性模型使用验证集置换重要性；
* 分组重要性已完成；
* 稳定性和敏感性分析已完成；
* 验证脚本检查真实数值而非仅检查文件存在；
* 同一随机种子可以复现；
* 图、表、生图数据、配置和元数据完整；
* `results.md` 与 CSV 结果严格一致；
* 项目 README 中第一问状态已同步；
* 不再存在未实现占位程序。

完成后向上级 Agent 返回以下内容：

```text
1. 修改文件清单
2. 核心数据清洗变化
3. 重新计算后的主要结果
4. 修正前后差异
5. 模型与参数
6. 验证结果
7. 尚未解决的问题
8. 对最终论文表述的建议
9. 对应 Git commit
```
