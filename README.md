# AUTO-EVO-AI V0.1

> 生产级 AI Agent 自动化平台 — **457 模块** · **185+ API** · **4 核心引擎** · **3500+ 测试通过**

> ⚠️ **Python 版本要求**: Python >=3.11（推荐 3.11 或 3.12）。不兼容 Python 3.10 及以下版本。

## 🚀 5分钟启动

### 已有依赖
```bash
git clone https://github.com/haijunwu007007/my-evo-ai.git
cd my-evo-ai
pip install -r requirements.txt
python api_server.py
```
打开 http://127.0.0.1:8765/dashboard

### 访问 API 文档
- **Swagger UI**: http://127.0.0.1:8765/docs
- **OpenAPI JSON**: http://127.0.0.1:8765/openapi.json
- **前端 SPA**: http://127.0.0.1:5173 （需额外启动：`cd frontend && npx vite`）

### 从头开始
```bash
git clone https://github.com/haijunwu007007/my-evo-ai.git
cd my-evo-ai
python -m venv venv
# Windows: venv\Scripts\activate  |  Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python api_server.py
```

### Docker
```bash
git clone https://github.com/haijunwu007007/my-evo-ai.git
cd my-evo-ai
docker compose up -d
```

### 手机访问
电脑和手机同一WiFi：`http://<电脑IP>:8765/dashboard`

## 系统架构

```
AUTO-EVO-AI V0.1/
├── api_server.py          # FastAPI 主服务 (345行入口)
├── frontend/              # 独立前端 (可独立部署)
│   ├── dashboard/         # Dashboard 前端 (手机+PC响应式)
│   └── serve.py           # 独立前端开发服务器
├── api/                   # API 层
│   ├── middleware.py       # 安全/限流/认证中间件
│   ├── startup.py          # 启动脚本/后台任务
│   ├── routes_*.py         # 4个路由模块 (模块/服务/WS/认证)
│   └── infra.py            # 基础设施 (注册表/协调器)
├── core/                  # 16个核心引擎
│   ├── data_layer.py       # SQLite 数据层 (事务/迁移/批量)
│   ├── message_bus.py      # 消息总线 (发布订阅/持久化队列)
│   ├── auth_provider.py    # JWT 认证 / RBAC
│   ├── logging_config.py   # 结构化 JSON 日志
│   ├── evo_brain.py        # AI 大脑
│   ├── module_manager.py   # 模块管理器
│   ├── modules_loader.py   # 模块加载器
│   ├── llm_gateway.py      # LLM 智能网关
│   ├── external_services.py # 13渠道通知
│   ├── doc_generator.py    # 文档生成 (PDF/Word/Excel/PPT)
│   ├── cicd_engine.py      # CI/CD 引擎
│   ├── pipeline_engine.py  # 模块管线引擎
│   ├── config_center.py    # 统一配置中心
│   ├── scheduler_engine.py # 定时调度器
│   ├── task_queue_engine.py # 持久化任务队列
│   └── ws_engine.py        # WebSocket 实时推送
├── modules/               # 457个功能模块 (0空壳)
│   └── _base/             # 企业级模块基类 (熔断/限流/审计/追踪)
├── config/                # 配置系统
│   ├── defaults.yaml       # 默认配置
│   └── environments/       # 环境覆盖配置
├── benchmarks/             # 性能基准测试
├── requirements.txt        # Python 依赖
├── .github/workflows/      # GitHub Actions CI
└── .evo_data/              # 运行时数据 (自动创建)
```

## 核心能力

| 引擎 | 功能 |
|------|------|
| SQLite 数据层 | 线程安全连接池 · Schema 迁移 · 批量操作 · JSON→SQLite 迁移 |
| 消息总线 | 发布订阅 · 通配符主题 · SQLite 持久化队列 · 历史查询 |
| JWT 认证 | 令牌签发/验证 · RBAC 角色权限 · API Key 认证 |
| 模块管线 | DAG拓扑排序 · 字段级映射 · 条件分支 · 并行 · 循环 · 重试 |
| LLM网关 | 多Provider故障转移 · 流式SSE · 缓存 · 成本追踪 |
| 定时调度 | Cron · 间隔 · 一次性 · 日历 · 断电恢复 |
| 事件驱动 | 发布订阅 · 文件监听 · Webhook · 规则引擎 |
| 任务队列 | 4优先级 · 延迟 · 指数退避重试 · 死信 · 多Worker |
| WebSocket | 7频道隔离 · 实时日志流 · 心跳 · 历史缓冲 |
| 配置中心 | 30+预置模板 · 环境变量注入 · 脱敏 · 持久化 |
| 文档生成 | Word · Excel · PPT · Markdown · HTML |
| CI/CD | GitHub Actions · Git · Docker 集成 |
| 通知推送 | 企微 · 钉钉 · 飞书 · 短信 · 邮件 · Slack · Telegram · Discord · 共15通道 |

## 技术规格

| 指标 | 数值 |
|------|------|
| **Python 代码** | 722+ 文件 / 13.9 MB |
| **功能模块** | 457 个（0 空壳，全部有真实 dispatch 逻辑） |
| **API 端点** | 185 路由 |
| **测试覆盖** | 34 个测试文件 / 3534 用例，100% 真实 HTTP 请求，零 Stub / Mock |
| **Git 提交** | 125 commits |
| **CI 管道** | GitHub Actions（推代码自动跑合规+E2E测试） |
| **模块平均 actions** | 8-10 个 |
| **基础设施** | SQLite 数据层 / JWT 认证 / 消息总线 / JSON 日志 |

## 技术栈

- **后端**: Python 3.13 / FastAPI / Uvicorn / SQLite WAL / asyncio
- **前端**: 原生 HTML/CSS/JS (零框架依赖, 57KB) / 响应式设计 / PWA
- **AI**: 智谱 GLM-4-Flash (默认) / DeepSeek / OpenAI / Anthropic / Ollama
- **测试**: pytest 9.x / 34 个真实测试文件 / 3500+ 测试用例 / 全真实链路校验 / 零 Stub / GitHub Actions CI
- **安全**: JWT / RBAC / 限流 / 熔断 / 链路追踪 / 审计

## 配置向导

首次打开 Dashboard 自动弹出配置向导：

1. **AI Provider** — 智谱 / DeepSeek / OpenAI / Anthropic / Ollama
2. **通知渠道** — 企微 / 钉钉 / 飞书 / 邮件 / 共13通道
3. **自动化任务** — 健康巡检 / 安全扫描 / 性能报告 / 日志清理
4. **事件规则** — 异常告警 / CPU监控 / 安全威胁

## API 文档

启动服务后访问：http://127.0.0.1:8765/docs

## CI/CD

```yaml
# .github/workflows/ci.yml
# 推送到 master/develop 或 PR 时自动:
#   1. 安装依赖
#   2. 运行 3500+ 测试
#   3. 启动服务验证 API
#   4. 运行基准测试
```

## 许可证

Apache 2.0 License
