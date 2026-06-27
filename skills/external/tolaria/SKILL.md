# tolaria

> Auto-generated from GitHub: refactoringhq/tolaria

## 描述
Markdown 知识库桌面端。基于 Electron + React，把本地 Markdown 文件夹变成类 Obsidian/Notion 的双向链接知识库。支持全文搜索、标签、链接图谱、AI 摘要。专为个人/小团队知识管理设计，数据完全本地。

## 来源
- GitHub: https://github.com/refactoringhq/tolaria
- Stars: 3,592+ (周新增 3,592, 2026-06-15)
- 语言: TypeScript
- 许可证: MIT

## 核心能力
- 文件夹即库：选定目录自动索引所有 .md
- 双向链接：[[wiki-style]] 解析
- 全文搜索：基于 ripgrep 即时
- 链接图谱：d3-force 渲染
- AI 摘要：可选接入 OpenAI / Ollama / 智谱
- 离线优先：无需账号，配置存本地

## 集成到 AUTO-EVO-AI
- 对接 EvoNexus：可作为 `modules/ai_memory.py` 的桌面端伴侣
- Skills 桥接：`mcpize:tolaria`
- 调用方式：`POST /api/v1/mcpize/cli {"cmd": "tolaria", "args": ["search", "agent"]}`

## 使用说明
1. 下载安装：https://github.com/refactoringhq/tolaria/releases
2. 启动后选择知识库根目录
3. 启用 AI 摘要（可选，配置 LLM API Key）
4. 在 AUTO-EVO-AI 中通过 MCPize 调用其搜索/摘要能力

## 自动更新
- 扫描时间: 2026-06-16 22:00
- 来源: 51cto/博客园 6月上半旬盘点
- 周新增排名: #10

---
*由 AUTO-EVO-AI v3.2 自动生成*
