# AUTO-EVO-AI 全系统架构审查报告 v1.0
> 目标：打造真正能自动完成几乎所有工作的智能体系统
> 当前状态：2026-06-05 23:07

---

## 一、现有组件总览（6层）

```
┌─────────────────────────────────────────────────────────────────┐
│  F1: 前端层 (chat.html / dashboard / 游戏页面)                    │
│  功能：用户交互、消息展示、认证                                    │
│  问题：chat.html渲染使用textContent，不支持图片/链接显示           │
│        context传递残缺，provider选型没用上                        │
├─────────────────────────────────────────────────────────────────┤
│  F2: API入口层 (api_server.py / api/infra.py)                    │
│  功能：路由注册、模块注册表、模块执行核心、限流缓存                │
│  问题：infra._execute_module_internal() 支持同步调用也支持异步     │
│        但 routes_smart_chat.py 没用它                             │
├─────────────────────────────────────────────────────────────────┤
│  F3: LLM层 (core/llm_gateway.py / routes_llm_chat.py)           │
│  功能：LLMPool网关(7种Provider自动识别/故障转移/缓存/成本追踪)    │
│        以及 routes_llm_chat.py 直连转发(13种Provider)             │
│  问题：LLMPool的chat_sync()不支持tools(函数调用)参数              │
│        routes_llm_chat.py 独立于LLMPool，两套Provider配置         │
│        chat_sync()入口参数是prompt(str)，不是messages(list)       │
├─────────────────────────────────────────────────────────────────┤
│  F4: 意图理解层 (core/intelligent_coordinator.py)                │
│  功能：IntentParser意图解析、WorkflowPlanner多步规划              │
│        DataFlowMapper数据流映射、经验学习                         │
│  问题：1106行代码，功能完备，但只在WebSocket路径被调用            │
│        智能协调器已经加载但没被REST API使用                       │
├─────────────────────────────────────────────────────────────────┤
│  F5: 协调执行层 (modules/system_coordinator_v3/)                 │
│  功能：SystemCoordinatorV3、ModuleCapabilityGraph、AutonomousLoop│
│        CrossModuleOrchestrator多模块编排                          │
│  问题：3982行代码，但大多数情况降级到ModuleCapabilityGraph桩类    │
│        IntelligentCoordinator加载但双重检查易失败                 │
│        Coordinator.execute()路径太长(6步降级链)                   │
├─────────────────────────────────────────────────────────────────┤
│  F6: 模块层 (modules/ 457个模块)                                 │
│  功能：457个功能模块，6个重型核心，115个真实模块，304个半真实     │
│  问题：LLM不知道这些模块存在，不知道每个模块能做什么              │
│        没有统一的模块元数据注册机制给LLM使用                      │
│        routes_coordinator.py用subprocess执行模块(绕过infra)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、必须改的6件事（按优先级）

### P0：统一LLM调用入口

**现状：**
- `routes_smart_chat.py` 自己有 `_call_llm()` 手写httpx
- `routes_llm_chat.py` 自己有13个Provider硬编码
- `routes_services.py` 有 `get_llm_pool().chat_sync()` 
- 3套LLM调用逻辑互不连通

**改成：**
```
所有路由 → get_llm_pool().chat_sync() 或 get_llm_pool().chat_stream_sync()
  ├── 统一识别Key（管你填啥Key）
  ├── 统一故障转移（Provider挂了自动切换）
  ├── 统一缓存（省token）
  └── 统一成本追踪
```

**改动范围：**
- `routes_smart_chat.py` — 删掉 _call_llm()，改用 pool.chat_sync()
- `routes_llm_chat.py` — 保持兼容但标记 deprecated

### P0：让LLM知道457个模块

**现状：**
- LLM只知道5个手写工具
- 457个模块一个都不知道

**改成：**
```python
# 注册模块元数据API
GET /api/v1/modules/catalog → 返回所有模块的分类/描述/动作
# 智能体会调这个接口获取模块列表
```

**改动范围：**
- `routes_modules.py` 或 `routes_smart_chat.py` — 增加模块目录API
- `routes_smart_chat.py` — 工具注册时包含模块目录

### P1：统一模块执行

**现状：**
- `routes_smart_chat.py` 自己写 _exec() 实现工具
- `routes_coordinator.py` 用 subprocess 执行模块
- `infra._execute_module_internal()` 正确接口反而没用

**改成：**
```
所有路由 → infra._execute_module_internal(模块名, 动作, 参数)
```

**改动范围：**
- `routes_smart_chat.py` — execute_module 工具直接调 infra._execute_module_internal
- `routes_coordinator.py` — subprocess路径改为调用 infra

### P1：打通智能协调器

**现状：**
- `IntelligentCoordinator` (1106行) 已加载但只用WebSocket
- 每次请求走6步降级链，经常失败

**改成：**
```
routes_smart_chat.py → IntelligentCoordinator.process()
  → 意图解析 → 模块推荐 → 多步编排 → 执行
  → 失败降级到直接调模块
```

**改动范围：**
- `routes_smart_chat.py` — 复杂任务走 coordinator
- `coordinator.py` — 简化降级链（不需要6步）

### P2：记忆学习系统全局化

**现状：**
- `routes_smart_chat.py` 有自己的 _remember/_recall
- `IntelligentCoordinator` 有自己的经验学习
- 两套记忆不互通

**改成：**
```
统一记忆中心 data/agent_memory.db
├── memory 表: 对话记忆
├── module_scores 表: 模块评分
├── patterns 表: 使用模式
└── fail_patterns 表: 失败模式
```

**改动范围：**
- 新建 `core/agent_memory.py` — 集中管理5张表
- `routes_smart_chat.py` 和 `IntelligentCoordinator` 都调这个

### P2：前端全面升级

**现状：**
- chat.html用textContent渲染，不支持图片/链接
- 没有区分"LLM思考"和"模块执行中"的loading状态
- 没有显示执行进度

**改成：**
- 支持markdown渲染（图片、链接、代码块）
- 显示执行状态（🤔思考 / ⚙️执行 / ✅完成 / ❌失败）
- 支持流式输出

---

## 三、不改的部分

| 组件 | 原因 |
|------|------|
| api_server.py | 路由注册正常 |
| api/infra.py | 模块执行核心正常（只是别人没用它） |
| core/llm_gateway.py | LLM网关正常 |
| modules/ 全部 | 模块本身正常 |
| api/middleware.py | 中间件正常 |
| api/startup.py | 后台任务正常 |
| api/routes_* (除smart_chat) | 功能正常 |

---

## 四、总结

| 优先级 | 改什么 | 影响文件 | 预计行数 |
|--------|--------|---------|---------|
| P0 | 统一LLM调用 | routes_smart_chat.py | 删20行，加5行 |
| P0 | LLM知道模块 | routes_smart_chat.py + routes_modules.py | 加30行 |
| P1 | 统一模块执行 | routes_smart_chat.py + routes_coordinator.py | 删30行，加10行 |
| P1 | 打通协调器 | routes_smart_chat.py + coordinator.py | 加40行 |
| P2 | 记忆全局化 | 新建core/agent_memory.py | 加80行 |
| P2 | 前端升级 | chat.html | 加40行 |

**全部改完：** 约200行净新增，不破坏任何现有功能。
