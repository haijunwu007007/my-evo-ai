# fff

> Auto-generated from GitHub: dmtrKovalenko/fff

## 描述
AI Agent 本地文件搜索引擎。用 Rust 写，号称"比 fd 快 10 倍"。支持正则、文件名、扩展名、文件类型、文件大小过滤，针对代码库和大型项目优化。与 Claude Code、Cursor 等 Agent 配套使用，作为本地工具调用层。

## 来源
- GitHub: https://github.com/dmtrKovalenko/fff
- Stars: 1,617+ (周新增 1,617, 2026-06-15)
- 语言: Rust
- 许可证: MIT

## 核心能力
- 极速文件名/内容搜索（ripgrep 内核 + 自研索引）
- 支持 .gitignore 自动遵守
- JSON 输出：方便 Agent 解析
- 并发安全：可同时被多个 Agent 调用
- 编译产物 < 5MB，单二进制

## 集成到 AUTO-EVO-AI
- 对接 Agent 引擎：`api/routes_agent_engine.py` 自主 Agent 步骤执行
- Skills 桥接：`mcpize:fff`
- 调用方式：`POST /api/v1/mcpize/cli {"cmd": "fff", "args": ["--json", "name:*.py", "src/"]}`

## 使用说明
1. `cargo install fff` 或下载 release
2. `fff "name:*.py" ./src`  搜索所有 .py 文件
3. `fff "content:async def" .`  搜索包含 async def 的文件
4. 在 Agent 配置中将其注册为本地工具

## 自动更新
- 扫描时间: 2026-06-16 22:00
- 来源: 51cto/博客园 6月上半旬盘点
- 周新增排名: #13

---
*由 AUTO-EVO-AI v3.2 自动生成*
