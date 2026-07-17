# Codex / 外部 Agent 研究记录提示词

请只研究公开可访问的信息，并将每个已打开来源的可核验观察整理为以下 JSON。不要给出合作、投资、招聘或参与建议；不要把摘要或推断写成已核验事实；不要包含 API key、登录信息、个人敏感信息或付费墙内容。

```json
{
  "agent": {"name": "Codex", "mode": "interactive"},
  "sources": [
    {
      "title": "来源页面标题",
      "source_url": "https://exact-source-url.example/path",
      "research_excerpt": "从该页面实际观察到的、可与原页面核对的简短摘录或事实描述。"
    }
  ]
}
```

要求：

- `source_url` 必须是无凭据的完整 HTTP(S) URL，保持原样，不补尾部 `/`、不改写参数。
- `research_excerpt` 必须来自同一 URL 的实际页面内容；未知或无法访问时不要编造。
- 每一条观察只描述来源说了什么，不补充证据等级、结论或建议。
- 若没有可靠来源，返回空数组：`{"agent": {"name": "Codex"}, "sources": []}`。
