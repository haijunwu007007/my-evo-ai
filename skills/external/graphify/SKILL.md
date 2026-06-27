# graphify

> Auto-generated from GitHub: safishamsi/graphify

## 描述
代码知识图谱 Skill。兼容 Claude Code / Codex / Cursor / Aider 等主流 AI 编码 Agent。扫描本地代码库构建实体级知识图（类、函数、文件、模块、调用关系），通过 MCP 协议向 Agent 暴露语义检索能力，让 AI 编码助手能基于真实代码结构回答问题。

## 来源
- GitHub: https://github.com/safishamsi/graphify
- Stars: 5,478+ (周新增 5,478, 2026-06-15)
- 语言: Python
- 许可证: Apache-2.0

## 核心能力
- 实体抽取：AST 解析 + LLM 增强
- 图谱存储：NetworkX + SQLite
- 语义检索：基于嵌入的混合搜索
- MCP Server 模式：被任意支持 MCP 的 Agent 调用
- 增量更新：watchdog 监听文件变更

## 集成到 AUTO-EVO-AI
- 对接 RAG 知识库：`api/routes_rag.py` 已有端到端 RAG，graphify 可作为代码域专用 retriever
- Skills 桥接：`mcpize:graphify`
- 调用方式：`POST /api/v1/mcpize/python {"repo": "graphify", "tool": "search", "query": "认证流程"}`

## 使用说明
1. 安装：`pip install graphify` 或 `npx graphify`
2. 在代码库根目录执行 `graphify init`
3. 启动 MCP Server：`graphify serve --port 7654`
4. 在 Claude Code 的 `.mcp.json` 中配置 `{"graphify": {"url": "http://localhost:7654"}}`

## 自动更新
- 扫描时间: 2026-06-16 22:00
- 来源: 51cto/博客园 6月上半旬盘点
- 周新增排名: #6

---
*由 AUTO-EVO-AI v3.2 自动生成*
