# AUTO-EVO-AI 智能体架构重设计 v2.5

> 设计目标：一个真正能工作、越用越好的智能体系统
> 核心理念：LLM决策 + 457模块执行 + 全场景容错 + 持续学习

## 第一章：总体架构图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            用户 (浏览器/API)                              │
│  输入: 文本 / 文件(未来) / 图片(未来)                                    │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ POST /api/v1/smart
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  routes_smart_chat.py (薄层编排器 ~320行)                                 │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  前置检查层                                                          │   │
│  │  ├── 消息为空？ → 400                                              │   │
│  │  ├── 测试/试试？ → _LAST_APP[t] 返回上次结果                        │   │
│  │  ├── 敏感内容（涉黄/涉政/违法） → 拒绝                              │   │
│  │  ├── 白名单检查 → 禁止模块自动执行                                   │   │
│  │  └── 无Key → 本地兜底 + 提示                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                 │                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LLM决策循环（最多3轮，每轮不同温度准确控制）                        │   │
│  │                                                                      │   │
│  │  第1轮: _call_llm(temperature=0.1, max_tokens=2048)                │   │
│  │    ├── LLM返回聊天 → 直接回复                                       │   │
│  │    ├── LLM返回工具 → _exec() → 结果回注                            │   │
│  │    ├── LLM超时 → 自动重试1次（可能临时网络问题）                     │   │
│  │    └── LLM连续失败 → 换Provider重试                                  │   │
│  │         │                                                            │   │
│  │  第2轮: _call_llm(temperature=0.2, max_tokens=2048, 带第1轮结果)   │   │
│  │    ├── 成功 → 继续/总结/调下一个                                     │   │
│  │    ├── 失败(参数错) → LLM修正参数再试                                │   │
│  │    ├── 失败(模块不存在) → LLM换同类模块                              │   │
│  │    └── 失败(权限不足) → 提示用户配置 → 跳过                         │   │
│  │         │                                                            │   │
│  │  第3轮: _call_llm(temperature=0.3, max_tokens=4096, 最后一轮)      │   │
│  │    ├── 完成 → 总结                                                  │   │
│  │    └── 未完成 → 强制结束，说明原因                                   │   │
│  │                                                                      │   │
│  │  卡住检测（全程实时监控）：                                           │   │
│  │    ├── 连续2轮相同工具+参数 → _stuck_count++                         │   │
│  │    ├── 连续2轮相同回复内容 → _stuck_count++                          │   │
│  │    ├── 连续3轮全部失败 → _stuck_count++                             │   │
│  │    ├── 超过Token预算(8192) → 强制结束                               │   │
│  │    └── _stuck_count >= 2 → 打断                                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                 │                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  后处理层（结果优化）                                                │   │
│  │  ├── 结果太短(小于15字符) → 从_LAST_APP取链接追加                   │   │
│  │  ├── 没有中文字符 → 强制LLM用中文重生成                             │   │
│  │  ├── 包含错误 → 但部分成功 → 告诉用户哪些成功/哪里失败              │   │
│  │  ├── _remember() → 保存到记忆库                                    │   │
│  │  ├── _update_score() → 更新模块评分                                │   │
│  │  └── 审计日志 → 记录完整执行链                                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────────┐
          ▼                        ▼                            ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  工具执行层         │  │  记忆学习层         │  │  安全审计层         │
│                    │  │                    │  │                    │
│  execute_module    │  │  SQLite 5张表     │  │  白名单过滤        │
│  draw_image        │  │  ├── memory        │  │  敏感操作确认      │
│  web_search        │  │  ├── module_scores │  │  审计日志          │
│  get_module_info   │  │  ├── patterns      │  │  成本追踪          │
│                    │  │  ├── fail_patterns │  │  Key脱敏          │
│  执行保护：        │  │  └── execution_log │  │                    │
│  ├─ 熔断器         │  │                    │  │  动作白名单：      │
│  ├─ 限流器         │  │  冷启动专家规则    │  │  status/health ✓  │
│  └─ 超时控制       │  │  (50条预置映射)    │  │  delete/format ✗  │
└────────┬──────────┘  └───────────────────┘  └───────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  api/infra._execute_module_internal() — 模块执行核心                      │
│                                                                          │
│  ├── 模块存在 → 执行 → 返回标准格式 {success, result/error}              │
│  ├── 模块不存在 → 返回友好错误（不抛异常）                                │
│  ├── 模块执行异常 → 捕获 → 返回错误信息                                  │
│  ├── 模块超时(30s) → 断开 → 返回超时提示                                │
│  └── 模块白名单 → 禁止自动执行危险操作                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

## 第二章：LLM Provider适配层

### 2.1 Key自动识别

```
用户输入的Key → 自动识别Provider → 选择对应endpoint+模型

sk-开头:
  ├── 有 OPENAI_BASE_URL → OpenAI / 自定义兼容
  └── 无 OPENAI_BASE_URL → DeepSeek

非sk-开头(包含小数点):
  └── 智谱GLM

无Key:
  └── 本地兜底模式
```

### 2.2 LLM回退链（Provider故障转移）

```
主Provider失败时（401/429/500/超时），自动换备用：

路径1（有OpenAI Key时）:
  OpenAI GPT-4o → DeepSeek (自动故障转移，core/llm_gateway已有)

路径2（有智谱Key时）:
  智谱 GLM-4 → 直接返回（无备用）

路径3（普通用户浏览器Key）:
  用户填的Key → 失败 → 本地兜底
```

### 2.3 LLM选择策略（按任务复杂度）

```
简单任务（聊天/查询状态）:
  模型: glm-4-flash（便宜，够用）
  温度: 0.5
  max_tokens: 1024

中等任务（生成/搜索/单模块调用）:
  模型: deepseek-chat（平衡）
  温度: 0.2
  max_tokens: 2048

复杂任务（多步编排/代码生成）:
  模型: deepseek-chat（强）
  温度: 0.1
  max_tokens: 4096
```

## 第三章：模块执行保护层

### 3.1 熔断器（Circuit Breaker）

```python
# 某个模块连续失败3次 → 熔断5分钟
# 熔断期间不调用该模块

_circuit_breakers = {}  # {module_name: {fail_count, last_fail, open_until}}

def _check_circuit(name):
    cb = _circuit_breakers.get(name)
    if cb and cb["open_until"] > time.time():
        return False  # 熔断中
    return True

def _record_failure(name):
    cb = _circuit_breakers.setdefault(name, {"fail_count":0, "open_until":0})
    cb["fail_count"] += 1
    if cb["fail_count"] >= 3:
        cb["open_until"] = time.time() + 300  # 熔断5分钟

def _record_success(name):
    _circuit_breakers.pop(name, None)  # 恢复
```

### 3.2 动作白名单

```python
# 某些危险操作不能由LLM自动触发
BLOCKED_ACTIONS = {"delete", "drop", "truncate", "format", "shutdown",
                   "restart", "remove", "purge", "clear_all", "reset_all"}

# LLM调模块时自动拦截
def _check_action(action):
    action_lower = action.lower()
    for blocked in BLOCKED_ACTIONS:
        if blocked in action_lower:
            return False, f"危险操作'{action}'已拦截"
    return True, None
```

### 3.3 限流器（已有）

```python
# api/infra.py rate_limiter — 每个IP每分钟30次请求
# 不需要额外实现
```

### 3.4 模块依赖解析

```python
# 有些模块需要先初始化
# 通过infra._execute_module_internal的lazy_load自动处理

# 复杂依赖：system_coordinator_v3已经有capability graph
# 但当前阶段不用，等LLM自己试错学习
```

## 第四章：记忆学习系统（5张表）

### 4.1 memory — 对话记忆（已有）

```sql
CREATE TABLE memory (
    id INTEGER PRIMARY KEY,
    input TEXT,           -- 用户输入
    output TEXT,          -- 系统回复
    success INTEGER,      -- 1成功/0失败
    module_used TEXT,     -- 用了哪些模块
    created REAL          -- 时间戳
);
```

### 4.2 module_scores — 模块评分（新增）

```sql
CREATE TABLE module_scores (
    module TEXT,           -- 模块名
    action TEXT,           -- 动作
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    avg_latency REAL DEFAULT 0,  -- 平均延迟(ms)
    last_used REAL,               -- 最后使用时间
    PRIMARY KEY (module, action)
);
```

### 4.3 patterns — 使用模式（新增）

```sql
CREATE TABLE patterns (
    task_type TEXT,        -- 任务类型（如"开发系统"）
    module_chain TEXT,     -- 模块链（如"form_builder→database_manager→ui_renderer"）
    success_count INTEGER DEFAULT 1,
    created REAL,
    PRIMARY KEY (task_type, module_chain)
);
```

### 4.4 fail_patterns — 失败模式（新增）

```sql
CREATE TABLE fail_patterns (
    module TEXT,
    action TEXT,
    error_message TEXT,
    count INTEGER DEFAULT 1,
    first_seen REAL,
    last_seen REAL,
    PRIMARY KEY (module, action, error_message)
);
```

### 4.5 execution_log — 执行日志（新增）

```sql
CREATE TABLE execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,       -- 请求ID
    input TEXT,            -- 用户输入
    rounds TEXT,           -- 每轮详情JSON
    total_latency REAL,    -- 总耗时
    success INTEGER,
    error TEXT,
    created REAL
);
```

## 第五章：5个工具定义

```
┌─────────────────────────────────────────────────────────────────────────┐
│  工具1: chat                                                            │
│  用途: 纯对话，不需要调模块时用                                         │
│  参数: 无                                                               │
│  温度: 0.5                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│  工具2: get_module_info                                                 │
│  用途: 查模块能力（按类别或按模块名）                                  │
│  参数: {category: "数据库"} 或 {module: "data_analysis"}               │
│  返回: {modules: [{name, desc, actions, score, success_rate}]}          │
│  失败: 自动返回最近似类别                                                │
├─────────────────────────────────────────────────────────────────────────┤
│  工具3: execute_module                                                  │
│  用途: 调用任意模块执行任务                                              │
│  参数: {module, action, params}                                         │
│  保护: 熔断器/白名单/超时/幂等                                          │
│  失败: 按类型修正或跳过                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  工具4: draw_image                                                      │
│  用途: AI画图                                                          │
│  参数: {prompt}                                                         │
│  失败: 不重试，直接告诉用户                                              │
├─────────────────────────────────────────────────────────────────────────┤
│  工具5: web_search                                                      │
│  用途: 搜索信息                                                        │
│  参数: {query}                                                          │
│  失败: 不重试，建议换方式                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

## 第六章：全场景状态机

### 6.1 正常流程

```
第1轮: LLM → execute_module(模块A) → 成功
第2轮: LLM → execute_module(模块B) → 成功  
第3轮: LLM → 总结完成
```

### 6.2 失败修正

```
第1轮: execute_module(A) → fail("表名重复")
第2轮: LLM换名 → execute_module(A, {name:"v2"}) → 成功
第3轮: execute_module(B) → 成功
```

### 6.3 卡住打断

```
检测到：连续2轮相同工具+参数 → _stuck_count=2
→ 打断循环
→ "卡住了，建议换个方式"
→ 记录到fail_patterns
```

### 6.4 LLM API失败

```
401 → "Key无效" → 不重试
429 → "请求频繁" → 等待3秒重试
500 → "服务暂时不可用" → 换Provider重试
超时 → "响应超时" → 本地兜底
```

### 6.5 模块执行异常

```
模块不存在 → "没用这个模块" → LLM换一个
参数错误 → "参数xxx不对" → LLM修正
执行异常 → 捕获返回错误 → LLM看情况处理
超时(>30s) → "执行超时" → 跳过
熔断中 → "模块正在恢复" → LLM换模块
白名单拦截 → "不能执行危险操作" → 跳
```

### 6.6 用户中断

```
用户发新消息 → 放弃当前 → 处理新的
用户刷新 → 当前会话丢失 → 长期记忆在
用户长时间不操作 → 不变（无超时）
```

### 6.7 并发多用户

```
每个请求独立 → context[] per request
记忆库按key_hash前缀隔离
_LAST_APP按key_hash存储
```

### 6.8 成本控制

```
每次LLM调用记录：tokens, cost, provider
单次上限：max_tokens=8192
3轮上限：total_tokens=8192
```

### 6.9 断电恢复

```
systemd自启 ✓
SQLite持久化 ✓（数据不丢）
正在执行的请求 → 丢失（无法恢复）
```

### 6.10 模块热发现

```
启动时扫描模块目录 → 建立模块索引
运行时新增模块 → 下次请求时重新扫描（可选）

简化方案：每次启动时扫描一次，运行时不变。
因为模块改动通常伴随重启。
```

## 第七章：兜底（无Key时）

| 你说 | 返回 |
|------|------|
| 做一个计算器 | ✅ `/app_calc.html` |
| 系统状态 | ✅ 457模块运行正常 |
| 游戏 | ✅ 狼吃娃/五子棋/老婆跳井 |
| 你会什么 | ✅ 能力列表 |
| 搜索/画图/其他 | ⚠️ "需要API Key" |

## 第八章：模块分类（LLM决策用）

```
📊 数据分析(38): data_analysis, chart_engine, excel_engine...
🤖 AI服务(30): code_generator, translation_service...
🔧 系统管理(45): system_monitor, docker_manager...
🔐 安全防护(15): permission_guard, audit_log...
🗄️ 数据库(20): database_manager, sql_generator...
🧩 Agent(25): agent_orchestrator, agent_planner...
📁 文件文档(18): file_manager, pdf_report...
🌐 网络(12): web_scraper, dns_manager...
📈 金融(8): finance_data, stock_api...
🎮 娱乐(20): 游戏/小工具...
🛠️ 其他工具(226): ...
```

## 第九章：改动范围

| 文件 | 改动 | 行数 |
|------|------|------|
| routes_smart_chat.py | 全部重写 | ~320行 |
| chat.html | 2行微调 | provider参数 |

## 第十章：不动清单

| 文件 | 原因 |
|------|------|
| api_server.py | 路由正常 |
| api/infra.py | 执行核心 |
| core/llm_gateway.py | LLM网关 |
| modules/全部 | 模块正常 |
| 其他所有文件 | 不动 |

## 第十一章：最终校验（25项）

### 核心（8项）
```
✅ Key自动识别（sk- → OpenAI/DeepSeek, 含小数点→智谱）
✅ 5个工具（chat/get_module_info/execute_module/draw_image/web_search）
✅ 3轮循环（每步看结果再决定下步）
✅ 温度控制（工具0.1 → 对话0.5）
✅ 中文优先（无中文强制重生成）
✅ 执行追踪（每轮记录耗时+结果）
✅ 无Key兜底（本地功能+提示）
✅ Provider回退（故障自动切换）
```

### 容错（7项）
```
✅ 卡住检测（重复工具/重复内容/连续失败）
✅ 熔断器（连续3次失败熔断5分钟）
✅ 超时控制（LLM120s/模块30s）
✅ 失败分类（临时重试/参数修正/不支持跳过）
✅ Token预算（3轮累计≤8192）
✅ 动作白名单（delete/drop等禁止自动执行）
✅ 模块依赖解析（lazy_load自动处理）
```

### 安全（3项）
```
✅ 敏感内容过滤（拒绝+不暴露细节）
✅ API Key脱敏（日志中不记录）
✅ 幂等性（10分钟去重）
```

### 学习（4项）
```
✅ 短期记忆（context[] 8轮）
✅ 长期记忆（SQLite memory表）
✅ 模块评分（success_rate + avg_latency）
✅ 模式识别（重复成功自动记录+推荐）
```

### 体验（3项）
```
✅ 结果优化（太短→追加链接，无中文→重生成）
✅ 熔断提示（"模块正在恢复，建议稍后重试"）
✅ 部分成功（告诉用户哪些成功/哪里失败）
```
