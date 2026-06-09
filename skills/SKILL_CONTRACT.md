# SKILL_CONTRACT.md — AUTO-EVO-AI 技能合约规范

本文档定义了 AUTO-EVO-AI 系统中所有技能的注册、发现、执行和生命周期管理规范。

## 技能合约格式

每个技能必须包含以下字段：

```json
{
  "name": "技能名称（唯一标识）",
  "version": "1.0.0",
  "description": "技能描述",
  "author": "作者",
  "type": "builtin|custom|external|mcp|gateway",
  "capabilities": ["能力列表"],
  "entry": "入口文件或命令",
  "dependencies": ["依赖列表"]
}
```

## 技能注册

通过 `POST /api/v1/skills/register` 注册新技能，或放入 `skills/custom/` 目录自动发现。

## 技能发现

- `GET /api/v1/skills` — 获取全部技能列表（支持 type 过滤）
- `GET /api/v1/skills/search?q=关键词` — 搜索技能
- `GET /api/v1/skills/{name}` — 获取技能详情

## 技能执行

`POST /api/v1/skills/{name}/execute` 执行技能，支持参数传递。

## 技能类型

| 类型 | 说明 | 来源 |
|------|------|------|
| builtin | 内置技能 | skills/builtin/ |
| custom | 用户自定义 | skills/custom/ |
| external | 外部桥接 | WorkBuddy自动发现 |
| mcp | MCP工具桥接 | MCP服务器 |
| gateway | 集成网关 | Gateway连接器 |

## 当前技能

### 内置技能（18个）
1. text — 文本处理
2. document — 文档生成
3. code — 代码生成
4. image — 图片处理
5. search — 搜索
6. crawl — 爬虫
7. translate — 翻译
8. calculator — 计算
9. github — GitHub工具
10. memory — 记忆管理
11. todo — 待办管理
12. ppt — PPT生成
13. excel — Excel处理
14. voice — 语音
15. screenshot — 截图
16. scaffold — 脚手架
17. docker — Docker
18. app_launcher — 应用启动

### 外部桥接技能（28+）
通过 WorkBuddy 的 ~/.workbuddy/skills/auto-discovered/ 自动发现注册。

### MCP桥接工具（8+）
通过 api/routes_mcp.py 的 MCP 网关将 MCP 工具桥接为 skill 格式。

### 网关集成（101+）
通过 api/routes_gateway.py 将 101+ 集成连接器桥接为 gateway: 前缀的技能。
