# Changelog

## 2026-05-22 — V0.1 架构重构

### 新增
- `.gitignore` — 项目版本控制基础
- `ARCHITECTURE.md` — 架构重构计划文档

### 变更
- `api_server.py` → 468行精简入口（路由已拆分到 `api/routes_*.py`）
- `api/infra.py` → 包含共享基础设施、注册表、限流器、执行引擎

### 修复
- 全系统 ~3200 个测试全部通过（test_load_all + test_unit_core + API + E2E）
- `routes_modules.py` 参数名错误 `params` → `params_dict`
- `recommendation_system.py` 拼写错误 `tmod.time()` 修复
- 8 个 UnitCore 模块修复（FeishuNotifier/DataQuality/SqlGenerator/SsoAuth/OAuth/HealthCheck/SessionStore/StaticCache）
- `api/infra.py` 运行时错误 `list|set` → `set|set`
- `core/llm_gateway.py` config.yaml list 格式兼容修复

## 2026-05-22 晚上 — 桩模块清理 + CI

### 新增
- `.github/workflows/ci.yml` — GitHub Actions CI，全自动跑 3200+ 测试

### 变更
- 8 个桩模块升级为真实桥接（autonomous_agent / grafana_monitor 等）
- 12 个桩模块升级为实用模块（resilience / bot_handler 等）
- 24 个纯空壳模块删除（blockchain_web3 / three_d_ar 等）
- `modules/` 降至 535 个模块（已无空壳），所有留存模块均有真实 dispatch 逻辑

### 架构
- api_server: 468→345 行精简
- middleware: 新文件
- startup: 新文件
- frontend/: 独立目录
- config/: 分层配置系统
- benchmarks/: 性能基准框架
- core/logging_config.py: 结构化 JSON 日志
