# Task Plan: q1 第一问计划完成

## Goal
完成 `docs/plans/task1.md` 中第一问计划：数据审计、相关性、重要性排序、稳定性分析、图表产物、证据链和文档闭环。

## Current Phase
Phase 10

## Phases

### Phase 1: 仓库初始化和前期拆分
- [x] 建立标准仓库结构
- [x] 完成题面拆解和 q1-q3 方案骨架
- [x] 提交并推送初始化仓库
- **Status:** complete

### Phase 6: task1 要求识别
- [x] 读取 `docs/plans/task1.md`
- [x] 识别表格、图片、验证、文档与完成标准
- **Status:** complete

### Phase 7: q1 测试先行
- [x] 为数据加载、样本口径、相关性、聚合排序写失败测试
- [x] 看到测试因缺少 `analysis.py` 失败
- [x] 修复后测试通过
- **Status:** complete

### Phase 8: q1 流水线实现
- [x] 实现 `questions/q1/scripts/analysis.py`
- [x] 接通 `pipeline.py`、`validate.py`、`visualize.py`
- [x] 增加 `scikit-learn` 依赖
- **Status:** complete

### Phase 9: q1 产物生成与文档闭环
- [x] 运行 q1 pipeline 生成表格、图、图数据和 meta
- [x] 运行 q1 validate 检查 26 个产物
- [x] 更新 q1 results/experiments/evidence/manifest
- [x] 更新全局 evidence_chain 和 figure_table_registry
- **Status:** complete

### Phase 10: 最终验证与提交
- [x] 运行单元测试
- [x] 运行 q1 pipeline/validate
- [x] 运行仓库自检和 raw snapshot verify
- [x] 提交本地 task1 结果
- [x] 提交 artifact 序列化稳定性修复
- [ ] 推送到远端 `origin/main`（当前环境无法连接 `github.com:443`）
- **Status:** complete for task1 modeling deliverables; remote sync pending on network recovery

## Key Questions
1. task1 是否要求完整实现而非文档计划？答案：是，要求生成 q1 表格、图片、稳定性分析、证据链和结果文档。
2. 自旋变量如何避免重复表达？答案：主模型分别使用“自旋速率+自旋轴偏角”和“后旋+侧旋”两套表示，聚合条件贡献，不在单个模型中同时使用四个自旋变量。
3. 缺失值如何处理？答案：S1 不用杆头速度/攻击角，S2 完整样本，S3 中位数插补加缺失指示变量。

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| q1 分析核心放在 `questions/q1/scripts/analysis.py` | 第一问逻辑较专用，先避免过早抽象到全局模块；q2/q3 可复用 processed 数据 |
| q1 非线性重要性使用 ExtraTrees + 验证集置换重要性 | 满足 task1 对非线性预测贡献和非纯度重要性的要求 |
| Bootstrap 设置为 500 次 | 满足 task1 对相关系数不确定性和排名区间的要求 |
| 交叉验证设置为 5 折 x 5 次 | 满足 task1 对重复交叉验证的要求 |
| 主结论只写统计关联和预测信息 | 避免把观测数据相关性写成因果 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| q1 pipeline 首次运行图表阶段 KeyError: score columns missing | 1 | 增加回归测试，保留 aggregate ranking 的四个 score 列 |
| PowerShell 中 `python -c` 嵌入 `\n` 导致 SyntaxError | 1-2 | 改为不含换行的单行列表表达式 |
| q1 pipeline 在 180 秒工具窗口内超时 | 1 | 确认为耗时窗口不足，使用 900 秒窗口复跑通过，实际约 192-203 秒 |
| q1 artifact 重跑后出现 1e-15 量级浮点 CSV diff | 1 | 增加 artifact 浮点格式测试，公共 CSV 写出固定为 12 位有效数字 |
| q1 artifact 在 Windows 下重写为 CRLF 导致 `git diff --check` trailing whitespace | 1 | 扩展 artifact 测试为字节级 LF 断言，公共 CSV 和 meta JSON 写出统一 LF |
| `git push origin main` 无法连接 GitHub | 4 | 普通 push、授权 push、`curl -I https://github.com`、HTTP/1.1 回退均失败；本地提交保留，待网络恢复后执行 `git push origin main` |
