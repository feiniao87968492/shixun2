# q2 - 飞行轨迹预测

- 状态：`done`
- 入口：`python questions/q2/scripts/pipeline.py --config configs/default.yaml`
- 验证：`python questions/q2/scripts/validate.py --config configs/default.yaml`
- 上游：q1 清洗数据与特征审计结果

## 目标

第二问同时完成两类模型：

- 监督预测模型：预测 `carry_distance_yd` 和 `apex_height_yd`，固定 70%/30% 划分，训练集内选模，测试集只报告最终指标。
- 三维 ODE 模型：建立 `vacuum`、`drag`、`constant_lift`、`spin_factor_lift` 四层模型，使用训练集代表样本标定参数，并在固定测试集上评估。

## 关键结果

- 固定划分：train=514，test=221，random_seed=2026。
- 监督模型：两个目标均由 `launch_state_model / hist_gradient_boosting` 在训练 CV 中胜出。
- 测试指标：
  - carry RMSE=8.337 yd，MAPE=4.986%。
  - apex RMSE=1.739 yd，MAPE=14.335%。
- ODE 参数：
  - drag: `C_D=0.05`，位于下界，仅作为 drag-only 基线。
  - constant_lift: `C_D=0.27, C_L=0.18`。
  - spin_factor_lift: `C_D=0.27, k_L=0.8`。
- ODE 测试集 carry RMSE：
  - vacuum=32.233 yd
  - drag=36.465 yd
  - constant_lift=16.506 yd
  - spin_factor_lift=29.001 yd

## 主要产物

- 表格：`questions/q2/artifacts/tables/`
- 图：`questions/q2/artifacts/figures/`
- 生图数据与元信息：`questions/q2/artifacts/figure_data/`
- 模型文件：`questions/q2/artifacts/models/q2_carry_model.joblib`、`q2_apex_model.joblib`
- ODE 参数 JSON：`questions/q2/artifacts/models/q2_ode_parameters.json`

## 复现命令

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
python questions/q2/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_full_task2.py -q
```
