# AUTO-EVO-AI V0.1 — API 文档

## 系统概览
- **版本**: V0.1
- **模块总数**: 416
- **核心引擎**: SchedulerEngine / EventEngine / PipelineEngine / TaskQueueEngine

## 架构
```
api_server.py → api/ (路由) → core/ (引擎) → modules/ (功能模块)
                                ↕
                      core/module_delegate.py (单例委托)
```

## API 端点

### 系统
- `GET /` — 系统状态
- `GET /api/status` — 详细状态
- `GET /metrics` — Prometheus 指标

### 模块
- `GET /api/modules` — 模块列表
- `GET /api/modules/{name}` — 模块详情
- `POST /api/modules/{name}/execute` — 执行模块

### 认证
- `POST /api/auth/login` — 登录
- `GET /api/auth/config` — 认证配置
- `GET /api/auth/verify` — 验证令牌

## 模块目录

| 模块名 | 外部依赖 | 描述 |
|--------|----------|------|
| system_coordinator_v3 | 162KB | — |
| agent_planner | 117KB | — |
| agent_resource_control | 70KB | — |
| system_coordinator | 66KB | — |
| m53_finance_data | 51KB | — |
| ragflow | 48KB | — |
| second_brain | 47KB | — |
| cli_interface | 47KB | — |
| agent_hephaestus | 47KB | — |
| key_insights | 44KB | — |
| agent_cronus | 43KB | — |
| flowise | 42KB | — |
| data_pipeline | 42KB | — |
| security_scanner | 41KB | — |
| rpa_controller | 41KB | — |
| cloud_connector | 41KB | — |
| agent_eros | 41KB | — |
| agent_boreas | 41KB | — |
| code_review | 40KB | — |
| agent_orchestrator | 40KB | — |
| m51_web_remote | 39KB | — |
| form_builder | 39KB | — |
| access_control | 39KB | — |
| http_client | 38KB | — |
| flow_engine | 37KB | — |
| docker_manager | 37KB | — |
| bucket_policy | 37KB | — |
| template_registry | 36KB | — |
| smart_scheduler | 36KB | — |
| code_generator | 36KB | — |
| bloom_filter | 36KB | — |
| user_profile | 35KB | — |
| ui_renderer | 35KB | — |
| project_mgmt | 35KB | — |
| githubtrending | 35KB | — |
| supermemory | 34KB | — |
| soul_identity | 34KB | — |
| permission_guard | 34KB | — |
| config_manager | 34KB | — |
| cicd_pipeline | 34KB | — |
| backup_scheduler | 34KB | — |
| file_system | 33KB | — |
| database_client | 33KB | — |
| resource_server | 32KB | — |
| registry_center | 32KB | — |
| qdrant_vector | 32KB | — |
| mem0_memory | 32KB | — |
| litellm_gateway | 32KB | — |
| kafka_producer | 32KB | — |
| feature_flag | 32KB | — |
