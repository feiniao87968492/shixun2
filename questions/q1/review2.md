# 第二次审查结论

第一问已经从“不可复现”修复到**基本可运行、主要结论可信**的状态。上次指出的两个阻断性问题已经解决：

* `pipeline.py` 已经接入正式分析流程，不再是 `IMPLEMENTED=False` 的占位程序。([GitHub][1])
* 三条“杆头速度和攻击角同时为 0”的异常记录已转为缺失值，修正后杆头速度缺失 66 条、攻击角缺失 68 条。([GitHub][2])
* ExtraTrees 的插补位于交叉验证训练流程内，置换重要性是在验证折上计算的，基本避免了数据泄漏。([GitHub][3])
* 结果文档不再把攻击角直接归为稳定关键因素，也开始区分边际关联、线性条件贡献和非线性贡献。([GitHub][4])

但目前还不能称为完全定稿。我建议状态标为：

> **第一问主体通过，存在 4 项必须整改和若干次要问题。**

---

## 一、当前主要结论可以保留

重新计算后的核心结果逻辑是合理的：

| 变量          | 当前判断                 |
| ----------- | -------------------- |
| 球速          | 最稳定、最重要的飞行距离关联因素     |
| 杆头速度        | 边际相关较强，但与球速存在较多信息重叠  |
| 发射角         | 线性相关较弱，但存在明显非线性贡献    |
| 攻击角         | 弱边际相关，独立预测贡献较低，稳定性不足 |
| 发射方向、自旋轴、侧旋 | 对横向偏移的作用比对飞行距离更明显    |

球速的 Pearson 约为 0.758、Spearman 约为 0.776，并且岭回归和置换重要性均排第一。杆头速度修正异常值后的 Pearson 上升到约 0.581。发射角在线性边际排名中不高，但岭回归和非线性置换重要性均排第二。([GitHub][5])

发射角二次模型的交叉验证 RMSE 从约 37.24 降到 34.64，估计的样本经验最优角度约为 17.89°。这个结果可以作为非线性证据，但应明确它只是当前样本中的经验结果。([GitHub][6])

---

# 二、必须整改的问题

## 1. `S3_imputed` 敏感性分析实际没有使用插补样本

这是目前最明确的代码错误。

敏感性分析中，S3 场景传入了 735 条记录，但在计算边际排名前又执行了类似：

```python
frame.dropna(subset=[features + target])
```

所以真正参与计算的仍然是完整案例，而不是插补后的 735 条样本。([GitHub][3])

输出表中却写着：

```text
S3_imputed  n = 735
```

而且它的排名结果与 S2 完整样本几乎完全相同，这也与代码行为一致。([GitHub][7])

### 应如何修改

S3 的相关性分析需要选择一个明确方案：

* 在训练折内插补后，只用于模型敏感性分析；
* 或单独生成一次明确标记为“描述性插补相关性”的数据集；
* 或干脆不对 Pearson、Spearman 做 S3 插补比较，只比较 S1 和 S2。

不能记录 735 条，却实际只使用完整案例。

这是 **P0 级别**，必须修复。

---

## 2. 球速与杆头速度的信息重叠实验使用了不同样本

当前三个模型的样本数是：

| 模型      | 样本数 |    RMSE |
| ------- | --: | ------: |
| 仅球速     | 735 | 约 24.32 |
| 仅杆头速度   | 669 | 约 30.34 |
| 球速＋杆头速度 | 669 | 约 24.42 |

([GitHub][8])

这样不能直接比较“加入杆头速度后是否改善模型”，因为：

* 仅球速模型使用 735 条；
* 双变量模型只使用 669 条；
* RMSE 差异可能来自样本不同，而不完全来自变量不同。

### 应如何修改

先取：

```python
speed_overlap_df = df[
    ["ball_speed", "club_speed", "carry_distance"]
].dropna()
```

然后三个模型全部在相同的 669 条记录、相同的交叉验证划分上运行：

1. 球速；
2. 杆头速度；
3. 球速＋杆头速度。

最好保存每一折的预测误差，使用配对比较判断加入杆头速度后误差是否稳定下降。

这是 **P0 级别**，因为它直接影响“杆头速度是否提供额外信息”的结论。

---

## 3. 分组重要性不够稳健

当前分组重要性存在三个问题：

* 只进行了一次训练集—测试集划分；
* 每组只产生一个重要性值；
* 所有组的 `importance_std` 都是 0。([GitHub][3])

此外，当前实现似乎分别随机打乱组内的每一列。这会破坏组内变量之间原有的联合结构。例如同时打乱球速和杆头速度时，两列之间的对应关系也被破坏，可能放大速度组的重要性。

### 应如何修改

使用与单变量重要性相同的重复交叉验证：

```text
5 折 × 5 次重复
每折进行 20～30 次组置换
```

对某一变量组置换时，使用同一行索引整体打乱该组：

```python
permutation = rng.permutation(len(X_valid))
X_permuted[group_columns] = X_valid[group_columns].iloc[permutation].to_numpy()
```

这样可以保留组内变量的联合关系，只破坏变量组与目标之间的联系。

输出：

```text
group
importance_mean
importance_std
positive_frequency
fold_count
```

当前分组重要性可以作为探索性结果，但暂时不要写成强结论。

---

## 4. “排名稳定性”实际上只验证了边际相关排名

当前 Bootstrap 排名稳定性是根据 Pearson 和 Spearman 的边际得分重采样计算的，没有重新拟合岭回归和 ExtraTrees。([GitHub][3])

但 `q1_feature_summary.csv` 又使用这套排名区间和 Top-3 频率来辅助判断变量整体稳定性。([GitHub][5])

因此当前字段名：

```text
rank_interval
top3_frequency
stability
```

容易让人误以为它表示四种方法的综合稳定性。

### 两种修复方式

#### 简单方案

重命名为：

```text
marginal_rank_interval
marginal_top3_frequency
marginal_rank_stability
```

并在文档中明确：

> 该稳定性只反映边际相关排名的 Bootstrap 稳定程度。

#### 完整方案

在每次 Bootstrap 中重新运行：

* Pearson；
* Spearman；
* 岭回归；
* 非线性置换重要性。

然后分别报告各方法排名分布。

考虑计算量，目前采用简单方案即可。

---

# 三、建议整改的问题

## 5. 岭回归的 `ridge_coef_std=0` 没有实际意义

当前岭回归是在全部样本上拟合一次，因此每个变量只有一个系数；输出表中的 `ridge_coef_std` 全为 0。([GitHub][3])

这不是“系数非常稳定”，而是“没有重复估计”。

建议二选一：

* 删除 `ridge_coef_std` 字段；
* 或在重复交叉验证的每个训练折中拟合 RidgeCV，再统计系数均值、标准差、正号比例和负号比例。

推荐第二种，因为它可以真正回答攻击角系数方向是否稳定。

---

## 6. 旧的综合排名文件与新结论冲突

仓库仍然保留：

```text
q1_feature_ranking.csv
```

它继续使用旧的四方法等权聚合，并把攻击角和杆头速度标记成 `stable_key`。([GitHub][9])

但新的：

```text
q1_feature_summary.csv
```

已经把：

* 球速归为 `stable_key`；
* 杆头速度归为 `secondary`；
* 攻击角归为 `unstable`；
* 发射角归为 `structural_nonlinear`。([GitHub][5])

同一仓库中存在两个互相冲突的最终结论文件，很容易在后续写论文或让 Agent 读取时用错。

### 建议

把旧文件改为：

```text
q1_legacy_equal_weight_ranking.csv
```

或者直接移入：

```text
questions/q1/artifacts/archive/
```

并在元数据中标记：

```text
deprecated: true
not_for_final_conclusion: true
```

最终论文只引用 `q1_feature_summary.csv`。

---

## 7. 自旋方案选择需要写得更清楚

当前预测结果显示：

* 自旋表示 B 的 ExtraTrees RMSE 约 8.23；
* 自旋表示 A 的 RMSE 约 8.48。

但最终把 A 选作主表示，理由是物理解释性更强。([GitHub][10])

这种选择可以接受，但文档中应明确：

> 方案 B 的纯预测精度略高；方案 A 因使用自旋速率和自旋轴偏角，物理解释更直接，因此用于主文分析，方案 B 用作敏感性验证。

不要表述成“方案 A 的模型效果最好”。

另外，当前方法汇总把两套互斥表示中的变量重要性放在同一个排名表中，容易造成横向比较误解。最好分别保存：

```text
q1_method_importance_spin_A.csv
q1_method_importance_spin_B.csv
```

主结论表以选定的方案 A 为基础。

---

## 8. 联合 1% 截断仍混入了缺失样本删除

当前联合截断从 735 条降到 558 条，删除 177 条，占约 24.08%。([GitHub][11])

代码在多个变量上依次构造分位区间掩码。对于缺失值，比较表达式返回 False，因此部分记录是因为缺失而被删除，不完全是因为处于 1% 极端区间。([GitHub][3])

建议把删除原因拆成：

| 原因               | 数量 |
| ---------------- | -: |
| 因杆头速度或攻击角缺失被排除   |  … |
| 因至少一个变量超出分位区间被排除 |  … |
| 两者同时存在           |  … |

或者联合截断只在统一完整样本 S2 内执行。

---

# 四、验证脚本评价

验证脚本已经比上一版完善很多，当前约有 62 项检查，包括：

* 文件存在；
* CSV 非空；
* 表结构；
* 数值范围；
* 样本数量；
* 哈希或元数据一致性。([GitHub][12])

但它没有发现上述 S3 样本错标、速度重叠样本不一致和分组重要性标准差为零等方法问题。

建议补充以下验证规则：

```text
S3 报告样本量必须等于实际参与计算的样本量
速度重叠三个模型必须使用相同 n 和相同 CV split
group importance 的 fold_count 必须大于 1
有 std 字段时，必须确实来自重复估计
deprecated 文件不得被 results.md 引用
最终分类不得与 feature_summary 冲突
```

---

# 五、最终验收状态

| 审查项目           | 当前状态             |
| -------------- | ---------------- |
| 正式分析入口         | 通过               |
| 异常零值处理         | 通过               |
| 基础相关性计算        | 通过               |
| Bootstrap 相关区间 | 通过               |
| 非线性模型交叉验证      | 通过               |
| 验证折置换重要性       | 通过               |
| 主要结论方向         | 通过               |
| S3 插补敏感性       | **不通过**          |
| 速度变量重叠比较       | **不通过**          |
| 分组重要性稳定性       | **不通过**          |
| 综合排名稳定性表述      | 需要修正             |
| 岭回归系数稳定性       | 需要修正             |
| 结果文件唯一性        | 需要清理             |
| 是否可以进入论文撰写     | **可以开始，但不应最终锁定** |

## 建议状态

```text
q1_status: conditionally_passed
```

修复前四项后，可以改为：

```text
q1_status: done
```

现阶段不需要重构整个第一问。重点只需修正：

1. S3 插补场景；
2. 速度重叠实验统一样本；
3. 分组重要性重复交叉验证；
4. 排名稳定性字段重命名或扩展；
5. 清理旧综合排名文件。

完成这些后，第一问的方法链条就基本足够支撑正式数学建模论文。

[1]: https://github.com/feiniao87968492/shixun2/blob/main/questions/q1/scripts/pipeline.py?plain=1&v=20260712 "shixun2/questions/q1/scripts/pipeline.py at main · feiniao87968492/shixun2 · GitHub"
[2]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_invalid_zero_records.csv "raw.githubusercontent.com"
[3]: https://github.com/feiniao87968492/shixun2/blob/main/questions/q1/scripts/analysis.py?plain=1&v=20260712 "shixun2/questions/q1/scripts/analysis.py at main · feiniao87968492/shixun2 · GitHub"
[4]: https://github.com/feiniao87968492/shixun2/blob/main/questions/q1/results.md?plain=1&v=20260712 "shixun2/questions/q1/results.md at main · feiniao87968492/shixun2 · GitHub"
[5]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_feature_summary.csv "raw.githubusercontent.com"
[6]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_launch_angle_quadratic.csv "raw.githubusercontent.com"
[7]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_sensitivity_comparison.csv "raw.githubusercontent.com"
[8]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_speed_overlap_models.csv "raw.githubusercontent.com"
[9]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_feature_ranking.csv "raw.githubusercontent.com"
[10]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_model_performance.csv "raw.githubusercontent.com"
[11]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_outlier_audit.csv "raw.githubusercontent.com"
[12]: https://raw.githubusercontent.com/feiniao87968492/shixun2/main/questions/q1/artifacts/tables/q1_validation_checks.csv "raw.githubusercontent.com"
