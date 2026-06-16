# AUTO-EVO-AI 能力全景分析 · 差缺补遗

> 全面盘点现有能力，定位缺口，规划从 0.1 到 1.0 的完整路径

---

## 一、现有能力概览

### ✅ 已就绪（500+功能点）

| 层 | 内容 | 数量 |
|----|------|------|
| 🖥️ API路由 | 75个路由文件 | 覆盖chat/agent/模块/CI/CD/网关/多租户 |
| 🧠 核心引擎 | 47个引擎文件 | 决策/协调/进化/调度/事件/管道 |
| 📦 业务模块 | 500+模块 | AI/安全/数据/运维/企业级全覆盖 |
| 🎨 前端 | 聊天 + 管理后台 | 9语言、80+快捷工具、18标签管理 |
| 🤖 LLM | 本地+云端双模型自动路由 | Qwen3.6(迅捷) + R1(保底) |
| 🏗️ 基础设施 | Prometheus/JWT/Docker CI/CD | 完整可观测+安全+部署链 |

### ❌ 缺失的核心能力

| # | 缺口 | 影响 | 优先级 |
|---|------|------|--------|
| **1** | 可视化开源心 | 用户无法看到和管理开源项目 | 🔴 P0 |
| **2** | 拖拽编排画布 | 无法可视化组合项目 | 🔴 P0 |
| **3** | 项目发现引擎 | 用户不知道有哪些开源项目可用 | 🔴 P0 |
| **4** | 二次开发系统 | 用户无法在开源项目上衍生创新 | 🔴 P0 |
| **5** | 统一前端框架 | 当前chat.html+admin.html维护困难 | 🟡 P1 |
| **6** | Code Server集成 | 不能在线编辑代码 | 🟡 P1 |
| **7** | 用户引导教程 | 第一次使用不知道做什么 | 🟡 P1 |
| **8** | Docker运行时UI | 当前只有静态文本 | 🟡 P1 |
| **9** | 智能体虚拟公司 | 无CEO Agent协同 | 🟢 P2 |
| **10** | 社区/市场 | 用户不能分享衍生项目 | 🟢 P2 |

---

## 二、详细缺口分析

### 2.1 🔴 可视化开源中心（无→全新建）

**现状**：发现页、画布、集成流程、运行监控 → **完全不存在**

**需要新建的模块**：

```
backend/
├── api/routes/routes_hub.py          # [新建] 开源中心API
├── api/hub/                          # [新建] 开源中心引擎
│   ├── __init__.py
│   ├── discover.py                   # 项目发现(GitHub/HF API)
│   ├── integrate.py                  # 集成引擎(依赖分析+部署)
│   ├── compose.py                    # 编排引擎(组合管理)
│   ├── runtime.py                    # 运行时管理(Docker/进程)
│   ├── fork_dev.py                   # 二次开发引擎
│   ├── security.py                   # 安全沙箱
│   └── models.py                     # 数据模型(SQLite)
frontend/
├── hub/                              # [新建] 开源中心前端
│   ├── HubDiscover.html              # 发现页
│   ├── ProjectDetail.html            # 项目详情
│   ├── HubDashboard.html             # 已集成项目
│   ├── ComposeCanvas.html            # 编排画布(核心)
│   ├── ForkStudio.html               # 二次开发工作台
│   └── HubTemplates.html             # 模板市场
```

**依赖**：httpx(已有), docker-py(需安装), VueFlow CDN

### 2.2 🔴 拖拽编排画布（无→全新建）

**现状**：画布组件 → **完全不存在**

**需要新建**：
- 基于 VueFlow (vue3) 的独立 HTML 页面
- 或使用纯 JS 的拖拽库 (interact.js + leader-line)
- 节点拖拽、连线、组合、配置面板

**前端技术选型**：
```
方案A: Vue 3 + VueFlow (推荐)
  - 组件化好, 生态成熟
  - 需要加载 vue3 + vueflow CDN (~200KB)

方案B: 纯JS + interact.js + LeaderLine
  - 无框架依赖, 更轻量
  - 但需要自己实现节点渲染
```

### 2.3 🟡 统一前端框架（改进）

**现状**：chat.html(57KB) + admin.html(16KB) → 纯手写JS，维护困难

**改进方案**：不替换框架，而是用**组件化模板**：
- `frontend/templates/` → 独立可复用的 HTML 片段
- `frontend/js/` → 拆分 JS 为独立文件
- 后端 API 直接返回模板组合

### 2.4 🟡 Code Server 集成（改进）

**现状**：`routes_code_server.py` 已经存在（1.17KB），但有未注册到路由

**需要做**：
1. 注册 `routes_code_server.py` 到 `api_server.py`
2. 确认 Code Server 容器配置
3. 在开源中心二次开发工作台中集成

### 2.5 🟡 用户引导教程（新建）

**现状**：无首次使用引导

**需要新建**：
- `frontend/tutorial.html` → 首次登录引导浮层
- 分步引导：选择身份→推荐场景包→第一个集成

### 2.6 🟡 Docker运行时UI（改进）

**现状**：admin.html 的 Docker 标签页只有静态文本

**需要**：
- 调用 Portainer API (已有 `routes_portainer.py`)
- 实时显示容器状态、资源使用
- 启停操作

---

## 三、实施路线图

### Phase 0 — 基础加固（2天）

| 任务 | 文件 | 工作量 |
|------|------|--------|
| 注册6个未激活路由 | api_server.py | 0.5h |
| 修复死代码(frontend_i18n_js) | api_server.py | 0.5h |
| 配置SMTP/分钟 | .env | 0.5h |
| 统一agent_llm.py提供者配置 | agent_llm.py | 1h |

### Phase 1 — 开源中心核心（5天）

| 任务 | 产出 | 工作量 |
|------|------|--------|
| PyPI 项目发现引擎 | hub/discover.py | 1天 |
| 项目卡片API+发现页UI | routes_hub.py + HubDiscover.html | 1天 |
| 集成引擎(依赖分析+部署) | hub/integrate.py | 1.5天 |
| 集成流程UI | IntegrateWizard.html | 0.5天 |
| 运行监控API+仪表盘 | hub/runtime.py + HubDashboard.html | 1天 |

### Phase 2 — 可视化画布（4天）

| 任务 | 产出 | 工作量 |
|------|------|--------|
| VueFlow画布集成 | ComposeCanvas.html | 1.5天 |
| 节点拖拽+连线 | 同上 | 1天 |
| 组合创建API | hub/compose.py | 0.5天 |
| 属性面板+配置编辑 | 同上 | 1天 |

### Phase 3 — 二次开发系统（3天）

| 任务 | 产出 | 工作量 |
|------|------|--------|
| Fork引擎(git clone+管理) | hub/fork_dev.py | 1天 |
| Code Server集成 | hug/integrate.py + api_server.py | 0.5天 |
| 二次开发工作台UI | ForkStudio.html | 1天 |
| AI辅助开发API | hub/fork_dev.py | 0.5天 |

### Phase 4 — 打磨完善（3天）

| 任务 | 产出 | 工作量 |
|------|------|--------|
| 首次使用引导 | tutorial.html | 0.5天 |
| 模板市场(导出/导入) | HubTemplates.html | 1天 |
| 社区分享功能 | routes_hub.py | 0.5天 |
| 用户手册+视频 | docs/ | 1天 |

### Phase 5 — 虚拟公司智能体（远期）

| 任务 | 产出 |
|------|------|
| CEO Agent(目标拆解) | agent_ceo.py |
| 虚拟公司Dashboard | CompanyDashboard.html |
| Agent间通信协议 | 已有A2A协议基础 |
| 自我进化引擎 | 已有evolution_engine.py |

---

## 四、已有基础与复用

| 已有模块 | 直接复用 |
|---------|---------|
| `docker_manager.py` (38KB) | Docker部署引擎 |
| `routes_portainer.py` | Docker管理UI |
| `routes_gitea.py` | Git仓库管理 |
| `routes_code_server.py` | 在线编辑器 |
| `git_ops.py` (27KB) | Git操作(克隆/Fork) |
| `evolution_engine.py` (22KB) | 进化引擎 |
| `github_scanner.py` (31KB) | Github扫描(已有基础) |
| `routes_gateway.py` (500+集成模板) | 集成模板库 |
| `project_mgmt.py` (36KB) | 项目管理 |
| `agent_llm.py` | LLM自动路由 |
| `agent_hermes.py` (23KB) | 消息Agent |
| `agent_athena.py` (24KB) | 策略Agent |

---

## 五、总结：从 V0.1 到 V1.0 的差距

```
现状 V0.1             目标 V1.0              差距
─────────────────────────────────────────────────
500+ 模块            [已有]                 
75路由               [已有]                 
聊天+管理后台        开源中心 + 画布 + 工作台   🔴 缺口
无法发现项目          GitHub/HF发现页          🔴 缺口
无编排画布           拖拽组合系统              🔴 缺口
无二次开发           Fork工作台               🔴 缺口
无引导              首次使用教程              🟡 缺口
Docker静态文本      实时容器管理              🟡 缺口
纯手写前端          组件化模板                🟡 缺口
R1+Qwen3.6          [已有]                 
无虚拟公司           CEO Agent+部门Agent      🟢 远期
```

**最短路径到 V1.0 = Phase 0~3 = 14 天**

从今天开始算，14天后用户打开 Evo 看到的是：
1. 开源项目发现页（像逛应用商店）
2. 拖拽画布（像搭积木一样组合项目）
3. 二次开发工作台（改代码 Fork 发布）
4. 首次使用引导（打开就知道做什么）
5. 实时 Docker 管理（看到容器状态）

---

*设计文档: v0.5 · 2026-06-16*  
*相关文件: open-source-hub-architecture.md, open-source-hub-visual-operations.md, open-source-catalog.md, agent-os-whitepaper.md*
