# Due diligence evidence runner

## 用户请求

在 Open Deep Research Fork 中实现用于公开信息尽调的最小证据采集闭环。

## 范围与假设

- 公共接口接收尽调请求 JSON 和候选证据 JSON，返回结构化证据包。
- 本切片不调用模型、搜索 API 或 MCP，也不输出合作、投资、招聘或参与建议。
- 高优先级主张只有具备独立 A/B 级候选证据、且 runner 直接抓取来源并验证直接引文后才标记为已覆盖。
- 候选证据的必填字段缺失、为空或仅为空白字符时一律拒绝；来源必须是 HTTP(S) URL，发布日期和访问日期必须为 ISO 日期，不能覆盖任何主张。

## 变更

- 新增 `src/open_deep_research/diligence_evidence.py`。
- 新增聚焦行为测试和合成输入示例。
- 在 README 中声明 Fork 的边界与运行方式。
- 恢复上游 LangSmith 集成测试的默认语义；本 fork 仅在 README 中单独列出不依赖远程凭据的本地证据测试。
- 新增研究输出适配器与 CLI：仅允许将原研究输出中原样出现的凭据安全 HTTP(S) URL、且关键摘录实际出现于该 URL 任一来源观察中的内容映射为候选证据；URL 校验不改写原始字符串，并拒绝无主机、带凭据或非法端口的 URL。
- 新增平台无关的外部 Agent 研究记录接口：Codex、本地 Agent 或其他研究系统可提交只含 `title`、精确 `source_url` 和页面观察摘录的 JSON；CLI 通过 `--research-record` 接收它，并与内置研究输出走同一 URL/摘录/证据门禁。不会嵌入 Codex 会话权限或要求其作为运行时依赖。
- 新增可复制的 Codex 研究提示词与合成 JSON 示例，明确 Agent 只交付来源观察，不能自证证据等级、结论或建议。
- 对每个映射主张，runner 直接抓取公开 URL、检查直接引文、输出实际抓取时间和内容 SHA-256；抓取失败或引文缺失时不产生可用证据。高优先级事实还必须是直接引文；外部 Agent 自报内容只能作为来源线索。
- 公开来源试跑：2026-07-20 以 Codex 观察的 `https://raw.githubusercontent.com/langchain-ai/open_deep_research/main/README.md` 运行 `diligence_runner`。可复跑输入如下（未保存页面全文）：

  ```json
  {"subject":"langchain-ai/open_deep_research","purpose":"验证 Codex 公开来源的直接引文与网页哈希门禁","claims":[{"id":"course-update","statement":"该仓库 README 在 2025-08-14 提到其免费课程。","priority":"normal"}]}
  ```

  ```json
  {"agent":{"name":"Codex","mode":"interactive"},"sources":[{"title":"GitHub - langchain-ai/open_deep_research","source_url":"https://raw.githubusercontent.com/langchain-ai/open_deep_research/main/README.md","research_excerpt":"August 14, 2025**: See our free course"}]}
  ```

  ```json
  [{"claim_id":"course-update","fact":"August 14, 2025**: See our free course","key_excerpt":"August 14, 2025**: See our free course","source_url":"https://raw.githubusercontent.com/langchain-ai/open_deep_research/main/README.md","published_at":"2025-08-14","source_type":"official_project_repository","evidence_level":"C","is_independent":false,"limitations":"项目维护方自身 README；只核验该页面显示的更新条目。"}]
  ```

  执行命令：`uv run python -m open_deep_research.diligence_runner --request /private/tmp/open-deep-research-live-request.json --research-record /private/tmp/open-deep-research-live-record.json --mappings /private/tmp/open-deep-research-live-mappings.json --accessed-at 2026-07-20 --output /private/tmp/open-deep-research-live-package.json`。输出：`status=verified`、`coverage=covered`、`fetched_at=2026-07-20T08:29:39.073856+00:00`、SHA-256 为 `0fc75629079c025b0200e6032a038edf9c91c332d4ce925cbc6165910008267f`；未保存页面全文。

## 验证

- 先运行测试，确认模块缺失而失败。
- 增加空值、仅含空白字符及无效 URL/日期的回归测试；空值路径和无效 URL/日期路径在修复前失败，修复后通过。
- 实现后运行 `uv run pytest tests/test_diligence_evidence.py -q`。
- 运行 `uv run ruff check src/open_deep_research/diligence_evidence.py tests/test_diligence_evidence.py`。
- 运行本地 evidence 测试和静态检查；上游全量测试仍保留其远程 LangSmith 依赖。
- 使用合成请求、研究输出和映射清单端到端运行 CLI，检查生成的证据包与覆盖状态。
- 对外部 Agent JSON 记录先增加失败测试，再实现适配器和 CLI；适配器与 CLI 聚焦测试通过。
- 以本地 HTTP 服务器覆盖 CLI 对私网来源的拒绝；固定-IP 抓取器的成功路径、摘录匹配、抓取时间和 SHA-256 由不依赖公网的单测覆盖；再用公开官方页面做一次可复跑 CLI 试跑。
- 本地 evidence 套件：20 项通过。
- 上游全量 pytest 已恢复执行 LangSmith 集成测试；当前环境的 LangSmith token 返回 401，因此该远程测试失败而非被跳过。此状态需要有效的 LangSmith 凭据才能完成。

## 后续

- 后续如需完全无人值守的研究，可在同一 JSON 记录协议上接 API、本地或 MCP Agent；映射前不得把摘要当成事实或决策依据。
