# open-notebook

> Auto-generated from GitHub: lfnovo/open-notebook

## 描述
开源版 NotebookLM。上传 PDF/网页/音视频，自动提取内容 → AI 摘要 → 多轮对话。支持多源知识库、播客生成、引用溯源。完全本地部署，数据可控。

## 来源
- GitHub: https://github.com/lfnovo/open-notebook
- Stars: 3,468+ (周新增 3,468, 2026-06-15)
- 语言: Python
- 许可证: MIT

## 核心能力
- 多格式摄取：PDF/EPUB/Markdown/YouTube/音频
- 内容分块 + 嵌入（surreal-db + fastembed）
- 引用溯源：每条回答标注原文段落
- 播客生成：双 TTS 对话合成
- 多 Notebook 隔离
- 部署：Docker 一键起

## 集成到 AUTO-EVO-AI
- 对接 RAG 端点：`api/routes_rag.py` 可桥接 open-notebook 作为多模态摄取器
- Skills 桥接：`mcpize:open-notebook`
- 调用方式：`POST /api/v1/mcpize/python {"repo": "open-notebook", "tool": "ask", "notebook_id": "xxx", "question": "..."}`

## 使用说明
1. `git clone https://github.com/lfnovo/open-notebook && cd open-notebook`
2. `cp .env.example .env` 填入 LLM API Key
3. `docker compose up -d`
4. 访问 http://localhost:8502

## 自动更新
- 扫描时间: 2026-06-16 22:00
- 来源: 51cto/博客园 6月上半旬盘点
- 周新增排名: #11

---
*由 AUTO-EVO-AI v3.2 自动生成*
