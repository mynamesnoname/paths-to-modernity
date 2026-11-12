# WP-056 — continuation 无效工具调用重放修复（2026-11-02）

## 背景

见 `wp055-sh-failure-diagnostics-20261102.md`：7 条 BadRequestError 会话的第 3 个事件有 2–3k 输出 tokens 但无可见 tool_calls，`invalid_tool_calls` 被 `_convert_message_to_dict` 序列化为 `tool_calls` 后重放，缺少对应 tool 消息。

## 修复

1. `node_runtime.complete_tool_call_sequences`：为 `invalid_tool_calls` 与未应答的 `tool_calls` 紧接原 AI 消息补一条合成 `ToolMessage`（沿用 call ID 与 name，内容声明调用格式损坏并请求重发）；已有的真实 tool 响应不会被重复。
2. `repair_incomplete_stage` 在重放前调用该修复，并把合成响应记为 `repair_synthetic_tool_messages` 事件。
3. `MarkdownSessionRecorder` 现在打印 `invalid_tool_calls`，此前该字段完全不可见。
4. `sh_line_review` 捕获 `BadRequestError`：调用一次 `restart_with_instruction`，只发送原始 user 提示 + 含 `rows_to_repair` 的修复反馈；若修复轮仍 400，再执行同一回退一次，之后仍失败则按严格策略失败。
5. `repair_instruction()` 把校验器的 `rows_to_repair` 一并带给模型，减少无效重试。

## 执行结果

- 离线测试：`PYTHONPATH=src:tests/agentic_graph python -B -m unittest discover -s tests/agentic_graph -p 'test_*.py'`：**202 条通过**（原 196 + 新增 6）。
- 新增 `tests/agentic_graph/test_node_runtime.py`：5 条，覆盖 invalid call 合成响应、已应答调用不重复、悬空合法调用补齐、修复轮重放序列无悬空 ID、全新会话只带原始提示与反馈。
- `test_session_markdown` 新增 invalid tool call 归档断言。
- 用 `_convert_message_to_dict` 验证：修复后的消息序列中每个 `tool_call_id` 都有紧随的 `tool` 消息；修复前 `invalid_tool_calls` 会被序列化为无应答的 `tool_calls`。
- 真实回放（见下节）：修复路径不再 400，模型在合成错误后重发并写出 23 行有效表。

## 真实回放（2026-11-02）

用归档的 120/H2 提示词与 `hypothesis_001_measurement_catalog.json` 重建同一 agent，并在消息中注入同一个损坏调用（`invalid_tool_calls`，`id=call_*_bad`）：

- **对照组（不补 tool 消息，直接重放）**：提供方返回
  `400 ... An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'. (insufficient tool messages following tool_calls message) ...`；
  CSV 未生成。
- **修复组（`repair_incomplete_stage` 补合成 `ToolMessage`）**：无 400；模型收到“调用格式损坏”的合成响应后重发，工具校验通过并写出 **23 行**有效表；会话归档含 `repair_synthetic_tool_messages` 事件。
- 本地归档：`.data/replay120/replay_session.md`、`control_session.md`、`replay_lines.csv`（工作目录，未入库）。
- 说明：回放是**注入式单次实验**，不是 249 条批量的完整重跑；它验证的是失败机制与修复，不替代真实批量的成功率测量。

## 限制

- 根因与 400 正文已由上述对照回放确认；但“模型自然产生损坏调用”的概率没有重新测量。
- 全新会话回退只在 `sh_line_review` 启用；其他使用 `repair_incomplete_stage` 的节点只获得序列修复，没有 400 回退。
- 回退为一次性；若全新会话仍失败，按“单假设失败即样本失败”的已裁定策略处理。
