# q2 - 飞行轨迹预测

- 状态：`done`
- 入口：`python questions/q2/scripts/pipeline.py --config configs/default.yaml`
- 验证：`python questions/q2/scripts/validate.py --config configs/default.yaml`
- 上游：q1 清洗数据与特征审计结果

## 目标

第二问同时完成两类模型：

- 监督预测模型：预测 `carry_distance_yd` 和 `apex_height_yd`，固定 70%/30% 划分，训练集内选模，测试集只报告最终指标。
- 三维 ODE 模型：实现 `vacuum`、`drag`、`constant_lift`、`spin_factor_lift`，使用训练集代表样本标定参数，并在固定测试集评估。

## task4 后关键结果

- 固定划分：train=514，test=221，random_seed=2026。
- 监督模型：两个目标均由 `launch_state_model / hist_gradient_boosting` 在训练集 CV 中胜出。
- 监督测试指标：
  - carry RMSE=8.337 yd，MAPE=4.986%。
  - apex RMSE=1.739 yd，MAPE=14.335%。
- ODE 标定：
  - drag 代表样本 36 条，粗网格 10 点。
  - lift 代表样本 24 条，粗网格 6x6。
  - 参数经粗网格 + 有界局部优化获得；局部优化真实记录 `optimizer_success/objective_finite/accepted`，选中运行均无标定和全训练集积分失败。
- ODE 求解器：
  - 正式积分时间上限由 `q2.ode.solver.max_flight_time_s=20.0` 配置控制。
  - 超过时间上限仍未触地时记录 `integration_status=time_horizon_exceeded`，不得作为成功积分参与最终参数选择。
- ODE 参数：
  - drag: `C_D=0.05`，边界解，仅作 drag-only 基线。
  - constant_lift: `C_D=0.238654, C_L=0.203952`。
  - spin_factor_lift: `C_D=0.050059, k_L=0.151837`。
- 主 carry 定义固定为 `forward_x`，即前向距离 `D_x=x_land`。
- ODE 测试集 D_x carry RMSE：
  - vacuum=32.502 yd
  - drag=36.830 yd
  - constant_lift=7.157 yd
  - spin_factor_lift=30.530 yd
- 第二问 best-fit ODE 由完整训练集目标自动确定为 `constant_lift`；第三问兼容接口单独输出 `spin_factor_lift`。
- `spin_factor_lift` 通过 16 个边界组合稳定性检查，最大飞行时间 8.611 s、最大最高点 93.551 yd、最大横向距离 152.335 yd。

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
python -m pytest tests/test_q2_q3_integration.py -q
python -m pytest tests/test_q2_task4_final_remediation.py -q
python -m pytest tests/test_q2_task3_recalibration.py -q
```
