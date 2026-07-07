# AUTO-EVO-AI V0.1 — 模块真实性分类

> 生成时间: 2026-05-23
> 分类方法: 基于第三方依赖、execute方法深度、业务语句数、文件大小综合评分

---

## 总体分布

| 分类 | 数量 | 占比 | 说明 |
|------|------|------|------|
| 🔴 Shallow（浅层模板） | **110** | 20.6% | 无第三方依赖，execute<10行，biz语句<30句 |
| 🟡 Semi-Real（半真实） | **304** | 56.8% | 有一定业务逻辑，但主要靠dispatch路由，无外部依赖 |
| 🟢 Real（真实） | **115** | 21.5% | 有第三方依赖，execute有实质内容 |
| 🟣 Heavy（重型核心） | **6** | 1.1% | >30KB且有复杂业务逻辑和外部依赖 |
| **总计** | **535** | **100%** | |

---

## 🔴 Shallow (110个) — 建议重构或移除

这些模块仅有最基本的骨架结构，无第三方依赖，execute方法体极小。它们是代码生成器产物。

```
advanced_resilience.py       api_gateway.py              api_rate_limiter.py
audit_trail.py               auto_optimizer.py           auto_recovery.py
auto_setup_autonomous.py     auto_update.py              autonomous_agent.py
autonomous_decision_engine.py biometric_auth.py          bot_handler.py
cache_manager.py             cloud_sync.py               component_lib.py
cors_config.py               crewai.py                   daemon_controller.py
data_analysis.py             data_catalog.py             data_encrypt.py
data_quality.py              database_manager.py         document_intelligence.py
elasticsearch_search.py      enterprise_notifier.py      event_bus_pro.py
evo_engine_v2.py             evo_plugin_market.py        excel_engine.py
external_executor.py         feishu_notifier.py          file_watcher.py
file_watcher_engine.py       finance_legal_agent.py      firewall_rules.py
forex_api.py                 form_engine.py              futures_api.py
game_simulation.py           geo_manager.py              graphql_gateway.py
grpc_proxy.py                header_injector.py          health_check.py
heatmap_generator.py         help_docs.py                hermes_solo.py
hot_key_detection.py         icon_manager.py             image_engine.py
image_generation.py          iot_edge.py                 json_store.py
jwt_token.py                 key_insights.py             lobehub_ui.py
longterm_memory.py           m49_push_notify.py          m56_scheduler_pro.py
mcp_client.py                meeting_transcribe.py       metric_collector.py
metrics.py                   ml_intern.py                model_router.py
mongodb_nosql.py             multi_agent_crew.py         oauth_provider.py
oauth_server.py              opa_policy_engine.py        open_lovable.py
openhands_agent.py           openinterpreter.py          orchestrator_core.py
pipelines.py                 postgres_db.py              praisonai_agent.py
priority_queue.py            pub_sub.py                  query_cache_layer.py
rate_limit_redis.py          read_write_split.py         realtime_collaboration.py
rebalance_protocol.py        replication_monitor.py      rpa_fault_tolerance.py
ruoyi_ai.py                  scheduler_pro.py            schema_evolution.py
search.py                    session_store.py            skill_marketplace.py
speech_to_text.py            sso_auth.py                 template_market.py
three_d_ar.py                unified_api_adapter.py      visual_rpa_core.py
voice.py                     watchdog.py                 web_remote.py
webtoapp.py                  whisper_asr.py              workflow_orchestrator.py
```

---

## 🟣 Heavy (6个) — 核心资产

| 模块 | 大小 | 行数 | 业务语句 | 外部依赖 |
|------|------|------|----------|----------|
| system_coordinator_v3.py | 162.2KB | 3982 | 667 | psutil |
| system_coordinator.py | 66.7KB | 1654 | 312 | psutil |
| m53_finance_data.py | 51.1KB | 1282 | 266 | pandas, psutil |
| data_pipeline.py | 42.1KB | 1013 | 313 | pandas |
| system_command.py | 26.0KB | 677 | 115 | psutil |
| m54_browser_auto.py | 18.8KB | 439 | 170 | requests, playwright |

---

## 建议行动

1. **P0 — 110个Shallow模块**：每模块标注"TEMPLATE"注释，删除或合并到相关真实模块
2. **P1 — 304个Semi-Real模块**：逐模块确认是否需要保留，无实际使用场景的归档
3. **P2 — 代码生成器**：`tools/batch_upgrade_real.py` 和 `upgrade_modules_engine.py` 评估是否继续使用
