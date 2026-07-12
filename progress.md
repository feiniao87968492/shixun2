# Progress Log

## Session: 2026-07-12

### Phase 1: 安全检查与题面识别
- **Status:** complete
- Actions taken:
  - 检查当前目录内容：仅有 `2026年实训题2/` 资料目录。
  - 确认当前目录尚无 `.git/`。
  - 读取题面 OCR 文本，识别项目标题、3 个主问题和 Excel 附件说明。
  - 读取初始化脚本，确认非空目录需使用 `--force`，已有文件不会被覆盖。
- Files created/modified:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### Phase 2: 仓库结构初始化
- **Status:** complete
- Actions taken:
  - 运行 `init_modeling_repo.py . --questions 3 --force --no-git`。
  - 生成标准目录、项目级文档、q1-q3 文档与脚本骨架。
- Files created/modified:
  - `README.md`
  - `AGENTS.md`
  - `docs/`
  - `questions/q1/`
  - `questions/q2/`
  - `questions/q3/`
  - `scripts/`
  - `src/modeling_common/`

### Phase 3: 原始数据归档与快照
- **Status:** complete
- Actions taken:
  - 将 PDF、OCR Markdown 和 Excel 附件复制到 `data/raw/problem/`。
  - 运行 `python scripts/snapshot_raw.py` 生成哈希清单。
  - 读取 Excel 工作表，确认表头在第 3 行，数据记录 735 条。
  - 发现 `杆头速度(mph)` 缺失 63 条，`攻击角(度)` 缺失 65 条。
- Files created/modified:
  - `data/raw/problem/`
  - `data/raw_manifest.csv`
  - `docs/data_dictionary.md`

### Phase 4: 前期问题拆分
- **Status:** complete
- Actions taken:
  - 更新题目重述、符号单位、假设、数据字典、项目计划、模型选择、验证计划。
  - 更新 q1-q3 `approach.md`、`results.md` 和 `manifest.yaml`。
  - 更新证据链计划记录与图表登记表。
  - 更新风险登记和决策日志。
- Files created/modified:
  - `docs/problem_statement.md`
  - `docs/symbols.md`
  - `docs/assumptions.md`
  - `docs/project_plan.md`
  - `docs/model_selection.md`
  - `docs/validation_plan.md`
  - `docs/evidence_chain.csv`
  - `docs/figure_table_registry.csv`
  - `questions/q1/approach.md`
  - `questions/q2/approach.md`
  - `questions/q3/approach.md`

### Phase 5: 验证与提交
- **Status:** complete
- Actions taken:
  - 运行 `python scripts/check_repo.py`，仓库检查通过，保留 3 个预期 warning：q1-q3 pipeline 尚未实现。
  - 运行 `python scripts/snapshot_raw.py --verify`，3 个 raw 文件哈希验证通过。
  - 运行 `git init -b main` 初始化 Git 仓库。
  - 使用 `git check-ignore` 确认原始资料目录和 `data/raw/problem/` 被忽略，不会误提交 raw 附件。
  - 创建初始化提交 `chore: initialize modeling repository`。
- Files created/modified:
  - `.git/`
  - `task_plan.md`
  - `progress.md`

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Raw snapshot | `python scripts/snapshot_raw.py` | Write manifest for raw files | Wrote `data/raw_manifest.csv` for 3 files | pass |
| Repository check | `python scripts/check_repo.py` | No errors | Passed with 3 expected pipeline warnings | pass |
| Raw snapshot verify | `python scripts/snapshot_raw.py --verify` | Raw files match manifest | Verified 3 raw files | pass |
| Git ignore check | `git check-ignore -v ...` | Raw package ignored | Original package and `data/raw/problem/` ignored | pass |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-07-12 | `python -c` command with embedded `\n` failed under PowerShell | 1-2 | Rewrote as single-line Python expression |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 5: 验证与提交 |
| Where am I going? | 下一阶段可开始 q1 数据清洗与相关性基线 |
| What's the goal? | 完成实训题2可复现建模仓库初始化与前期问题拆分 |
| What have I learned? | See findings.md |
| What have I done? | 完成仓库结构、raw 归档、题面拆解和 q1-q3 方案文档 |

## Session: 2026-07-12 — task1 q1 实施

### Phase 6: task1 要求识别
- **Status:** complete
- Actions taken:
  - 读取 `docs/plans/task1.md`。
  - 提取第一问要求：数据审计、S1/S2/S3 样本口径、两套自旋表示、Pearson/Spearman/Kendall、Bootstrap 500、岭回归、非线性置换重要性、5x5 重复交叉验证、综合排序、敏感性、分组重要性、5 张图和完整文档闭环。
- Files created/modified:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### Phase 7: q1 测试先行
- **Status:** complete
- Actions taken:
  - 新增 `tests/test_q1_analysis.py`。
  - 首次运行测试，确认 4 个测试因缺少 `questions/q1/scripts/analysis.py` 失败。
  - 实现后测试通过。
  - 首次完整 pipeline 暴露图表阶段缺少 score 列，补回归测试后修复。
- Files created/modified:
  - `tests/test_q1_analysis.py`

### Phase 8: q1 流水线实现
- **Status:** complete
- Actions taken:
  - 新增 `questions/q1/scripts/analysis.py`。
  - 接通 `questions/q1/scripts/pipeline.py`、`validate.py`、`visualize.py`。
  - 增加 `scikit-learn` 依赖。
- Files created/modified:
  - `questions/q1/scripts/analysis.py`
  - `questions/q1/scripts/pipeline.py`
  - `questions/q1/scripts/validate.py`
  - `questions/q1/scripts/visualize.py`
  - `requirements.txt`

### Phase 9: q1 产物生成与文档闭环
- **Status:** complete
- Actions taken:
  - 运行 `python questions/q1/scripts/pipeline.py --config configs/default.yaml`。
  - 生成 `data/processed/golf_shots_clean.csv`。
  - 生成 q1 全部表格和 5 张图片，每张图片均有同名 CSV 与 meta.json。
  - 运行 `python questions/q1/scripts/validate.py`，26 个 artifact checks 全部通过。
  - 更新 q1 文档、全局证据链、图表登记表、论文草稿和开发日志。
- Files created/modified:
  - `data/processed/golf_shots_clean.csv`
  - `questions/q1/artifacts/`
  - `questions/q1/results.md`
  - `questions/q1/experiments.md`
  - `questions/q1/evidence.md`
  - `docs/evidence_chain.csv`
  - `docs/figure_table_registry.csv`
  - `report/paper.md`

### Phase 10: 最终验证与提交
- **Status:** in_progress
- Actions taken:
  - 复跑 `python questions/q1/scripts/pipeline.py --config configs/default.yaml`，q1 产物可复现。
  - 运行 `python questions/q1/scripts/validate.py`，26 个 artifact checks 通过。
  - 运行 `python -m pytest -q`，5 个测试通过。
  - 运行 `python scripts/check_repo.py`，通过；仅 q2/q3 pipeline 未实现 warning。
  - 运行 `python scripts/snapshot_raw.py --verify`，3 个 raw 文件验证通过。
  - 发现复跑后 artifact CSV 存在 1e-15 量级浮点文本抖动。
  - 新增 `tests/test_artifacts.py`，先观察失败，再将公共 CSV 写出固定为 12 位有效数字。
  - 继续扩展 artifact 测试为字节级 LF 换行断言，修复 Windows 下 CSV/meta JSON 重写为 CRLF 导致的 `git diff --check` trailing whitespace。
  - 复跑 q1 pipeline、q1 validate、全量 pytest、仓库自检和 raw verify 均通过。
  - 创建本地提交 `2d48c97 feat(q1): complete factor analysis workflow`。
  - 创建本地提交 `4e4e967 test: stabilize modeling artifact serialization`。
  - 多次尝试 `git push origin main`，均因当前环境无法连接 `github.com:443` 失败；本地分支保留 ahead 状态，待网络恢复后推送。
- Files created/modified:
  - `task_plan.md`
  - `progress.md`
  - `src/modeling_common/artifacts.py`
  - `tests/test_artifacts.py`

## Task1 Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| q1 tests red | `python -m pytest tests\test_q1_analysis.py -q` | Fail because implementation missing | 4 failures: `analysis.py` missing | pass |
| q1 tests green | `python -m pytest tests\test_q1_analysis.py -q` | Pass | 4 passed | pass |
| q1 pipeline | `python questions\q1\scripts\pipeline.py --config configs/default.yaml` | Generate q1 artifacts | Completed; top features ball_speed, club_speed, attack_angle, launch_angle, spin_axis | pass |
| q1 artifact validation | `python questions\q1\scripts\validate.py` | All q1 artifacts exist with data/meta | 26 checks passed | pass |
| full pytest | `python -m pytest -q` | All tests pass | 5 passed | pass |
| artifact format regression | `python -m pytest tests\test_artifacts.py -q` | Stable CSV float precision and LF newlines | 1 passed after RED failures | pass |
| full pytest after artifact fix | `python -m pytest -q` | All tests pass | 6 passed | pass |
| diff whitespace check | `git diff --check` | No whitespace errors | No output | pass |
| repo check | `python scripts\check_repo.py` | No errors | Passed with q2/q3 scaffold warnings | pass |
| raw verify | `python scripts\snapshot_raw.py --verify` | Raw files match manifest | Verified 3 files | pass |
| remote push | `git push origin main` | Push local commits to GitHub | Failed: connection reset / cannot connect to github.com:443 | blocked |

## Task1 Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-07-12 | q1 pipeline failed at visualization due missing `pearson_score`/`ridge_score` columns | 1 | Added regression test and kept score columns in `aggregate_rankings` |
| 2026-07-12 | q1 pipeline exceeded 180-second tool timeout | 1 | Reran with 900-second timeout; script completed successfully |
| 2026-07-12 | q1 generated CSV artifacts changed only in last-bit float text formatting after rerun | 1 | Added failing artifact precision test, fixed `save_table` and `save_figure_bundle` with stable float format |
| 2026-07-12 | Generated CSV/meta artifacts used CRLF on Windows, causing `git diff --check` trailing whitespace reports | 1 | Added byte-level LF assertions and fixed artifact writers to use LF |
| 2026-07-12 | GitHub push failed because current environment cannot connect to `github.com:443` | 4 | Verified no proxy config; `curl.exe -I https://github.com` and HTTP/1.1 git push also failed. Keep local commits and retry after network recovery |

## Task1 Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 10: final verification and commit |
| Where am I going? | Run full verification, commit, push |
| What's the goal? | Complete `docs/plans/task1.md` |
| What have I learned? | See findings.md |
| What have I done? | q1 workflow implemented, artifacts generated, docs updated |

## Session: 2026-07-12 — q1 review1 completion audit

### Phase 11: review1 整改补齐
- **Status:** complete
- Actions taken:
  - 确认远端已成功推送到 `origin/main`，当前远端提交为 `756a0aa fix(q1): complete review1 reproducibility audit`。
  - 读取 `questions/q1/review1.md`、`task_plan.md`、`progress.md` 和 `findings.md`，从当前工作树重新审计完成标准。
  - 用 `rg` 搜索旧口径数字和结论，定位 `docs/data_dictionary.md`、`docs/assumptions.md`、`docs/symbols.md`、`devlog.md` 和计划文件中仍需同步的 review1 口径。
  - 更新数据字典、假设表和符号表：原始缺失 63/65，异常 0 值 3/3，修正后缺失 66/68，杆头速度修正后非缺失范围 50.3534-106.59 mph。
  - 追加 `devlog.md` 的 q1 review1 整改记录，保留旧 task1 历史记录。
  - 修正 `questions/q1/scripts/visualize.py` standalone 入口，使其加载 `q1_feature_summary`、`q1_group_importance` 和 `q1_sensitivity_comparison` 等 review1 图表依赖。
  - 新增测试断言 standalone 绘图入口注册 review1 所需表。
  - 运行 standalone 绘图入口，确认 q1 图表可由 `visualize.py` 独立再生成。
  - 按 review1 验收顺序运行 pipeline、validate、pipeline，并比较关键 CSV hash；`q1_feature_summary.csv`、`q1_correlation_confidence_intervals.csv`、`q1_permutation_importance.csv`、`q1_model_performance.csv` hash 前后完全一致。
  - 运行全量 pytest、仓库检查、raw snapshot verify 和 whitespace check。
  - 提交 `36fbd51 chore(q1): close review1 audit gaps` 并推送到 `origin/main`。
  - 补记 Phase 11 状态为 complete。
- Files modified:
  - `questions/q1/scripts/visualize.py`
  - `tests/test_q1_review1.py`
  - `docs/data_dictionary.md`
  - `docs/assumptions.md`
  - `docs/symbols.md`
  - `devlog.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## Review1 Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| standalone q1 visualize | `python questions\q1\scripts\visualize.py` | Regenerate q1 figures from registered tables | `[ok] q1 figures regenerated` | pass |
| q1 pipeline first run | `python questions\q1\scripts\pipeline.py --config configs/default.yaml` | Regenerate all q1 artifacts | Completed | pass |
| q1 validation | `python questions\q1\scripts\validate.py --config configs/default.yaml` | Real artifact/schema/numeric/repro checks pass | 62 checks passed | pass |
| q1 pipeline second run | `python questions\q1\scripts\pipeline.py --config configs/default.yaml` | Same-seed rerun succeeds | Completed | pass |
| key CSV reproducibility | SHA256 of four key q1 CSVs before/after second pipeline | Hashes unchanged | All four hashes identical | pass |
| q1 targeted tests | `python -m pytest tests\test_q1_review1.py tests\test_q1_analysis.py -q` | Review1 and q1 analysis tests pass | 8 passed | pass |
| full pytest | `python -m pytest -q` | All tests pass | 10 passed | pass |
| whitespace check | `git diff --check` | No whitespace errors | No output | pass |
| repo check | `python scripts\check_repo.py` | No errors | Passed with q2/q3 scaffold warnings | pass |
| raw verify | `python scripts\snapshot_raw.py --verify` | Raw files match manifest | Verified 3 raw files | pass |

### Completion
- Phase 11 review1 completion-audit patch has been committed and pushed.

## Session: 2026-07-12 — q1 review2 method audit

### Phase 12: review2 RED tests and implementation
- **Status:** in_progress
- Actions taken:
  - 读取 `questions/q1/review2.md`，确认状态为 `q1_status: conditionally_passed`，需修复 4 项必须整改和若干次要问题。
  - 新增 `tests/test_q1_review2.py`，覆盖 S3 敏感性样本量、速度重叠同样本配对 CV、分组重要性重复 CV/block permutation、边际稳定性字段命名、Ridge 重复估计、旧等权排名弃用、联合截断删除原因和 validate 方法不变量。
  - 运行 `python -m pytest tests\test_q1_review2.py -q`，8 项按预期失败，证明测试覆盖旧问题。
  - 修改 `questions/q1/scripts/analysis.py`：Ridge 改为训练折重复估计；S3 敏感性新增描述性插补口径；速度重叠输出同样本 summary + fold scores；分组重要性改为重复 CV + block permutation；rank stability 改为 `marginal_*` 字段；旧 feature ranking 标记为 deprecated；outlier audit 拆分删除原因；validate 增加 review2 方法检查。
  - 运行 `python -m py_compile ...` 通过。
  - 运行 `python -m pytest tests\test_q1_analysis.py tests\test_q1_review1.py -q`，8 passed。
- Files modified:
  - `questions/q1/scripts/analysis.py`
  - `tests/test_q1_review2.py`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## Review2 Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| review2 RED | `python -m pytest tests\test_q1_review2.py -q` | Fail on old artifacts/method contracts | 8 failed for expected missing columns/tables/checks | pass |
| syntax | `python -m py_compile questions\q1\scripts\analysis.py ...` | No syntax errors | No output | pass |
| existing q1 tests | `python -m pytest tests\test_q1_analysis.py tests\test_q1_review1.py -q` | Existing behavior remains green | 8 passed | pass |

### Pending
- None for review2.

### Phase 12: review2 documentation sync
- **Status:** complete
- Actions taken:
  - 修正 `pipeline.py` 输出，不再打印容易误导为最终结论的 `top_features`，改为 `summary_order_features` 和 `stable_key_features`。
  - 新增 review2 测试断言 `q1_run_summary.json` 只保留 `summary_order_features` / `stable_key_features`，且稳定关键因素仅为 `ball_speed_mph`。
  - 更新 `questions/q1/approach.md`、`results.md`、`experiments.md`、`evidence.md`、`questions/q1/README.md`、根 `README.md`、`report/paper.md`、`docs/evidence_chain.csv` 和 `docs/figure_table_registry.csv`。
  - 文档同步为 669 条共同样本配对 CV、5x5 CV block permutation、边际排名稳定性、旧等权排名弃用和 71 项验证检查。
  - 运行 `python questions\q1\scripts\pipeline.py --config configs/default.yaml`，重新生成 review2 artifacts，CLI 摘要为 `stable_key_features=ball_speed_mph`。
  - 运行 `python questions\q1\scripts\validate.py --config configs/default.yaml`，71 checks passed。
  - 运行 `python -m pytest -q`，19 passed。
  - 运行 `python scripts\check_repo.py`，通过，保留 q2/q3 pipeline scaffold warning。
  - 运行 `python scripts\snapshot_raw.py --verify`，verified 3 raw files。
  - 运行 `git diff --check`，无输出。

## Review2 Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| q1 pipeline | `python questions\q1\scripts\pipeline.py --config configs/default.yaml` | Regenerate all q1 artifacts | Completed; stable key only `ball_speed_mph` | pass |
| q1 validation | `python questions\q1\scripts\validate.py --config configs/default.yaml` | Review2 method invariants pass | 71 checks passed | pass |
| full pytest | `python -m pytest -q` | All tests pass | 19 passed | pass |
| repo check | `python scripts\check_repo.py` | No errors | Passed with q2/q3 scaffold warnings | pass |
| raw verify | `python scripts\snapshot_raw.py --verify` | Raw files match manifest | Verified 3 raw files | pass |
| whitespace check | `git diff --check` | No whitespace errors | No output | pass |

### Completion
- Phase 12 review2 method-audit patch is ready for commit and push to `origin/main`.
