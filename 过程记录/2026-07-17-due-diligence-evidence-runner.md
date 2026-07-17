# Due diligence evidence runner

## 用户请求

在 Open Deep Research Fork 中实现用于公开信息尽调的最小证据采集闭环。

## 范围与假设

- 公共接口接收尽调请求 JSON 和候选证据 JSON，返回结构化证据包。
- 本切片不调用模型、搜索 API 或 MCP，也不输出合作、投资、招聘或参与建议。
- 高优先级主张只有具备独立 A/B 级候选证据时才标记为已覆盖。
- 候选证据的必填字段缺失、为空或仅为空白字符时一律拒绝；来源必须是 HTTP(S) URL，发布日期和访问日期必须为 ISO 日期，不能覆盖任何主张。

## 变更

- 新增 `src/open_deep_research/diligence_evidence.py`。
- 新增聚焦行为测试和合成输入示例。
- 在 README 中声明 Fork 的边界与运行方式。
- 将依赖远程模型、搜索和 LangSmith 的 legacy 集成测试改为 `--run-langsmith` 显式启用；默认全量测试只执行本地可复现检查。
- 将测试配置抽为共享 pytest 插件，确保从仓库根目录或 `src/legacy/tests` 目录运行时均保留相同的选项与 opt-in 行为。
- 新增研究输出适配器与 CLI：仅允许将原研究输出中原样出现的 URL、且关键摘录实际出现于同一来源观察中的内容映射为候选证据，并保留来源观察与访问日期。

## 验证

- 先运行测试，确认模块缺失而失败。
- 增加空值、仅含空白字符及无效 URL/日期的回归测试；空值路径和无效 URL/日期路径在修复前失败，修复后通过。
- 实现后运行 `uv run pytest tests/test_diligence_evidence.py -q`。
- 运行 `uv run ruff check src/open_deep_research/diligence_evidence.py tests/test_diligence_evidence.py`。
- 运行 `uv run pytest -q`，确认本地测试通过、外部集成测试明确跳过。
- 分别从仓库根目录和 `src/legacy/tests` 运行 pytest，确认共享插件均被加载。
- 使用合成请求、研究输出和映射清单端到端运行 CLI，检查生成的证据包与覆盖状态。

## 后续

- 后续再将研究图输出映射为候选证据；映射前不得把摘要当成事实或决策依据。
