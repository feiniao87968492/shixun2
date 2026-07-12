# 2026年实训题2 高尔夫球飞行轨迹预测与最优击球策略建模

- 比赛 / 项目：课程实训
- 小问数量：3
- 初始化时间：2026-07-12T16:10:49+08:00
- 文档语言：zh-CN
- 当前状态：`initialized`

## 项目目标

围绕高尔夫球飞行轨迹数据，建立从相关性解释、监督预测、三维动力学仿真到最优击球参数搜索的完整建模流程。最终交付物包括：关键影响因素排序、飞行距离与最高点高度预测模型、典型击球轨迹图、ODE 模型误差分析、200 yd 目标下的最优击球参数及对应轨迹。

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
data/raw/                原始数据，只读
data/interim/            中间数据
data/processed/          可建模数据
data/external/           外部补充数据
docs/                    项目级建模文档
notebooks/               探索性分析，不作为最终运行入口
questions/qN/            每个小问的方案、代码和产物
report/                   论文与附录
scripts/                  仓库级运行和审计脚本
src/modeling_common/      跨小问共享代码
tests/                    基础测试
```

## 运行约定

- 所有命令从仓库根目录执行。
- 每个小问的正式入口是 `questions/qN/scripts/pipeline.py`。
- 图和生图数据必须同名保存。
- 最终结论必须登记到 `docs/evidence_chain.csv`。
- 原始数据首次放入后运行 `python scripts/snapshot_raw.py`。

## 当前小问

| 小问 | 状态 | 主要目标 | 入口 |
|---|---|---|---|
| q1 | planned | 相关性分析与飞行距离影响因素排序 | `python questions/q1/scripts/pipeline.py --dry-run` |
| q2 | planned | 监督预测、三维 ODE 轨迹建模与典型记录误差分析 | `python questions/q2/scripts/pipeline.py --dry-run` |
| q3 | planned | 以 200 yd 目标为约束的最优击球参数搜索与轨迹绘制 | `python questions/q3/scripts/pipeline.py --dry-run` |

原始题面与附件已归档到 `data/raw/problem/`，哈希清单见 `data/raw_manifest.csv`。
