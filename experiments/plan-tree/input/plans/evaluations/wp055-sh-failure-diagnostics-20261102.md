# WP-055 — SH 失败诊断与中心范围校验（2026-11-02）

## 背景

2026-10-30 的 249 条 BGS 批量运行中，10 条样本因 6 个 SH 假设之一失败而整条中止：

- 7 条 `BadRequestError`：工具以 `invalid_id_judgments` 拒绝线表，模型仅回复“将修复”而未再次调用工具，runner 注入 continuation 后下一次模型调用返回 HTTP 400。归档只保存异常类名，无法确认 400 正文。
- 3 条 `ValueError`：CSV 已写出，但某个 MARGINAL 行的 `fitted_center` 略超光谱红端（9824.288 / 9824.143 / 9843.2 Å，上限 9824.0），`plot_sh_adopted_lines` 抛出范围错误。

## 修复

1. **失败详情落盘**
   - `MarkdownSessionRecorder.finish` 新增可选 `error_message` 与 `traceback_text`，在 `## Session outcome` 中渲染单行错误消息与代码围栏 traceback；`sh_line_review` 在异常分支传入 `str(exc)` 与 `traceback.format_exc()`。
   - `GraphWorkflow` 的 SH 批量汇总保留原有 `failed`（ref → 异常类名），新增 `failure_details`（ref → `{type, message, traceback}`），schema 升为 `forma-sh-batch-summary-v2`；`SHBatchIncompleteError` 文本改为带每个失败假设的 `类型: 消息` 摘要，因此 `run_batch.py` 的 CSV `error` 列不再只有假设名。
2. **中心范围校验前移**
   - `validate_sh_catalog` 对 kept 行新增 `wavelength_min <= fitted_center <= wavelength_max` 检查，越界在 `write_lines_csv` 阶段以 `kept line centre is outside the observed spectrum` 返回，进入 `rows_to_repair`，不再写出 CSV。
   - `plot_sh_adopted_lines` 保留范围守卫作为防御性断言，错误消息增加行名、中心、振幅与光谱范围，便于旧档案排障。

## 执行结果

- 新增/更新测试：
  - `test_sh_catalog_validation.test_kept_centre_outside_spectrum_is_rejected_at_the_write_boundary`
  - `test_session_markdown.test_failed_outcome_records_message_and_traceback`
  - `test_graph_workflow.test_one_sh_failure_does_not_cancel_successful_sibling` 扩展为断言 `failure_details` 与异常文本
- `PYTHONPATH=src:tests/agentic_graph python -B -m unittest discover -s tests/agentic_graph -p 'test_*.py'`：**196 条通过**（原 194 + 新增 2）。
- 定向运行 `test_sh_catalog_validation test_session_markdown test_graph_workflow`：18 条通过。
- 未重跑 249 条真实批量（成本约 18 小时）；本次以离线测试验证行为变化。旧归档中 3 条越界 CSV 仍会在绘图守卫处报错，但错误消息已带出行名与范围。

## 限制

- 7 条 `BadRequestError` 的直接触发流程不在本节点范围；400 正文已在 WP-056 的对照回放中确认（`insufficient tool messages following tool_calls message`）。
- 决策人已裁定**不做“单假设失败降级为部分完成”**：证据不完整时停止该样本，避免以不完整证据给出错误类型/红移。
- 仅 SH 会话路径传入错误消息/traceback；QSO/ELG/HS 的会话记录仍只存异常类名，可后续统一。
