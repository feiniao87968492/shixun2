# 复现说明

## 环境

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
python -m pip install -r requirements.txt
```

若存在 `requirements-lock.txt`，优先安装锁定版本。

## 数据

1. 本项目原始资料已复制到 `data/raw/problem/`。
2. 使用 `docs/data_dictionary.md` 确认字段和读取方式。
3. 运行 `python scripts/snapshot_raw.py --verify` 检查 raw data 哈希。
4. 若后续加入外部数据，必须在 `docs/references.md` 中记录来源、访问日期和许可。

## 运行

```bash
python scripts/check_repo.py
python scripts/run_all.py --dry-run
python scripts/run_all.py --execute
```

也可运行单个小问：

```bash
python questions/q1/scripts/pipeline.py --config configs/default.yaml
```

Q2/Q3 联合复现发布建议按以下顺序运行：

```bash
python questions/q2/scripts/pipeline.py --config configs/default.yaml
python questions/q2/scripts/validate.py --config configs/default.yaml
python questions/q3/scripts/pipeline.py --config configs/default.yaml
python questions/q3/scripts/validate.py --config configs/default.yaml
python -m pytest tests/test_q2_q3_integration.py -q
```

执行 q3 pipeline 后会生成 `docs/reproducibility/q2_q3_release_manifest.json`，其中记录当前 Git commit、配置、处理数据、Q2/Q3 run metadata 和所有 Q2/Q3 核心 CSV 的 SHA256。

## 预期产物

- 各小问 `artifacts/tables/` 中的结果表；
- `artifacts/figures/` 与 `artifacts/figure_data/` 中的成对图表；
- 更新后的证据链和图表登记表；
- 论文引用的最终结果。

## 干净环境复现记录

| 日期 | 环境 | 提交 | 执行人 | 结果 | 备注 |
|---|---|---|---|---|---|
| 2026-07-12 | 当前工作环境 | 初始化前 | Codex | 仓库结构自检通过；raw 快照验证通过 | q1-q3 正式流水线尚未实现 |
| 2026-07-14 | 当前工作环境 | 31c554b 基础上 task7 工作区 | Codex | q2 pipeline/validation、q3 pipeline/validation、Q2-Q3 integration 均通过 | release manifest 已生成，提交后需以最终 commit SHA 为准 |
