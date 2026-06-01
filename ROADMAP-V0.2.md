# AUTO-EVO-AI V0.2 路线图

基线评估（V0.1，2026-06-01）：**85/100**

---

## Phase 1 — 前端焕新（预计 4-6h）

### 1.1 Naive UI 迁移
- 替换 Element Plus（首屏 1MB → 预计 400KB）
- 16 个 .vue 文件标签替换 + API 适配
- 表格系统重写（`el-table-column` 模板 → `n-data-table` columns prop）
- 对话框/表单/通知 API 适配
- 主题系统接入（Naive UI 的 JS 主题变量）

### 1.2 组件库建设
_现有组件：_ StatCard / PagePanel / LoadingBox（V0.1 已创建）
- 补充：DataTable / FormModal / ConfirmDialog / NavSidebar
- 组件 Storybook 文档

### 1.3 PWA 增强
- Service Worker 离线缓存
- 移动端 App Shell

---

## Phase 2 — 数据库升级（预计 4-6h）

### 2.1 PostgreSQL 适配
_桥梁已建：_ `core/db_provider.py`（V0.1 已创建）
- 定义完整的 SQLAlchemy ORM 模型层
- 统一数据访问接口（Repository 模式）
- `docker-compose.db.yml` 一键启动 PG

### 2.2 数据库迁移
- Alembic 迁移脚本管理
- SQLite → PostgreSQL 数据迁移工具
- 零停机迁移方案

---

## Phase 3 — Plugin 架构（预计 6-10h）

### 3.1 Plugin 系统
_基类已建：_ `plugin_base.py` + `plugin_registry.py`（V0.1 已创建）
- 定义 6 核心 Hook 点（start/stop/config/webhook/menu/widget）
- Plugin 发现机制（文件扫描 + 声明加载）
- 依赖注入 + 版本兼容

### 3.2 模块迁移
- 首批迁移 10 个核心模块（LLM/通知/调度/安全）
- 提供 EnterpriseModule → PluginBase 迁移指南
- 旧模块向后兼容层

---

## Phase 4 — 测试与质量（预计 3-5h）

### 4.1 测试覆盖 24% → 50%+
- 核心引擎单测补齐（data_layer/decision/intelligent_coordinator）
- API 路由参数化测试
- E2E 集成测试（Playwright 浏览器自动化）

### 4.2 前端测试
- Vitest 组件测试
- Playwright E2E（页面加载/导航/CRUD 操作）

---

## Phase 5 — 运维增强（预计 2-3h）

### 5.1 监控告警
- Prometheus 告警规则（alerts.yml 完善）
- Grafana Dashboard 模板
- 自监控（进程/内存/磁盘）

### 5.2 CI/CD 增强
- 自动部署到 staging/production
- PR Preview 环境
- 依赖漏洞扫描（Dependabot）

---

## 优先级与依赖关系

```
Phase 1 (前端) ─────────┐
                       ├── 可并行
Phase 2 (数据库) ───────┤
                       │
Phase 3 (Plugin) ──────┘ (依赖 Phase 1+2 做完，是最大单项)
                       │
Phase 4 (测试) ────────┤ (可在任意阶段并行推进)
                       │
Phase 5 (运维) ────────┘ (依赖 Phase 2 的数据库稳定)
```

**建议执行顺序：** Phase 1 → Phase 2 → Phase 3（最大工程放最后），Phase 4 和 5 穿插。

## 预估总工时：**19-28 小时**
