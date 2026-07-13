# q2 - 飞行轨迹预测

- 状态：`done`
- 入口：`python questions/q2/scripts/pipeline.py --config configs/default.yaml`
- 验证：`python questions/q2/scripts/validate.py --config configs/default.yaml`
- 上游：q1 清洗数据与特征审计结果

## 目标

第二问同时完成两类模型：

- 监督预测模型：预测 `carry_distance_yd` 和 `apex_height_yd`，固定 70%/30% 划分，训练集内选模，测试集只报告最终指标。
- 三维 ODE 模型：实现 `vacuum`、`drag`、`constant_lift`、`spin_factor_lift`，使用训练集代表样本标定参数，并在固定测试集评估。

## task3 后关键结果

- 固定划分：train=514，test=221，random_seed=2026。
- 监督模型：两个目标均由 `launch_state_model / hist_gradient_boosting` 在训练集 CV 中胜出。
- 监督测试指标：
  - carry RMSE=8.337 yd，MAPE=4.986%。
  - apex RMSE=1.739 yd，MAPE=14.335%。
- ODE 标定：
  - drag 代表样本 36 条，粗网格 10 点。
  - lift 代表样本 24 条，粗网格 6x6。
  - 参数经粗网格 + 有界局部优化获得。
- ODE 参数：
  - drag: `C_D=0.05`，边界解，仅作 drag-only 基线。
  - constant_lift: `C_D=0.27, C_L=0.18`。
  - spin_factor_lift: `C_D=0.49, k_L=1.6`。
- ODE 测试集 carry RMSE：
  - vacuum=32.233 yd
  - drag=36.465 yd
  - constant_lift=16.506 yd
  - spin_factor_lift=31.996 yd
- 第二问主轨迹使用 `constant_lift`；第三问兼容接口单独输出 `spin_factor_lift`。
- 最终采用前向距离 `D_x=x_land` 作为主 carry 定义。

## 主要产物

- 表格：`questions/q2/artifacts/tables/`
- 图：`questions/q2/artifacts/figures/`
- 生图数据与元信息：`questions/q2/artifacts/figure_data/`
- 监督模型：`questions/q2/artifacts/models/q2_carry_model.joblib`、`q2_apex_model.joblib`
- ODE 参数 JSON：`questions/q2/artifacts/models/q2_ode_parameters.json`
- 运行元数据：`questions/q2/artifacts/run_metadata.json`

## 复现命令

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
python questions/q2/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_task3_recalibration.py -q
```
