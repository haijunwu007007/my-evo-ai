"""Reclassify uncategorized modules by filename prefix — tight & fast"""
from pathlib import Path
import re

modules_dir = Path("modules")
counter = {"total": 0, "fixed": 0, "skipped": 0}

# (prefix_regex, category) ordered by priority
RULES = [
    ("^(agent|agency)", "agent"), ("^api", "api"), ("^auth|oauth|jwt|sso|token|biometric", "auth"),
    ("^backup", "backup"), ("^cache|redis|kv", "cache"), ("^cdn", "cdn"),
    ("^cicd|ci_|jenkins|git_|argocd", "devops"), ("^code_|bytecode|component", "developer"),
    ("^config|setting", "config"), ("^cron|scheduler|job_", "scheduler"),
    ("^data_(pipeline|sync|scrap|catalog|quality|analysis|archival|lineage)", "data"),
    ("^db_|database|clickhouse|mongodb|postgres|sql_|neo4j|milvus|pgvector|weaviate|pinecone|qdrant|pgvector|pitr", "database"),
    ("^dify|flowise|n8n|langflow", "nocode"), ("^docker|k8s|kubernetes|deploy", "devops"),
    ("^doc|pdf|excel|form_|export_", "documents"),
    ("^encrypt|crypto|secret|ssl", "security"),
    ("^event_|pub_sub|fanout", "messaging"),
    ("^feishu|push|notif|email_|telegram|notification", "messaging"),
    ("^file_|storage|object_storage|backup_", "storage"),
    ("^finance|stock|forex|fund_|futures|crypto_api|macro", "finance"),
    ("^firewall|waf|ddos|bot_", "security"),
    ("^flow_|workflow_|trigger", "workflow"),
    ("^geo_|i18n|translation", "international"),
    ("^github|trend", "github"),
    ("^health_|heartbeat|ping", "monitor"),
    ("^http_|rest_|grpc|graphql|websocket|sse_|proxy", "network"),
    ("^image_|video_|ocr_|audio_|voice_|speech|tts|whisper|pixelle|hyperframe", "media"),
    ("^iot_|edge_", "iot"),
    ("^llm_|ai_|model_|embedding|rag_|ml_|rerank|stable_diffusion|openai|claude|gemini|local", "llm"),
    ("^log_|audit_|metric_|monitor|perf_|alert_|error_|incident|sla_", "monitor"),
    ("^longterm|memory_|memgpt|mem0|supermemory|soul_|second_brain|experience", "memory"),
    ("^mcp_|plugin_", "plugin"),
    ("^message_|queue_|broker|kafka", "messaging"),
    ("^migration|schema_", "database"),
    ("^multica|crewai|langgraph|agency|multi_agent|praisonai|openhands", "agent"),
    ("^network_|dns_|transfer", "network"),
    ("^opa_|cerbos|permission|rbac|access_control|policy", "security"),
    ("^pipeline|batch_|stream_", "data"),
    ("^process_|watchdog|daemon|system_coordinator|orchestrator|autonomous|task_", "system"),
    ("^rate_limiter|circuit_breaker|resilience", "resilience"),
    ("^recommendation|search_|index_|fts_", "search"),
    ("^report_|chart_|visual|heatmap|mindmap", "reports"),
    ("^rpa_|vision_rpa|visual_rpa|window_|win_control|browser_auto|web_remote|webtoapp", "rpa"),
    ("^rule_|state_machine|decision|saga_", "workflow"),
    ("^secret_|vault_", "security"),
    ("^self_|evolving|evolution", "evolution"),
    ("^service_|discovery|mesh", "network"),
    ("^session_|user_|profile_|identity", "auth"),
    ("^template_|market|skill|automation_hub", "marketplace"),
    ("^tunnel|vpn|remote_", "network"),
    ("^ui_|dashboard|renderer|hermes_|lobehub|config_ui", "ui"),
    ("^webhook|hook_", "webhook"),
    ("^waf|threat|compliance|gdpr", "security"),
    ("^stock|fund", "finance"),
    ("^search|index", "search"),
    ("^pipeline|etl", "data"),
]

for pyfile in sorted(modules_dir.glob("*.py")):
    if pyfile.name.startswith("_") or pyfile.name == "__init__.py": continue
    counter["total"] += 1
    # Read existing content
    content = pyfile.read_text(encoding="utf-8")
    # Check if already has a non-uncategorized group
    m = re.search(r'"group"\s*:\s*"([^"]+)"', content)
    if m and m.group(1) != "uncategorized":
        counter["skipped"] += 1
        continue
    # Match rules
    matched = None
    for pat, cat in RULES:
        if re.match(pat, pyfile.stem):
            matched = cat
            break
    if not matched:
        counter["skipped"] += 1
        continue
    # Replace group
    if '"group": "uncategorized"' in content:
        content = content.replace('"group": "uncategorized"', f'"group": "{matched}"')
        pyfile.write_text(content, encoding="utf-8")
        counter["fixed"] += 1
        logger.info(f"  {pyfile.stem}: uncategorized → {matched}"))

logger.info(f"\nTotal={counter['total']} Fixed={counter['fixed']} AlreadyCategorized={counter['skipped']}"))
