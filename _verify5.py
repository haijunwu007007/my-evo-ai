"""全量验证脚本"""
import importlib

all_modules = [
    'agent_browser_use','agent_gpt_researcher','agent_openhands','agent_letta','agent_composio',
    'agent_toolbench','agent_self_evolving','agent_moltron','agent_accomplish',
    'agent_markitdown','agent_scrapegraphai','agent_interpreter','agent_s2c',
    'agent_pra','agent_qodo','agent_aider','agent_openclaw','agent_tts',
    'agent_chatdev','agent_openmanus','agent_autogpt','agent_agenteval',
    'agent_swe','agent_gptpilot','agent_chat2db','agent_bolt','agent_agentk8s',
    'agent_openmontage','agent_lida','agent_paddleocr','agent_zen','agent_shannon',
    'agent_openant','agent_legal','agent_twenty','agent_frappehr','agent_invoice',
    'agent_chatwoot','agent_postiz','agent_mautic','agent_superset','agent_dataease',
    'agent_heyform','agent_docetl','agent_accord','agent_claude',
    'agent_plane','agent_openproject','agent_cal','agent_novu','agent_keycloak',
    'agent_meilisearch','agent_minio','agent_opentofu','agent_ansible','agent_strapi',
    'agent_directus','agent_uptime','agent_oneuptime','agent_signoz','agent_wazuh',
    'agent_nats','agent_rabbitmq','agent_gitea','agent_wikijs','agent_bookstack',
    'agent_projectsend',
    'agent_odoo','agent_erpclaw','agent_coolify','agent_rustdesk','agent_docuseal',
    'agent_homeassistant','agent_vaultwarden','agent_nocodb','agent_appsmith','agent_airbyte',
    'agent_mlflow','agent_langfuse','agent_hoppscotch','agent_grist','agent_freshrss',
    'agent_listmonk','agent_mermaid','agent_nocobase','agent_scriberr','agent_keploy',
]

ok = fail = 0
failed = []
for m in all_modules:
    try:
        importlib.import_module(f"api.{m}")
        ok += 1
    except Exception as e:
        fail += 1
        failed.append(f"{m}: {e}")

print(f"全量导入验证: {ok}/{ok+fail} PASS")
if failed:
    for f in failed:
        print(f"  FAIL: {f}")

with open("api/agent_tools.py", "r", encoding="utf-8") as f:
    tc = f.read()
tool_count = tc.count("if name ==")
print(f"agent_tools.py 工具分支数: {tool_count}")

with open("api/agent_core.py", "r", encoding="utf-8") as f:
    cc = f.read()
marker = '"type":"function","function"'
schema_count = cc.count(marker)
print(f"agent_core.py 工具schema数: {schema_count}")

# Syntax check
import py_compile
for fn in ["api/agent_tools.py", "api/agent_core.py"]:
    try:
        py_compile.compile(fn, doraise=True)
        print(f"✅ {fn} 语法通过")
    except py_compile.PyCompileError as e:
        print(f"❌ {fn} 语法错误: {e}")
