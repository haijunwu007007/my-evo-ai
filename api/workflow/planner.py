"""AUTO-EVO-AI V0.1 — LLM任务分解器

接收高级目标 → LLM分析 → 输出可执行步骤列表
"""
import logging
logger = logging.getLogger("evo.planner")

import json, traceback
from typing import List, Optional

# 87工具定义（精简版，给LLM）
TOOL_DEFS = """可用工具清单（name: description）:
- browser_automate: 浏览器自动化，访问网页截图
- web_scrape: 爬取网页内容
- web_search: 搜索互联网
- deep_research: 对主题深度研究生成报告
- code_review: 审查代码质量
- code_edit: AI编辑修改代码
- code_analyze: 分析代码结构
- generate_test: 自动生成单元测试
- fix_issue: 分析并修复GitHub Issue
- claude_code: AI写代码实现功能
- fullstack_project: 生成全栈项目骨架
- create_webapp: 一键生成Web应用
- chart_create: 根据数据生成图表
- bi_report: 生成BI分析报告
- dashboard: 生成仪表盘
- data_table: 操作数据表格
- spreadsheet: 生成电子表格
- nl_query_db: 自然语言查数据库
- etl_pipeline: 运行ETL数据管道
- api_test: 测试API接口
- site_monitor: 监控网站状态
- ocr_image: 图片文字识别
- extract_pdf: 提取PDF内容
- markdown_convert: 文档转Markdown
- document_extraction: 从文件提取结构化内容
- document_system: 管理文档系统
- send_email: 发送邮件
- send_social: 发社交媒体
- send_notification: 发系统通知
- send_sms: 发短信
- messaging_platform: 多渠道消息平台
- email: 邮件系统
- create_invoice: 生成发票
- create_ticket: 创建工单
- crm_contacts: CRM联系人管理
- contract_review: 合同审查
- legal_agreement: 生成法律协议
- survey_create: 创建问卷
- ai_testing: AI模型测试
- agent_eval: Agent性能评测
- autonomous_task: 自主任务执行
- multi_agent: 多Agent协作
- video_script: 生成视频脚本
- screenshot_to_code: 截图转代码
- voice_synth: 语音合成
- skill_learn: 技能学习
- password_manager: 密码管理
- auth_check: 身份认证
- memory_save/search: 记忆管理
- file_storage/share: 文件存储共享
- git_manage: Git版本管理
- iac_deploy: IaC部署
- paas_deploy: PaaS平台部署
- ops_automation: 运维自动化
- cms_manage: CMS内容管理
- project_manage: 项目管理
- erp_manage: ERP管理
- ai_erp: AI智能ERP
- employee_lookup: 查员工
- schedule_add: 日程调度
- expense_record: 记费用
- security_scan: 安全扫描
- code_audit: 代码审计
- security_monitor: 安全监控
- message_queue: 消息队列管理
- message_broker: 消息代理
- observability: 可观测
- apm_monitor: APM监控
- mlops: MLOps流水线
- llm_observability: LLM观测
- rss_aggregator: RSS聚合
- audio_transcribe: 音频转录
- flowchart: 生成流程图
- e_signature: 电子签名
- smart_home: 智能家居
- remote_desktop: 远程桌面
- desktop_automation: 桌面自动化
- computer_control: 电脑控制
- lowcode_platform: 低代码平台
- lowcode: 低代码构建
- external_tools: 外部工具集成
- api_discover: API发现
"""


def create_planner_prompt(goal: str, context: Optional[str] = None) -> str:
    """生成任务分解Prompt"""
    prompt = """你是一个AI任务规划专家。请将用户的目标分解为可执行的步骤。

TOOL_LIST
规则：
1. 每一步必须使用上述工具之一
2. 步骤结果要传递给下一步（用 depends_on 引用）
3. 输出必须是纯 JSON 数组，不要任何其他文字
4. 如果无法用现有工具完成，在最后加 "NEEDS_MANUAL: ..."

用户目标: GOAL_PLACEHOLDER
CTX_PLACEHOLDER
输出格式示例 (JSON数组):
[
  {"id":"step_1","tool":"web_search","label":"搜索资料","args":{"query":"关键词"}},
  {"id":"step_2","tool":"deep_research","label":"深度分析","args":{"topic":"结果"},"depends_on":["step_1"]},
  {"id":"step_3","tool":"chart_create","label":"生成图表","args":{"data":"[]"},"depends_on":["step_2"]}
]"""
    prompt = prompt.replace("TOOL_LIST", TOOL_DEFS)
    prompt = prompt.replace("GOAL_PLACEHOLDER", goal)
    prompt = prompt.replace("CTX_PLACEHOLDER\n", f"额外上下文: {context}\n" if context else "")
    return prompt


def parse_steps(llm_response: str) -> dict:
    """解析LLM返回的步骤JSON"""
    text = llm_response.strip()
    # 清理可能的markdown代码块
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        steps = json.loads(text)
        if isinstance(steps, list):
            return {"ok": True, "steps": steps}
        return {"ok": False, "error": "LLM未返回数组"}
    except json.JSONDecodeError as e:
        # 检查是否有 NEEDS_MANUAL
        if "NEEDS_MANUAL" in text:
            manual = text.split("NEEDS_MANUAL:")[1].strip() if "NEEDS_MANUAL:" in text else ""
            return {"ok": False, "error": f"需要人工介入: {manual}", "needs_manual": True}
        return {"ok": False, "error": f"JSON解析失败: {e}"}
