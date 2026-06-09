"""注册第5轮20个工具到agent_core.py"""
import re

with open("api/agent_core.py", "r", encoding="utf-8") as f:
    content = f.read()

# Count existing tools
count = content.count('"type":"function","function"')
print(f"Current tool count: {count}")

# New tool schemas
new_schemas = [
    ('odoo_manage', '🏢 Odoo ERP：管理会计/库存/采购/销售/制造/HR模块', 'module:操作模块,action:操作类型'),
    ('erpclaw_manage', '🏭 ERPClaw AI-ERP：14行业46模块AI原生ERP', 'module:模块,industry:行业'),
    ('coolify_deploy', '🚀 Coolify PaaS：自托管部署应用和数据库', 'app_name:应用名,action:deploy/status'),
    ('rustdesk_connect', '🖥️ RustDesk远程桌面：远程控制电脑', 'target:目标机器,action:connect/status'),
    ('docuseal_sign', '✍️ DocuSeal电子签名：在线文档签署', 'document:文档,signers:签署人'),
    ('homeassistant_control', '🏠 智能家居：控制IoT设备/灯光/传感器/自动化场景', 'device:设备,action:操作,state:状态'),
    ('vaultwarden_manage', '🔐 密码管理：安全存储和检索密码凭证', 'action:list/create/get,site:网站'),
    ('nocodb_manage', '📊 NocoDB数据表：数据库→电子表格可视化管理', 'table:表名,action:list/create/query'),
    ('appsmith_build', '🛠️ Appsmith低代码：拖拽式构建内部管理工具', 'app_name:应用名,action:create/edit'),
    ('airbyte_sync', '🔄 Airbyte ETL：数据采集/清洗/同步管道', 'source:数据源,destination:目标,action:sync/status'),
    ('mlflow_track', '📈 MLflow MLOps：AI模型训练/部署/追踪', 'experiment:实验名,action:log/list/compare'),
    ('langfuse_observe', '👁️ Langfuse LLM可观测：Prompt管理/评估/追踪', 'action:trace/score/prompt,project:项目'),
    ('hoppscotch_test', '🧪 Hoppscotch API测试：API调试/Mock/回归测试', 'endpoint:API地址,method:HTTP方法,body:请求体'),
    ('grist_analyze', '📋 Grist电子表格：关系型数据分析/Python公式', 'table:表名,action:analyze/query/formula'),
    ('freshrss_read', '📰 FreshRSS聚合：RSS订阅/信息采集/资讯监控', 'action:read/search/subscribe,feed:RSS源'),
    ('listmonk_send', '📧 Listmonk邮件：邮件列表/Newsletter/营销邮件', 'action:send/list/create,list_id:列表ID'),
    ('mermaid_chart', '🗺️ Mermaid图表：文本→流程图/架构图/时序图', 'chart_type:flow/sequence/class/er,description:描述'),
    ('nocobase_build', '🏗️ NocoBase低代码：AI+低代码快速构建业务应用', 'app_name:应用名,action:create/schema/query'),
    ('scriberr_transcribe', '🎤 音频转录：AI将音频/会议转录为文字', 'audio_path:音频路径,action:transcribe/list'),
    ('keploy_test', '🧪 Keploy AI测试：自动生成API回归测试', 'action:record/test/report,endpoint:API地址'),
]

schema_lines = []
for name, desc, params_str in new_schemas:
    # Parse params
    props = {}
    required = []
    for p in params_str.split(","):
        p = p.strip()
        if ":" in p:
            pname, ptype = p.split(":", 1)
            pname = pname.strip()
            ptype = ptype.strip()
            props[pname] = {"type": "string", "description": ptype}
            if not pname.startswith("action") and pname not in ["state", "body", "description"]:
                required.append(pname)
    
    props_obj = {"type": "object", "properties": props}
    if required:
        props_obj["required"] = required
    
    import json
    schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": props_obj
        }
    }
    schema_lines.append(f'            {json.dumps(schema, ensure_ascii=False)},')

# Find the last tool entry in bt array and insert after it
# Look for the pattern that ends the tool list: a closing ]
# We need to find the right position
lines = content.split('\n')
insert_idx = -1
for i, line in enumerate(lines):
    if '"type":"function","function"' in line and 'keploy_test' in line:
        # Already registered
        print(f"WARNING: keploy_test already in agent_core.py at line {i+1}")
        break
    # Find the end of the bt array - look for the line that closes it
    # The bt array has tools and then closes with ]
    if insert_idx == -1 and '"type":"function","function"' in line:
        insert_idx = i  # We'll insert after the last tool

# Better approach: find the last tool line in bt[] and insert after it
# The bt array tools are between the opening [ and the first closing ]
# Find where tools end - after the last function definition line in bt
last_func_line = 0
for i, line in enumerate(lines):
    if '"type":"function","function"' in line:
        last_func_line = i

# The closing bracket of bt[] should be shortly after
# Let's insert after the last tool line
if last_func_line > 0:
    # Insert the new schemas after the last tool definition
    new_content_lines = lines[:last_func_line+1]
    new_content_lines.append("            # ===== 第5轮新增20个集成工具 =====")
    new_content_lines.extend(schema_lines)
    new_content_lines.extend(lines[last_func_line+1:])
    
    content = '\n'.join(new_content_lines)
    with open("api/agent_core.py", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ agent_core.py 追加 {len(new_schemas)} 个工具schema")
else:
    print("❌ 未找到插入位置")
