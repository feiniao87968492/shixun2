# Findings & Decisions

## Requirements
- 使用 `math-modeling-repo-init` 初始化当前数学建模项目仓库。
- 建立 Git、标准目录、问题文档、分问题脚本骨架和证据链文件。
- 完成前期题目拆解：题意重述、符号单位、假设、数据字典、项目计划、各小问方案。
- 保留和归档已有题面与附件，不覆盖已有文件。

## Research Findings
- 当前目录：`D:\Users\zty\数学建模\赛题集\实训2`。
- 当前目录原本未初始化 Git。
- 已有资料位于 `2026年实训题2/`，包含 PDF、OCR Markdown 和 Excel 附件。
- 题目标题：`2026年实训题2 高尔夫球飞行轨迹预测与最优击球策略建模`。
- 题目共有 3 个主问题：
  - q1：输入参数与输出结果相关性、飞行距离影响因素排序。
  - q2：预测模型建立与验证、三维 ODE 轨迹绘制、典型记录误差分析。
  - q3：200 yd 目标下的最优击球参数优化与轨迹绘制。
- OCR/题面附件说明提到约 30 条有效记录，但实际 Excel 读取结果为 735 条；后续以 Excel 实际记录为准，并在论文中避免照搬 OCR 的数据规模描述。
- Excel `高尔夫球实测数据` 工作表第 3 行为表头，字段包括序号、球速、发射角、发射方向、自旋速率、自旋轴偏角、后旋、侧旋、杆头速度、攻击角、飞行距离、最高点高度、总距离、横向偏移。
- 缺失情况：`杆头速度(mph)` 缺失 63 条，`攻击角(度)` 缺失 65 条，其余核心字段未发现缺失。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 skill 自带 `init_modeling_repo.py --force --no-git` | 目标目录非空，先补齐结构，再手动整理 raw data 与提交范围 |
| 问题数设为 3 | 题面按“问题一/二/三”组织，子任务归入对应 qN |
| 原始资料复制到 `data/raw/problem/` | 满足原始数据只读与快照要求，同时避免移动用户原始资料目录 |
| 原始资料目录加入 `.gitignore` | 已复制到 raw 目录，避免重复资料进入 Git |
| q3 主目标使用首次落点飞行距离与横向偏移 | 题面要求落点接近洞口，总距离只作为辅助诊断 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| PowerShell `python -c` 嵌入换行触发 SyntaxError | 改为单行 Python 表达式并成功读取 Excel 字段 |

## Resources
- Skill: `C:\Users\zty\.codex\skills\math-modeling-repo-init\SKILL.md`
- Init script: `C:\Users\zty\.codex\skills\math-modeling-repo-init\scripts\init_modeling_repo.py`
- Problem OCR: `2026年实训题2/2026年实训题2  高尔夫球飞行轨迹预测与最优击球策略建模.pdf_by_PaddleOCR-VL-1.6.md`
- Data attachment: `2026年实训题2/附件（实训题2）.xlsx`
- Raw manifest: `data/raw_manifest.csv`

## Visual/Browser Findings
- No browser or image findings.
