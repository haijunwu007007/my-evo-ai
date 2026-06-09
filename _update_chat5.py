"""更新chat.html：第5轮20个快捷按钮 + _TOOL_HINTS + _TOOL_KEYWORDS"""

with open("frontend/chat.html", "r", encoding="utf-8") as f:
    content = f.read()

# ===== 1. Add quick-action buttons =====
new_buttons = [
    ("odoo_manage", "🏢 ERP"),
    ("erpclaw_manage", "🏭 AI-ERP"),
    ("coolify_deploy", "🚀 PaaS部署"),
    ("rustdesk_connect", "🖥️ 远程桌面"),
    ("docuseal_sign", "✍️ 电子签名"),
    ("homeassistant_control", "🏠 智能家居"),
    ("vaultwarden_manage", "🔐 密码管理"),
    ("nocodb_manage", "📊 数据表格"),
    ("appsmith_build", "🛠️ 低代码"),
    ("airbyte_sync", "🔄 ETL管道"),
    ("mlflow_track", "📈 MLOps"),
    ("langfuse_observe", "👁️ LLM观测"),
    ("hoppscotch_test", "🧪 API测试"),
    ("grist_analyze", "📋 电子表格"),
    ("freshrss_read", "📰 RSS聚合"),
    ("listmonk_send", "📧 邮件"),
    ("mermaid_chart", "🗺️ 流程图"),
    ("nocobase_build", "🏗️ 低代码平台"),
    ("scriberr_transcribe", "🎤 音频转录"),
    ("keploy_test", "🧪 AI测试"),
]

# Find the last quick-action button (projectsend_files)
last_qa = "projectsend_files"
idx = content.find(last_qa)
if idx < 0:
    # Try alternative
    idx = content.find("文件共享")
    if idx < 0:
        print("ERROR: Cannot find insertion point for quick-action buttons")
        exit(1)

# Find the end of this span tag
span_end = content.find("</span>", idx) + len("</span>")

# Generate new button HTML
btn_html = ""
for tool_name, label in new_buttons:
    btn_html += f'\n      <span class="qa" onclick="quickTool(\'{tool_name}\')">{label}</span>'

# Insert after the last button
content = content[:span_end] + btn_html + content[span_end:]
print(f"✅ 添加 {len(new_buttons)} 个快捷按钮")

# ===== 2. Update _TOOL_HINTS =====
new_hints = {
    "odoo_manage": "帮我管理ERP（会计/库存/采购）：",
    "erpclaw_manage": "帮我用AI-ERP管理业务：",
    "coolify_deploy": "帮我在PaaS上部署应用：",
    "rustdesk_connect": "帮我远程连接电脑：",
    "docuseal_sign": "帮我发送电子签名：",
    "homeassistant_control": "帮我控制智能家居设备：",
    "vaultwarden_manage": "帮我管理密码/凭证：",
    "nocodb_manage": "帮我管理数据表格：",
    "appsmith_build": "帮我用低代码构建管理工具：",
    "airbyte_sync": "帮我同步数据管道：",
    "mlflow_track": "帮我追踪AI模型训练：",
    "langfuse_observe": "帮我监控LLM应用：",
    "hoppscotch_test": "帮我测试API：",
    "grist_analyze": "帮我分析电子表格数据：",
    "freshrss_read": "帮我读取RSS资讯：",
    "listmonk_send": "帮我发送邮件/Newsletter：",
    "mermaid_chart": "帮我生成流程图/架构图：",
    "nocobase_build": "帮我用低代码构建业务应用：",
    "scriberr_transcribe": "帮我转录音频/会议：",
    "keploy_test": "帮我自动生成API测试：",
}

# Find the _TOOL_HINTS closing
hints_start = content.find("_TOOL_HINTS = {")
if hints_start > 0:
    # Find the closing };
    search_from = hints_start
    # Find last hint entry (look for projectsend_files hint or the last known one)
    last_hint = "projectsend_files"
    last_hint_idx = content.find(last_hint, hints_start)
    if last_hint_idx > 0:
        # Find the end of this line
        line_end = content.find("\n", last_hint_idx)
        # Insert new hints after this line
        hints_insert = ""
        for k, v in new_hints.items():
            hints_insert += f"\n  {k}: \"{v}\","
        content = content[:line_end] + hints_insert + content[line_end:]
        print(f"✅ 添加 {len(new_hints)} 个 _TOOL_HINTS")

# ===== 3. Update _TOOL_KEYWORDS =====
new_keywords = [
    "odoo_manage", "erpclaw_manage", "coolify_deploy", "rustdesk_connect",
    "docuseal_sign", "homeassistant_control", "vaultwarden_manage", "nocodb_manage",
    "appsmith_build", "airbyte_sync", "mlflow_track", "langfuse_observe",
    "hoppscotch_test", "grist_analyze", "freshrss_read", "listmonk_send",
    "mermaid_chart", "nocobase_build", "scriberr_transcribe", "keploy_test",
]

kw_start = content.find("_TOOL_KEYWORDS = [")
if kw_start > 0:
    # Find the closing ]
    kw_close = content.find("]", kw_start)
    if kw_close > 0:
        # Insert before the closing bracket
        kw_insert = ""
        for kw in new_keywords:
            kw_insert += f'"{kw}", '
        content = content[:kw_close] + kw_insert + content[kw_close:]
        print(f"✅ 添加 {len(new_keywords)} 个 _TOOL_KEYWORDS")

with open("frontend/chat.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ chat.html 更新完成")
