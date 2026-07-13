# q3 解法方案：最优击球策略

## 0. 最终执行口径

- 主优化器为 q2 carry 监督模型 + q3 lateral 监督模型，目标函数为 $\sqrt{(\hat D-200)^2+\hat L^2}$。
- lateral 模型使用 q2 固定训练集训练、固定测试集评价，按训练集 5 折 CV RMSE 选模。
- 搜索证据由最佳观测训练记录、20,000 点 LHS 基线、5 个随机种子的差分进化和每个 DE 解附近 5,000 点局部 LHS 组成。
- 训练支持区使用 q2 训练集四维发射状态空间 kNN 距离计算，并额外检查五维模型输入支持区；最终推荐必须为 `supported`。
- 稳健性分析覆盖全部 supported near-optimal 候选（本轮为 482 个），使用共同随机数、p90 bootstrap 区间和 `ideal`/`stable_player`/`ordinary_player` 发射方向扰动场景。
- 最终论文推荐由 stable_player 场景下的联合模型-参数 p90 选择；单代理参数稳健解只作为比较和历史兼容输出。
- 195/200/205 yd 目标距离必须分别独立重优化，不复用 200 yd 候选池。
- `constant_lift` 和 `spin_factor_lift` ODE 只用于交叉检查与轨迹图，不作为主优化器，也不写成真实击球实验验证。
- 扰动范围为情景假设；联合稳健性模拟比例不能写成真实球员命中概率，论文中必须保留模型分歧和非唯一性局限。

## 1. 题意解释

- 原题要求：假设球员距离洞口 200 yd，使用 q2 的预测模型或 ODE 模型，以落点与洞口欧氏距离最小为目标，求最优球速、发射角、自旋速率和自旋轴偏角，并绘制三维轨迹。
- 数学目标：在边界约束下求解 $u^*=\arg\min J(u)$，其中 $J(u)=\sqrt{(D_{carry}(u)-200)^2+L(u)^2}$。
- 输入：q2 模型、q2 单位换算和 ODE 参数、q3 决策变量边界。
- 输出：最优参数、预测飞行距离、横向偏移、目标函数值、最优轨迹。
- 评价指标：落点到洞口距离、边界可行性、扰动灵敏度、模型适用范围。
- 歧义与采用解释：主目标使用首次落地的飞行距离和横向偏移；总距离仅作为辅助诊断。

## 2. 符号、单位和约束

| 符号 | 含义 | 单位 | 范围 / 约束 |
|---|---|---|---|
| $u$ | 决策变量向量 | 混合 | $(v_0,\theta_0,\omega_0,\phi)$ |
| $v_0$ | 球速 | mph | $80\le v_0\le 140$ |
| $\theta_0$ | 发射角 | degree | $5\le\theta_0\le 30$ |
| $\omega_0$ | 自旋速率 | rpm | $1000\le\omega_0\le 10000$ |
| $\phi$ | 自旋轴偏角 | degree | $-30\le\phi\le 30$ |
| $D_{target}$ | 洞口距离 | yd | 200 |
| $L(u)$ | 横向偏移 | yd | 由模型预测 |
| $J(u)$ | 目标函数 | yd | 越小越优 |

## 3. 数据与预处理

- 数据来源：q2 模型产物和 `data/processed/golf_shots_clean.csv`。
- 质量问题：q3 可能在数据边界附近外推，需检查最优参数是否落在训练数据支持范围内。
- 缺失值：q3 决策变量均由优化器给定，不存在缺失；模型输入中的非决策字段需固定为合理值或由 q2 ODE 模型避免使用。
- 异常值：若最优解靠近异常训练样本区域，需要做局部扰动诊断。
- 单位与尺度：优化器可使用归一化变量，模型调用前转换回题目单位；ODE 内部转 SI。
- 防止泄漏：不能用 q3 目标手工调改 q2 模型参数。

## 4. 基线方案

- 方法：在给定边界内做粗网格或随机采样，取目标函数最小的参数组。
- 为什么适合作为基线：实现简单，能发现明显可行区域，并为局部优化提供初值。
- 预期指标：基线最小落点距离和对应参数，作为主优化算法对照。

## 5. 候选模型

| 模型 | 适配性 | 假设 | 优点 | 风险 | 是否采用 |
|---|---|---|---|---|---|
| 粗网格/随机采样 | 黑箱优化基线 | 采样足够覆盖空间 | 简单稳健 | 精度有限 | adopt-baseline |
| 差分进化 | 非凸边界优化 | 目标可重复计算 | 全局搜索能力较强 | 计算量大 | candidate |
| 多起点局部优化 | 平滑目标精修 | 局部可微或近似平滑 | 收敛快 | 依赖初值 | candidate |
| 贝叶斯优化 | 昂贵黑箱优化 | 代理模型有效 | 减少模型调用 | 实现复杂 | fallback |

## 6. 主模型

- 数学定义：目标函数 $J(u)$ 由 q2 模型输出的飞行距离和横向偏移组成。
- 目标函数 / 损失：$J(u)=\sqrt{(D_{carry}(u)-200)^2+L(u)^2}$，单位 yd。
- 约束：所有变量满足题面上下界；若使用监督模型，最优点需检查是否超出训练数据分布。
- 参数来源：边界来自题面；q2 模型参数来自 q2 证据链；优化随机种子来自配置。
- 求解算法：先全局采样/差分进化，再用局部优化精修；最终复算一次 ODE 或监督模型输出。
- 复杂度：四维连续优化，主要成本来自 q2 模型调用；ODE 模型需限制迭代。

## 7. 验证与诊断

- 基线比较：主优化结果 vs 粗网格/随机采样最好结果。
- 主验证方法：约束可行性检查、多起点重复、目标函数复算、稳健候选池覆盖、共同随机数扰动、联合模型-参数稳健性、目标距离独立重优化和 full-input support 检查。
- 通过标准：最优结果可复现，目标值优于基线，参数不依赖单一随机初值。
- 失败案例：若最优解总在边界，需报告边界驱动现象并检查模型外推风险。

## 8. 灵敏度与不确定性

- 关键参数：q2/q3 代理模型选择、决策变量扰动、发射方向扰动、变量边界和目标距离。
- 扰动范围：决策变量小扰动；发射方向按 `ideal=0.0 deg`、`stable_player=0.5 deg`、`ordinary_player=1.0 deg` 三种情景；目标距离为 195/200/205 yd。
- 稳健性指标：mean/median/p90/p95 miss distance、p90 CI、within 3/5 yd 模拟比例、out-of-support fraction、模型成员间 objective prediction std。
- 非唯一性指标：近优候选参数分位范围、不同预测落点数量和最大预测平台规模。

## 9. 计划产物

| 产物 ID | 类型 | 内容 | 生成脚本 | 数据文件 |
|---|---|---|---|---|
| q3-T01 | table | 最优击球参数和目标函数值 | `questions/q3/scripts/pipeline.py` | `questions/q3/artifacts/tables/q3_optimal_parameters.csv` |
| q3-T02 | table | 依赖审计与横向模型评价 | `questions/q3/scripts/pipeline.py` | `questions/q3/artifacts/tables/q3_dependency_audit.csv`、`q3_lateral_model_metrics.csv` |
| q3-T03 | table | 稳健候选池与参数扰动稳健性 | `questions/q3/scripts/pipeline.py` | `questions/q3/artifacts/tables/q3_robust_candidate_pool.csv`、`q3_parameter_robustness.csv` |
| q3-T04 | table | 联合模型-参数稳健性 | `questions/q3/scripts/pipeline.py` | `questions/q3/artifacts/tables/q3_joint_robustness_summary.csv` |
| q3-T05 | table | 195/200/205 yd 目标距离独立重优化 | `questions/q3/scripts/pipeline.py` | `questions/q3/artifacts/tables/q3_target_optimal_parameters.csv` |
| q3-T06 | table | 近优参数范围与非唯一性 | `questions/q3/scripts/pipeline.py` | `questions/q3/artifacts/tables/q3_near_optimal_parameter_ranges.csv` |
| q3-F01 | figure | 最优参数三维轨迹图 | `questions/q3/scripts/visualize.py` | `questions/q3/artifacts/figure_data/q3_optimal_trajectory.csv` |
| q3-F02 | figure | 目标函数局部等高线或切片图 | `questions/q3/scripts/visualize.py` | `questions/q3/artifacts/figure_data/q3_objective_slice.csv` |

## 10. 备用方案与停止条件

- 主模型失败时：用粗网格最优结果作为保守策略，不声称连续全局最优。
- 计算超时处理：降低全局搜索样本数，或先用监督模型搜索再用 ODE 复核。
- 数据不足处理：若 q2 模型外推风险高，限制优化边界到训练数据分位范围并说明。
