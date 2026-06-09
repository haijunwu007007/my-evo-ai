"""注册第5轮20个工具到agent_tools.py"""
import re

with open("api/agent_tools.py", "r", encoding="utf-8") as f:
    content = f.read()

new_tools = [
    ("odoo_manage", "agent_odoo", "odoo_manage"),
    ("erpclaw_manage", "agent_erpclaw", "erpclaw_manage"),
    ("coolify_deploy", "agent_coolify", "coolify_deploy"),
    ("rustdesk_connect", "agent_rustdesk", "rustdesk_connect"),
    ("docuseal_sign", "agent_docuseal", "docuseal_sign"),
    ("homeassistant_control", "agent_homeassistant", "homeassistant_control"),
    ("vaultwarden_manage", "agent_vaultwarden", "vaultwarden_manage"),
    ("nocodb_manage", "agent_nocodb", "nocodb_manage"),
    ("appsmith_build", "agent_appsmith", "appsmith_build"),
    ("airbyte_sync", "agent_airbyte", "airbyte_sync"),
    ("mlflow_track", "agent_mlflow", "mlflow_track"),
    ("langfuse_observe", "agent_langfuse", "langfuse_observe"),
    ("hoppscotch_test", "agent_hoppscotch", "hoppscotch_test"),
    ("grist_analyze", "agent_grist", "grist_analyze"),
    ("freshrss_read", "agent_freshrss", "freshrss_read"),
    ("listmonk_send", "agent_listmonk", "listmonk_send"),
    ("mermaid_chart", "agent_mermaid", "mermaid_chart"),
    ("nocobase_build", "agent_nocobase", "nocobase_build"),
    ("scriberr_transcribe", "agent_scriberr", "scriberr_transcribe"),
    ("keploy_test", "agent_keploy", "keploy_test"),
]

blocks = []
for fname, module, funcname in new_tools:
    block = f'''        if name == "{fname}":
            try:
                from api.{module} import {funcname}
                r = {funcname}(**args)
                return {{"ok": r.get("ok", False) if isinstance(r, dict) else False, "data": json.dumps(r, ensure_ascii=False)[:2000]}}
            except Exception as e:
                return {{"ok": False, "data": f"{fname}执行失败: {{e}}"}}'''
    blocks.append(block)

# Find the last return statement in exec_tool to insert before
# We insert before the final fallback return
pattern = r'(        return \{"ok": False, "data": "未知工具: " \+ name\})'
match = re.search(pattern, content)
if match:
    insert_code = "\n".join(blocks) + "\n"
    content = content[:match.start()] + insert_code + content[match.start():]
    with open("api/agent_tools.py", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ agent_tools.py 追加 {len(new_tools)} 个工具分支（在fallback return前插入）")
else:
    # Fallback: append at end of exec_tool function
    # Find the last closing of exec_tool
    last_return_idx = content.rfind('return {"ok": False, "data":')
    end_of_block = content.find("}", last_return_idx) + 1
    insert_code = "\n" + "\n".join(blocks)
    content = content[:end_of_block] + insert_code + content[end_of_block:]
    with open("api/agent_tools.py", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ agent_tools.py 追加 {len(new_tools)} 个工具分支（fallback位置）")
