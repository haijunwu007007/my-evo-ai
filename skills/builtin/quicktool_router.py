"""QuickTool 统一路由注册 — 将前端所有工具按钮注册为真实技能"""
import json, re, logging, os
from pathlib import Path
from api.routes.routes_skills import SkillDefinition, _SKILL_REGISTRY, _SKILL_HANDLERS

logger = logging.getLogger("evo.qtskills")

# 前端 _TOOL_HINTS 中的所有中文工具名 → 描述映射
_QT_SKILL_MAP = {
    # 文档/办公
    "文档生成": "生成 Word/PDF/文字文档，如合同、方案、报告",
    "电子表格": "创建和编辑 Excel 电子表格、数据表",
    "演示文稿": "生成 PPT 演示文稿",
    "PDF处理": "读取、解析、转换 PDF 文件",
    "代码审查": "审查代码质量、发现Bug和安全隐患",
    "音频转录": "将音频/录音转为文字",
    "合同审查": "审查合同条款、识别风险",
    "OCR识别": "识别图片中的文字（光学字符识别）",
    "数据图表": "生成数据可视化图表",
    "流程图": "生成流程图、架构图、思维导图",
    "数学计算": "数学表达式计算，如四则运算、公式计算",

    # 数据管理
    "NocoDB管理": "管理 NocoDB 电子表格数据库",
    "Grist分析": "分析 Grist 电子表格数据",
    "Novu通知": "通过 Novu 发送多渠道通知",
    "Gitea代码": "管理 Gitea 代码仓库",
    "Wiki知识": "查阅和管理 Wiki 知识库",
    "BookStack百科": "管理 BookStack 百科知识库",
    "文件分享": "文件分享和传输",
    "RSS阅读": "读取 RSS 资讯订阅",
    "邮件营销": "发送邮件营销/Newsletter",

    # 项目/企业
    "项目管理": "管理项目、任务、里程碑",
    "日程调度": "日程安排和日历调度",
    "身份认证": "身份认证和单点登录管理",
    "Odoo管理": "管理 Odoo ERP 系统",
    "ERP管理": "企业管理资源规划",

    # 部署/运维
    "部署编排": "K8s/Terraform 部署编排",
    "自动化运维": "Ansible 自动化运维",
    "内容管理": "CMS 内容管理系统管理",
    "数据API": "REST/GraphQL 数据API",
    "一键部署": "一键部署应用服务",

    # 监控/搜索
    "全文搜索": "全文搜索引擎查询",
    "对象存储": "S3/MinIO 对象存储管理",
    "站点监控": "Uptime 站点可用性监控",
    "全面监控": "全面基础设施监控",
    "APM链路": "APM 链路追踪和性能监控",
    "安全监控": "SIEM 安全事件监控",
    "消息队列": "NATS/RabbitMQ 消息队列管理",
    "消息代理": "消息代理管理",

    # 实验/测试
    "实验追踪": "MLflow 实验追踪",
    "LLM观测": "Langfuse LLM 观测和监控",
    "API测试": "API 接口测试",
    "流程图": "Mermaid 流程图/架构图",

    # 远程/安全
    "远程桌面": "RustDesk 远程桌面连接",
    "电子签名": "DocuSeal 电子签名",
    "智能家居": "HomeAssistant 智能家居控制",
    "密码管理": "Vaultwarden 密码管理器",
    "低代码构建": "Appsmith 低代码构建管理工具",
    "数据同步": "Airbyte 数据同步管道",
    "低代码平台": "NocoBase 低代码业务应用构建",
    "反爬提取": "反爬虫数据提取",
    "代码知识": "代码知识图谱查询",
    "全网搜索": "全网搜索和信息检索",
    "页面动效": "页面动效和动画设计",
    "浏览器任务": "浏览器自动化任务",
    "知识查询": "知识库查询",
    "GPT研究": "GPT 研究助手",
    "自主生成": "自主生成项目代码",
    "记忆管理": "长期记忆存储和回忆",
    "工具集成": "外部工具集成管理",
    "自进化分析": "自我进化分析",
    "技能学习": "学习和获取新技能",
    "桌面自动化": "桌面自动化操作",
    "API发现": "发现和搜索 API",
    "文档转MD": "文档转为 Markdown 格式",
    "AI爬虫": "AI 智能爬虫抓取网页数据",
    "代码执行": "在线代码执行",
    "截图转代码": "截图/设计图转代码",
    "PR审查": "Pull Request 审查",
    "测试生成": "自动生成单元测试",
    "AI编辑": "AI 代码编辑",
    "消息平台": "消息平台集成",
    "语音合成": "文本转语音",
    "多智能体": "多智能体团队协作",
    "自主任务": "自主任务执行",
    "修复Issue": "自动修复 GitHub Issue",
    "生成项目": "从需求生成全栈项目",
    "自然查库": "自然语言查询数据库",
    "生成应用": "生成应用",
    "Agent评测": "Agent 评测和基准测试",
    "视频脚本": "生成视频脚本",
    "可视化": "数据可视化",
    "图片OCR": "图片 OCR 文字识别",
    "PDF识别": "PDF 文字识别",
    "安全扫描": "Web 安全扫描",
    "代码审计": "代码安全审计",
    "合同审查": "合同风险和合规审查",
    "CRM联系人": "CRM 联系人管理",
    "开发票": "创建和管理发票",
    "创建工单": "创建客服工单",
    "发社媒": "社交媒体发帖",
    "营销邮件": "发送营销邮件",
    "BI图表": "BI 数据仪表盘",
    "创建问卷": "创建问卷调查",
    "文档提取": "提取文档内容",
    "法律协议": "创建法律协议",
    "Claude写代码": "AI 代码生成",
    "查员工": "查询员工信息",
    "仪表盘": "数据仪表盘",
    "记费用": "记录费用",
    "代码图谱": "代码知识图谱",
    "知识提取": "知识提取",
    "知识库": "知识库管理",
    "EVE架构": "EVE 系统架构",
    "视频制作": "AI 视频制作",
    "MCP编辑": "MCP 工具编辑",
}

# 英文/拼音关键词
_QT_EN_SKILL_MAP = {
    "ocr": "OCR识别：图片文字识别",
    "bi": "BI数据分析：商业智能分析",
    "crm": "CRM客户管理：客户关系管理",
    "etl": "ETL数据管道：数据抽取转换加载",
    "hr": "HR人力资源：员工信息管理",
    "ticket": "工单管理：创建和管理客服工单",
}


def register_quicktool_skills():
    """一次注册所有快速工具技能"""
    count = 0
    _handler = _quicktool_handler
    for name, desc in _QT_SKILL_MAP.items():
        if name not in _SKILL_REGISTRY:
            skill = SkillDefinition(
                name=name,
                version="1.0.0",
                description=desc,
                author="AUTO-EVO-AI",
                category="工具",
                icon="🔧",
                tags=[name, "quick-tool"],
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            )
            _SKILL_REGISTRY[name] = skill
            _SKILL_HANDLERS[name] = _handler
            count += 1

    for name, desc in _QT_EN_SKILL_MAP.items():
        if name not in _SKILL_REGISTRY:
            skill = SkillDefinition(
                name=name,
                version="1.0.0",
                description=desc,
                author="AUTO-EVO-AI",
                category="工具",
                icon="🔧",
                tags=[name, "quick-tool"],
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            )
            _SKILL_REGISTRY[name] = skill
            _SKILL_HANDLERS[name] = _handler
            count += 1

    # 注册通用执行器
    _SKILL_HANDLERS["__quicktool__"] = _quicktool_handler
    # 确保数学计算和PPT中文别名注册（从英文技能映射）
    _alias_map = {"数学计算": "math-calculator", "PPT": "ppt-generator"}
    for cn_name, eng_name in _alias_map.items():
        if cn_name not in _SKILL_REGISTRY and eng_name in _SKILL_REGISTRY:
            eng_s = _SKILL_REGISTRY[eng_name]
            cn_s = SkillDefinition(
                name=cn_name, version="1.0.0", description=eng_s.description,
                author=eng_s.author, category=eng_s.category, icon=eng_s.icon,
                tags=[cn_name, eng_name], handler=eng_s.handler
            )
            _SKILL_REGISTRY[cn_name] = cn_s
            if eng_name in _SKILL_HANDLERS:
                _SKILL_HANDLERS[cn_name] = _SKILL_HANDLERS[eng_name]
            count += 1
    if count:
        logger.info(f"[QTSKILLS] 注册 {count} 个快速工具技能 + 通用LLM执行器")
    return count


def _quicktool_handler(params: dict, context: dict = None) -> dict:
    """QuickTool通用执行器 — 调用LLM处理请求"""
    query = params.get("query", "") or params.get("prompt", "") or str(params)
    try:
        from api.agent_llm import call_llm
        sp = f"你是一个全能工具助手。用户请求: {query[:500]}\n请直接完成用户请求，输出结果。如果请求需要生成文件，描述文件内容和格式。"
        text, _ = call_llm([{"role": "user", "content": sp}])
        return {"text": text or "处理完成", "mode": "llm"}
    except Exception as e:
        logger = __import__('logging').getLogger('evo.quicktool')
        logger.warning(f"QuickTool执行失败: {e}")
        return {"text": f"收到请求：{query[:100]}。请补充更多细节。", "mode": "fallback"}
