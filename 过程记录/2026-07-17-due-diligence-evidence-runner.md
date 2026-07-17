# Due diligence evidence runner

## 用户请求

在 Open Deep Research Fork 中实现用于公开信息尽调的最小证据采集闭环。

## 范围与假设

- 公共接口接收尽调请求 JSON 和候选证据 JSON，返回结构化证据包。
- 本切片不调用模型、搜索 API 或 MCP，也不输出合作、投资、招聘或参与建议。
- 高优先级主张只有具备独立 A/B 级候选证据时才标记为已覆盖。
- 候选证据的必填字段缺失或为空时一律拒绝，不能覆盖任何主张。

## 变更

- 新增 `src/open_deep_research/diligence_evidence.py`。
- 新增聚焦行为测试和合成输入示例。
- 在 README 中声明 Fork 的边界与运行方式。

## 验证

- 先运行测试，确认模块缺失而失败。
- 增加空来源链接回归测试，确认修复前失败、修复后通过。
- 实现后运行 `uv run pytest tests/test_diligence_evidence.py -q`。
- 运行 `uv run ruff check src/open_deep_research/diligence_evidence.py tests/test_diligence_evidence.py`。

## 后续

- 后续再将研究图输出映射为候选证据；映射前不得把摘要当成事实或决策依据。
