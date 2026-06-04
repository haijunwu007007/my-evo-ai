# AUTO-EVO-AI V0.1 — 2026 竞品对标分析 V3

**评估时间：** 2026-06-04 14:20
**数据来源：** Toolradar 2026-06-04 / 1337skills 2026-05-30 / GitHub 搜索

---

## 一、2026 AI Agent 平台格局

### 三强格局（2026年5月）

```
Dify (142k⭐)     = LLMOps 平台         → 端到端应用交付
n8n (130k+⭐)     = 通用自动化引擎      → 事件驱动 + 海量集成  
Langflow (60k⭐)  = LLM 图形构建器      → 透明数据流
```

**2026趋势：不再选一家，而是通过 MCP 协议组合使用。**

### MCP Gateway 市场（2026年3月-6月，快速爆发）

```
托管型:   Composio (850+集成, SOC2) | Cloudflare MCP Portals | MintMCP (SOC2)
开源型:   IBM ContextForge | Envoy AI Gateway | Docker MCP Gateway
注册表型: Smithery (6000+ 服务器目录)
```

---

## 二、MCP Gateway 竞品深度对比

### vs Composio（托管型第一名，850+ 集成）

| 维度 | Composio | AUTO-EVO-AI |
|------|---------|-------------|
| 预构建集成 | **850+**（GitHub/Jira/SFDC等） | 34（可扩展） |
| 认证管理 | ✅ 统一 OAuth 层 | 🟡 基础 SQLite 存储 |
| 零数据保留 | ✅ SOC 2 认证 | ❌ 未认证 |
| 惰性加载 | ❌ 全量加载 | ✅ **首创 MCP Gateway** |
| 工具→技能桥接 | ❌ | ✅ **首创** |
| **万能集成桥** | ❌ | ✅ **MCPize（网站/API/CLI/Python）** |
| 自托管 | ❌ 只有云版 | ✅ 单文件零依赖 |
| 价格 | 免费 2万次/月 → $29起 | **完全免费** |
| 整体架构 | 纯 MCP Gateway | **全栈平台（网关+技能+RAG+桌面+画布）** |

**差距：** 集成数量差距（850 vs 34）。但我们的万能集成桥（MCPize）是对方没有的杀手锏。

### vs IBM ContextForge（开源 MCP 网关）

| 维度 | ContextForge | AUTO-EVO-AI |
|------|-------------|-------------|
| 协议支持 | MCP + A2A + REST/gRPC | MCP + REST |
| 管理 UI | ✅ 内置管理面板 | ✅ 管理后台/admin |
| 插件数 | 40+ 插件 | **153 技能** |
| 容器隔离 | ❌ | 🟡 有 Docker 路由 |
| K8s 原生 | ✅ Helm 部署 | ❌ 单文件部署 |
| 多Agent协议 | ✅ A2A 协议 | 🟡 基础 Agent 路由 |
| 集成深度 | MCP 网关专用 | **全栈平台** |

**差距：** 支持 A2A（Agent-to-Agent）协议。但我们的技能规模（153）远超插件（40）。

### vs Cloudflare MCP Portals（安全最强）

| 维度 | Cloudflare | AUTO-EVO-AI |
|------|-----------|-------------|
| 安全模型 | Zero Trust + MFA | JWT 基础 |
| 边缘托管 | 300+ 数据中心 | 单机部署 |
| 冷启动 | 毫秒级 | 4秒（冷） |
| 可观测性 | 集中日志 | 🟡 基础日志 |
| 功能广度 | 纯网关 | **全栈平台** |

**差距：** 安全架构和边缘托管。但全栈能力完全不是一个量级。

### vs Smithery（6000+ 服务器注册表）

| 维度 | Smithery | AUTO-EVO-AI |
|------|---------|-------------|
| 服务器数量 | **6000+** | 1（内置）+ 外部自动发现 |
| 认证 | 无集中认证 | JWT + SQLite |
| 策略执行 | ❌ | ✅ RBAC |
| MCPize | ❌ | ✅ **万能集成桥** |
| 整体定位 | 仅发现层（Registry） | **全栈自动化平台** |

**差距：** 服务器生态数量巨大。但 MCPize 可以按需集成任何服务器。

---

## 三、核心结论

### AUTO-EVO-AI 的独特优势（竞品没有的）

```
1. MCPize 万能集成桥 — 任意网站/API/CLI/Python → MCP 工具 + Skill
2. MCP→Skill 桥接 — MCP 工具自动成为系统技能（153 个）
3. 全栈一体化 — MCP Gateway + RAG + 桌面自动化 + Workflow 画布 + 100 行业模板
4. 单文件零依赖部署 — 适合家庭 PC 和低配云服务器
5. 完全免费 — 托管型每月 $29-229，我们免费
```

### 竞品有我们没有的（差距清单）

| 借鉴自 | 功能 | 我们的差距 | 优先级 |
|--------|------|-----------|--------|
| **Composio** | 850+ 预构建集成 | 🔴 34 个，差 25 倍 | P0 |
| **Cloudflare** | Zero Trust 安全模型 | 🟡 只有 JWT | P1 |
| **ContextForge** | A2A Agent 间协议 | 🟡 只有基础 Agent | P1 |
| **Kong** | REST API → MCP 自动转 | 🟡 MCPize 需要手动 | P1 |
| **Docker MCP** | 容器隔离执行 | 🟡 有路由无隔离 | P2 |
| **Smithery** | 6000+ 服务器注册表 | 🟡 手动发现 | P2 |

### 我们应该优先做的

```
P0: 集成数量扩大到 100+（预定义 JSON 模板）
P1: REST API → MCP 自动转换（给个 OpenAPI URL 自动生成）
P1: A2A 协议支持（Agent 与 Agent 直接通信）
P2: 容器隔离执行（每个 MCP 工具在独立容器中运行）
P2: 边缘/多节点部署支持
```

### 一句话总结

> **我们是唯一把 MCP Gateway、Skills 桥接、万能集成桥、RAG、桌面自动化、Workflow 画布融为一体的全栈平台。竞品在各自细分领域更深，但我们的架构设计（MCPize + 桥接 + 惰性加载）是 2026 年最具创新性的。最大的短板是集成数量（34 vs 850+），但这可以通过 MCPize 的万能集成能力来弥补。**
