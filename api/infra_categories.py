"""模块分类 — 从 infra.py 拆分"""
from __future__ import annotations

_MODULE_CATEGORY_RULES = [
    (["agent_", "agent-"], "agent"),
    (["api_", "api-"], "api"),
    (["cache_", "cache-"], "cache"),
    (["security_", "sec_", "waf_", "firewall_"], "security"),
    (["log_", "audit_"], "logging"),
    (["db_", "database_", "sql_", "redis_", "mongo_"], "database"),
    (["auth_", "oauth_", "jwt_", "token_"], "auth"),
    (["metric_", "monitor_", "perf_", "trace_"], "monitor"),
    (["notify_", "push_", "email_", "sms_", "message_"], "notification"),
    (["backup_", "recovery_", "restore_", "snapshot_"], "backup"),
    (["config_", "setting_", "env_", "feature_"], "config"),
    (["task_", "job_", "scheduler_", "cron_", "workflow_"], "task"),
    (["queue_", "mq_", "broker_", "kafka_", "rabbit_"], "messaging"),
    (["search_", "index_", "rag_", "embedding_"], "search"),
    (["encrypt_", "crypto_", "ssl_", "cert_", "key_", "secret_"], "crypto"),
    (["network_", "dns_", "proxy_", "cdn_", "tunnel_"], "network"),
    (["file_", "storage_", "disk_", "oss_", "s3_"], "storage"),
    (["data_", "etl_", "pipeline_"], "data"),
    (["ml_", "ai_", "model_", "train_", "nlp_"], "ai"),
    (["test_", "lint_", "quality_", "bench_"], "testing"),
]
_CATEGORY_OTHER = "system"


def classify_module(name: str) -> str:
    nl = name.lower()
    for prefixes, cat in _MODULE_CATEGORY_RULES:
        for p in prefixes:
            if nl.startswith(p):
                return cat
    return _CATEGORY_OTHER
