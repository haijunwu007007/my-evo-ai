# cc-switch

> Auto-generated from GitHub: farion1231/cc-switch

## 描述
多 AI 编码 Agent 切换器。在 Claude Code、Codex、Cursor、Aider 等多个 AI 编码助手之间统一切换 API Key、Base URL 和模型配置。支持环境变量热切换，无需重启 IDE。配套 Tauri 桌面端，跨平台 (macOS/Linux/Windows)。

## 来源
- GitHub: https://github.com/farion1231/cc-switch
- Stars: 6,621+ (周新增 6,621, 2026-06-15)
- 语言: Rust + TypeScript
- 许可证: MIT

## 核心能力
- 多 Agent 统一配置：Claude Code / Codex / Cursor / Aider / Cline / Continue
- Provider 热切换（Anthropic / OpenAI / DeepSeek / 智谱 / Ollama）
- 配置文件加密存储（keyring）
- 一键备份与恢复
- MCP Server 集中管理

## 集成到 AUTO-EVO-AI
- 路由对应：`api/routes_gateway.py` 已有 31 个集成模板，可桥接 cc-switch 作为 Provider 切换层
- Skills 桥接：`gateway:cc-switch`
- 调用方式：`POST /api/v1/gateway/call {"integration": "cc-switch", "action": "switch", "provider": "deepseek"}`

## 使用说明
1. 安装：`brew install cc-switch` (macOS) 或下载 release
2. 启动后选择目标 Agent 目录
3. 在 GUI 中切换 Provider，配置即时生效
4. AUTO-EVO-AI 通过 Gateway 调用切换 API，实现 Evo 内部 LLM 路由

## 自动更新
- 扫描时间: 2026-06-16 22:00
- 来源: 51cto/博客园 6月上半旬盘点
- 周新增排名: #4

---
*由 AUTO-EVO-AI v3.2 自动生成*
