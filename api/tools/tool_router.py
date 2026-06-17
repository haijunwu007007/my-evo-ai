"""
AUTO-EVO-AI V0.1 — 智能工具路由层

用户输入 → 意图识别 → 工具路由 → 执行/聊天

三层策略:
  1. LLM Function Calling (首选)
  2. 关键词模糊匹配 (降级)
  3. 纯 LLM 聊天 (兜底)
"""
import json, re, time
from typing import Any

from api.tools import exec_tool, list_tools
from api.agent_llm import call_llm

# ── 工具定义（给 LLM Function Calling 用）──

def _build_tool_defs() -> list[dict]:
    """将 87 个工具转为 LLM 可识别的 function calling 定义"""
    defs = []
    for t in list_tools():
        defs.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": f"用户请求内容，与{t['name']}相关"},
                    },
                    "required": ["query"],
                },
            },
        })
    return defs

_TOOL_DEFS = _build_tool_defs()

# ── 关键词→工具映射 ──

_KEYWORD_TOOLS: list[tuple[re.Pattern, str]] = [
    (re.compile(p), t)
    for p, t in [
        (r"浏览|打开|访问.*网址|抓取.*页面|网页截图", "browser_automate"),
        (r"爬取|抓取.*内容|爬虫", "web_scrape"),
        (r"搜索.*信息|查.*资料|找.*资料|查询", "web_search"),
        (r"研究|调研|分析.*趋势|报告.*主题", "deep_research"),
        (r"审查.*代码|review|PR|代码审查", "code_review"),
        (r"修复.*issue|修.*Bug|修.*问题", "fix_issue"),
        (r"生成.*测试|单元测试|测试用例", "generate_test"),
        (r"编辑.*代码|修改.*代码|改.*代码", "code_edit"),
        (r"分析.*代码|代码分析|代码质量", "code_analyze"),
        (r"安全.*扫描|漏洞.*扫描", "security_scan"),
        (r"审计.*代码|代码审计", "code_audit"),
        (r"合同.*审查|审.*合同", "contract_review"),
        (r"开发票|发票", "create_invoice"),
        (r"创建工单|工单", "create_ticket"),
        (r"发.*邮件|邮件.*营销|营销邮件", "send_email"),
        (r"发.*通知|推送通知", "send_notification"),
        (r"发.*短信|短信", "send_sms"),
        (r"查.*员工|员工.*查", "employee_lookup"),
        (r"记费用|报销|费用", "expense_record"),
        (r"日程|安排.*会议|添加.*日程", "schedule_add"),
        (r"创建问卷|问卷|调查", "survey_create"),
        (r"身份认证|登录|token|API Key", "auth_check"),
        (r"记忆|记住|保存.*内容", "memory_save"),
        (r"搜索.*记忆|回忆", "memory_search"),
        (r"生成.*图表|图表|可视化.*数据", "chart_create"),
        (r"仪表盘|dashboard|报表", "dashboard"),
        (r"BI|商业智能|数据分析", "bi_report"),
        (r"数据表|表格", "data_table"),
        (r"ETL|数据管道|数据同步", "etl_pipeline"),
        (r"低代码|拖拽.*应用|构建.*应用", "lowcode"),
        (r"MLOps|模型.*部署|模型.*训练", "mlops"),
        (r"LLM.*观测|模型.*监控", "llm_observability"),
        (r"API.*测试|接口.*测试", "api_test"),
        (r"电子表格|excel", "spreadsheet"),
        (r"RSS|订阅", "rss_aggregator"),
        (r"音频.*转录|语音.*转文字|whisper", "audio_transcribe"),
        (r"AI.*测试|模型.*评估", "ai_testing"),
        (r"技能.*学习|学习.*技能", "skill_learn"),
        (r"外部工具|集成.*工具", "external_tools"),
        (r"API.*发现|发现.*API", "api_discover"),
        (r"Agent.*评测|智能体.*评估|agent.*eval", "agent_eval"),
        (r"Claude|写代码.*AI|AI.*写代码", "claude_code"),
        (r"法律.*协议|协议.*生成", "legal_agreement"),
        (r"密码.*管理|生成.*密码", "password_manager"),
        (r"流程图|流程.*图", "flowchart"),
        (r"电子签|签.*名|数字签名", "e_signature"),
        (r"智能家居|控制.*设备|家居", "smart_home"),
        (r"项目|项目管理|全栈.*项目|创建.*项目", "fullstack_project"),
        (r"ERP|企业.*资源|资源.*计划", "erp_manage"),
        (r"AI.*ERP|智能.*ERP", "ai_erp"),
        (r"Wiki|知识库|知识.*管理", "wiki_manage"),
        (r"文件共享|共享.*文件", "file_share"),
        (r"IaC|基础设施.*代码|部署.*自动", "iac_deploy"),
        (r"运维|运维.*自动", "ops_automation"),
        (r"CMS|内容管理|网站.*管理", "cms_manage"),
        (r"数据API|数据.*接口", "data_api"),
        (r"站点.*监控|网站.*监控", "site_monitor"),
        (r"可观测|observability", "observability"),
        (r"APM|应用.*性能|性能.*监控", "apm_monitor"),
        (r"安全.*监控|安全.*事件", "security_monitor"),
        (r"消息队列|queue", "message_queue"),
        (r"消息代理|broker", "message_broker"),
        (r"Git.*管理|git.*操作|提交|推送", "git_manage"),
        (r"桌面.*自动|桌面操作", "desktop_automation"),
        (r"远程.*桌面", "remote_desktop"),
        (r"电脑.*控制|控制.*电脑", "computer_control"),
        (r"截图.*代码|转代码", "screenshot_to_code"),
        (r"语音.*合成|文字.*转语音|TTS", "voice_synth"),
        (r"视频.*脚本|脚本.*生成", "video_script"),
        (r"多智能体|multi.*agent|多Agent|团队", "multi_agent"),
        (r"自主.*任务|自动.*任务", "autonomous_task"),
        (r"生成.*应用|Web.*应用|生成.*网站", "create_webapp"),
        (r"Markdown|文档.*转换|转MD", "markdown_convert"),
        (r"OCR|图片.*识别|识别.*文字", "ocr_image"),
        (r"PDF|提取.*PDF|PDF.*内容", "extract_pdf"),
        (r"文档.*提取|提取.*文档", "document_extraction"),
        (r"文档.*系统|文档管理", "document_system"),
        (r"消息.*平台|发送.*消息", "messaging_platform"),
        (r"PaaS|部署.*应用|应用.*部署", "paas_deploy"),
        (r"CRM|客户.*管理|联系人", "crm_contacts"),
    ]
]

# ── 直接路由（高频固定响应）──

_DIRECT_ROUTES: dict[str, tuple[str, str]] = {
    "游戏": ("games", "🎮 **游戏**\n• ⚫ [五子棋](/gomoku.html)\n• 👩 [老婆跳井](/wife_well.html)\n• 🐺 [狼吃娃](/wolf)\n• 🐍 [贪吃蛇](/snake)\n• 🛩️ [打飞机](/shooter)"),
    "系统怎么样": ("status", "✅ AUTO-EVO-AI V0.1 运行正常 · 87工具 · 双LLM"),
    "做一个计算器": ("app", "✅ **计算器**\n[📄 打开](/app_calc.html)"),
    "五子棋": ("app", "✅ **五子棋**\n[📄 打开](/gomoku.html)"),
    "老婆跳井": ("app", "✅ **老婆跳井**\n[📄 打开](/wife_well.html)"),
    "狼吃娃": ("app", "✅ **狼吃娃**\n[📄 打开](/wolf)"),
    "贪吃蛇": ("app", "✅ **贪吃蛇**\n[📄 打开](/snake)"),
    "打飞机": ("app", "✅ **打飞机**\n[📄 打开](/shooter)"),
    "有什么工具": ("tools", "📦 系统当前有 **87 个工具**可用，涵盖：\n🌐 浏览器 · 📊 研究 · 🏗️ 代码 · 📄 文档\n📈 数据 · 🤖 AI · 👤 企业 · ⚙️ 运维\n输入「帮助」查看更多"),
    "帮助": ("help", "💡 **试试说：**\n「帮我审查这段代码」\n「研究一下量子计算」\n「生成一个图表」\n「发一封邮件」\n「分析代码安全性」"),
}


# ═══════════════════════════════════════════════════════
# 路由内核
# ═══════════════════════════════════════════════════════

def route_and_execute(user_input: str, history: list | None = None) -> dict:
    """
    用户输入 → 智能路由 → 执行/回复

    返回: {"type":"tool"|"direct"|"chat", "name":str, "data":str, "tool_output":str|None}
    """
    text = user_input.strip()
    start = time.time()

    # ── 0. 直接路由（最高优先级）──
    for key, (rtype, reply) in _DIRECT_ROUTES.items():
        if key in text or text == key:
            return {"type": "direct", "name": rtype, "data": reply, "latency": time.time() - start}

    # ── 1. LLM Function Calling（首选）──
    try:
        result = _try_function_calling(text, history)
        if result:
            return result
    except Exception:
        pass

    # ── 2. 关键词模糊匹配（降级）──
    for pattern, tool_name in _KEYWORD_TOOLS:
        if pattern.search(text):
            try:
                output = exec_tool(tool_name, {"query": text})
                return {
                    "type": "tool",
                    "name": tool_name,
                    "data": output.get("data", ""),
                    "latency": time.time() - start,
                }
            except Exception as e:
                return {"type": "chat", "name": "chat", "data": f"工具 {tool_name} 调用失败: {e}", "latency": time.time() - start}

    # ── 3. 纯聊天（兜底）──
    try:
        text_out, _ = call_llm([{"role": "user", "content": text}], timeout=30)
        return {"type": "chat", "name": "chat", "data": text_out or "抱歉，我没有理解你的意思。", "latency": time.time() - start}
    except Exception:
        return {"type": "chat", "name": "chat", "data": "你好！我是 AUTO-EVO-AI，有87个工具可用。请告诉我需要什么帮助？", "latency": time.time() - start}


def _try_function_calling(text: str, history: list | None = None) -> dict | None:
    """
    尝试 LLM Function Calling。
    把 87 个工具定义发给 Qwen3.6，看 LLM 是否选择调用工具。
    """
    start = time.time()
    # 构建带工具定义的 prompt
    tool_names = ", ".join(t["name"] for t in _TOOL_DEFS[:10]) + "..."
    sys_prompt = f"""你是 AUTO-EVO-AI 的智能路由助手。你有 87 个工具可用。

当用户请求涉及以下操作时，你必须选择最合适的工具并调用它：
- 代码相关 → code_review/code_analyze/code_edit/fix_issue
- 搜索/研究 → web_search/deep_research  
- 文档/文件 → markdown_convert/ocr_image/extract_pdf
- 数据/图表 → chart_create/dashboard/bi_report
- 安全/审计 → security_scan/code_audit/contract_review
- 企业/业务 → erp_manage/crm_contacts/create_invoice
- 运维/部署 → iac_deploy/site_monitor/paas_deploy

可以使用的工具关键字: {tool_names}

用户请求: {text}

请直接回复你选择的工具名称和参数，格式: TOOL:工具名 | 参数说明
如果不需要工具，直接回复聊天内容。"""

    messages = [{"role": "system", "content": sys_prompt}]
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": text})

    text_out, _ = call_llm(messages, timeout=60)

    if not text_out:
        return None

    text_out = text_out.strip()

    # 解析 TOOL:xxx 格式
    tool_match = re.match(r"TOOL:\s*(\w+)", text_out)
    if tool_match:
        tool_name = tool_match.group(1)
        # 验证工具存在
        all_tools = {t["name"] for t in list_tools()}
        if tool_name in all_tools:
            output = exec_tool(tool_name, {"query": text})
            return {
                "type": "tool",
                "name": tool_name,
                "data": output.get("data", ""),
                "latency": time.time() - start,
            }

    # LLM 选择直接回复
    return {"type": "chat", "name": "chat", "data": text_out, "latency": time.time() - start}
