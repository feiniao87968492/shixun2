# 2026 年实训题2 高尔夫球飞行轨迹预测与最优击球策略建模

- 比赛 / 项目：课程实训
- 小问数量：3
- 初始化时间：2026-07-12T16:10:49+08:00
- 文档语言：zh-CN
- 当前状态：`q2_done`

## 项目目标

围绕高尔夫球飞行轨迹实测数据，建立从落点影响因素分析、飞行距离与最高点高度预测、三维动力学仿真到最优击球参数搜索的可复现建模流程。

## 快速开始

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/check_repo.py
python scripts/run_all.py --dry-run
```

## 目录

```text
configs/                 全局配置与随机种子
data/raw/                原始数据，只读且不入 Git
data/interim/            中间数据
data/processed/          可建模数据
docs/                    项目级建模文档、证据链和图表登记
questions/qN/            每个小问的方案、代码和产物
report/                  论文草稿
scripts/                 仓库级运行和审计脚本
src/modeling_common/     跨小问共享代码
tests/                   回归测试
```

## 运行约定

- 所有命令从仓库根目录执行。
- 每个小问的正式入口是 `questions/qN/scripts/pipeline.py`。
- 图和生图数据必须同名保存，并带 `.meta.json`。
- 最终结论必须登记到 `docs/evidence_chain.csv`。
- 原始题面与附件只保留在 `data/raw/problem/`，不提交到 Git。

## 当前小问

| 小问 | 状态 | 主要目标 | 入口 |
|---|---|---|---|
| q1 | done | 数据审计、异常 0 值修正、飞行距离影响因素分层解释、review2 方法审查修复 | `python questions/q1/scripts/pipeline.py --config configs/default.yaml` |
| q2 | done | 固定 70/30 划分、监督预测模型、四层 ODE 重标定、双角色轨迹、灵敏度与最终验收 | `python questions/q2/scripts/pipeline.py --config configs/default.yaml` |
| q3 | planned | 以 200 yd 目标为约束的最优击球参数搜索与轨迹绘制 | `python questions/q3/scripts/pipeline.py --dry-run` |

## Q1 复现与验证

```bash
python questions/q1/scripts/pipeline.py --config configs/default.yaml
python questions/q1/scripts/validate.py --config configs/default.yaml
```

第一问最终解释以 `questions/q1/artifacts/tables/q1_feature_summary.csv` 为准：球速是飞行距离最稳定的关键关联因素；杆头速度与球速信息重叠；发射角具有结构性非线性贡献；攻击角不写作稳定关键因素。

## Q2 复现与验证

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
python questions/q2/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_task3_recalibration.py -q
```

Q2 当前主结果：

- 固定划分：train=514，test=221。
- carry 最优监督模型：`launch_state_model / hist_gradient_boosting`，测试 RMSE=8.337 yd，MAPE=4.986%。
- apex 最优监督模型：`launch_state_model / hist_gradient_boosting`，测试 RMSE=1.739 yd，MAPE=14.335%。
- ODE 重标定：drag 使用 36 条代表样本和 10 点粗网格；lift 使用 24 条代表样本和 6x6 粗网格；三类可标定模型均执行粗网格 + 有界局部优化。
- ODE 参数：drag `C_D=0.05` 为边界解；constant_lift `C_D=0.27,C_L=0.18`；spin_factor_lift `C_D=0.49,k_L=1.6`。
- 第二问主轨迹采用 `constant_lift`，第三问兼容轨迹单独输出 `spin_factor_lift`。
- 最终采用前向距离 `D_x=x_land` 作为主 carry 定义；顺风/逆风方向已校正并通过平均 carry 顺序验证。

原始题面与附件哈希清单见 `data/raw_manifest.csv`；提交前运行 `python scripts/snapshot_raw.py --verify`。
