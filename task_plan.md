# Task Plan: 实训题2数学建模仓库初始化

## Goal
把当前“2026年实训题2 高尔夫球飞行轨迹预测与最优击球策略建模”整理成可复现、可审计的数学建模仓库，并完成前期题目拆解与分问题方案骨架。

## Current Phase
Phase 5

## Phases

### Phase 1: 安全检查与题面识别
- [x] 检查目标目录、Git 状态和已有文件
- [x] 识别题面、附件和实际小问数量
- [x] 记录发现
- **Status:** complete

### Phase 2: 仓库结构初始化
- [x] 运行仓库初始化脚本
- [x] 保留已有题面资料，不覆盖原文件
- [x] 建立标准目录、问题文档和脚本骨架
- **Status:** complete

### Phase 3: 原始数据归档与快照
- [x] 将 PDF、OCR 文本和 Excel 附件纳入 data/raw
- [x] 生成 raw data 哈希清单
- [x] 初步审计 Excel 字段和样本规模
- **Status:** complete

### Phase 4: 前期问题拆分
- [x] 完成 docs/problem_statement.md
- [x] 完成 docs/symbols.md
- [x] 完成 docs/assumptions.md
- [x] 完成 docs/data_dictionary.md
- [x] 完成 docs/project_plan.md
- [x] 完成 q1-q3 approach.md
- **Status:** complete

### Phase 5: 验证与提交
- [x] 运行 scripts/check_repo.py
- [x] 运行 snapshot_raw verify
- [x] 初始化 Git 并审查 status
- [x] 创建初始化提交
- **Status:** complete

## Key Questions
1. 实际小问数量是多少？答案：3 个主问题，含 q1 的 2 个子任务、q2 的 3 个子任务、q3 的 2 个子任务。
2. 原始数据是否已经存在？答案：存在 PDF、OCR Markdown 和 Excel 附件，已复制归档到 data/raw/problem。
3. 项目主要计算环境是什么？答案：Python 为主，必要时可用 MATLAB 交叉验证；正式入口按 questions/qN/scripts/pipeline.py。

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 仓库根目录使用当前 `实训2` 目录 | 用户在该目录发起请求，当前目录尚无 Git，适合作为项目根 |
| 小问数量设置为 3 | 题面明确分为问题一、问题二、问题三 |
| 原始题面资料复制到 `data/raw/problem/` | 保留已有资料目录，同时满足原始数据只读归档约定 |
| 原始资料目录加入 `.gitignore` | 避免把重复 raw package 纳入 Git，仓库用 raw manifest 追踪本地文件一致性 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| PowerShell 中 `python -c` 嵌入 `\n` 导致 SyntaxError | 1-2 | 改为不含换行的单行列表表达式 |
