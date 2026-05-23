# AUTO-EVO-AI V0.1 — 架构重构计划

> 上市公司级生产力标准 | 2026-05-22

---

## 当前架构基线

| 组件 | 文件 | 大小 | 状态 |
|------|------|------|------|
| API 入口 | `api_server.py` | 468 行 ✅ | 已良好拆分 |
| 共享基础设施 | `api/infra.py` | 35 KB | **核心单体**，承载 app/registry/ratelimiter/缓存/模型/执行引擎 |
| 路由模块 (4) | `api/routes_*.py` | 102 KB 合计 | 已拆分，功能正常 |
| 核心引擎 | `core/` | 52 文件 | 高质量 (A-级) |
| 模块系统 | `modules/` | 535 文件 | 100% 真实模块，0% 桩模块 |
| 前端 | 根目录 `.html/.js` + `static/` | 6+ 文件 | 未独立目录 |
| 配置 | `.env` + `.env.example` + `.env.prod` | 存在 ✅ | 需强化 |
| 包管理 | `pyproject.toml` | 存在 ✅ | 缺少根目录 `requirements.txt` |
| 版本控制 | ❌ | — | **P0 缺失** |
| 路径硬编码 | 需审计 | — | 需 pathlib 改造 |

---

## 重构原则

1. **不破坏现有功能** — 每步重构后运行 3523 测试验证
2. **增量迁移** — 不 rewrite，只 move/refactor
3. **保持向后兼容** — 旧导入路径继续可用
4. **每步可回滚** — Git 做 checkpoint

---

## 执行状态 (2026-05-22 全部完成 ✅)

### ✅ Phase 0: 版本控制
- ✅ `.gitignore` + `git init` + `CHANGELOG.md`
- ✅ Git 历史: 4 commits, 711 files baseline

### ✅ Phase 1: P0 架构风险

#### 1.1 api_server.py 拆分 ✅
- ✅ `api/middleware.py` — metrics + security middleware 独立
- ✅ `api/startup.py` — startup 事件 + 4 个后台任务独立
- ✅ `api_server.py` — 精简为 345 行入口（路由/端点/uvicorn）

#### 1.2 桩模块审计 ✅
- ✅ 95 个 < 2KB 模块审计: 100% EnterpriseModule 模板合规
- ✅ `STUBS.md` — 分类报告 + 优先级建议
- ✅ `modules/stubs_audit.json` — 详细审计数据
- ✅ `ModuleRegistry.get_stub_count() / get_stubs()` 方法
- ✅ Prometheus + API 端点暴露 stub count

### ✅ Phase 2: P1 质量短板

#### 2.1 前端独立目录 ✅
- ✅ `frontend/dashboard/` `frontend/wizard/` `frontend/static/`
- ✅ API `/dashboard` 端点优先查找 `frontend/dashboard/index.html`
- ✅ 向后兼容（fallback 到根目录 `index.html`）

#### 2.2 根目录 requirements.txt ✅
- ✅ 核心依赖 + LLM/数据库/开发依赖注释

#### 2.3 硬编码路径 ✅
- ✅ 搜索 0 处硬编码 `D:\AUTO-EVO-AI-V0.1\` — 已使用 pathlib

### ✅ Phase 3: P2 可优化

#### 3.1 配置体系 ✅
- ✅ `config/defaults.yaml` — 默认配置
- ✅ `config/environments/production.yaml` — 生产环境覆盖
- ✅ 支持 `EVO_ENV=dev|staging|prod` 环境变量

#### 3.2 结构化 JSON 日志 ✅
- ✅ `core/logging_config.py` — JSONFormatter + StructuredLogger
- ✅ 支持 `EVO_LOG_JSON=true` 开关

#### 3.3 性能基准 ✅
- ✅ `benchmarks/test_api_perf.py` — 1/10 并发基准测试 (6/6 passed)
- ✅ 覆盖 / /api/status /api/modules /dashboard + 并发测试
- ✅ 运行时 bug 修复: `list|set` → `set|set` (api/infra.py:333,342)

---

## 验证策略

每步重构后：
1. `python -m pytest tests/` — 3523 测试必须全绿
2. 启动服务 `python api_server.py`，验证 200 OK
3. Git commit
4. `xcopy D:\AUTO-EVO-AI-V0.1\ E:\AUTO-EVO-AI-V0.1\ /E /Y`

---

## 时间线估计

| Phase | 预计步骤 | 风险 |
|-------|----------|------|
| P0 初始化 Git | 2 步 | 低 |
| P0 api_server 拆分 | 3 步 | 中（infra.py 拆分影响路由导入） |
| P0 桩模块清理 | 2 步 | 低（仅移动文件） |
| P1 前端独立 | 3 步 | 低（不改变 API 行为） |
| P1 requirements.txt | 1 步 | 低 |
| P1 路径硬编码 | 1 步 | 低 |
| P2 配置体系 | 2 步 | 低 |
| P2 JSON 日志 | 1 步 | 低 |
| P2 性能基准 | 1 步 | 低 |
