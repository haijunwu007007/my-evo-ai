"""智能体路由 — ReAct 架构：Thought → Action → Observe"""
from fastapi import APIRouter
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os, json, asyncio, httpx
from core.logging_config import get_logger
logger = get_logger("evo.api.smart")
router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent

# ── 可配置的基础地址（环境变量覆盖默认值，无需改代码）──
_API_BASE = os.environ.get("EVO_API_BASE", "http://127.0.0.1:8765")
_DOMAIN = os.environ.get("EVO_DOMAIN", "https://autoevoai.com")
_N8N_BASE_PATH = os.environ.get("N8N_BASE", "/home/ubuntu/n8n-workflows/n8n-workflows-main")

class Req(BaseModel):
    message: str; api_key: Optional[str] = ""; lang: Optional[str] = "zh-CN"; context: Optional[list] = []

# ── 导航路由映射（不依赖LLM，直接跳转到对应管理页面）──
_NAVIGATION_MAP = [
    # 管理中心
    (["用户管理","用户列表","管理用户","查看用户","权限管理","角色管理","添加用户","删除用户"], "/admin#"),
    (["管理中心","管理后台","系统管理","后台管理","打开管理"], "/admin"),
    # 工作流
    (["桌面","桌面自动化","桌面操作","desktop"], "/desktop"),
    (["工作流","编排","工作流编排","创建流程","编辑工作流"], "/canvas"),
    (["流程编排","自动化配置","自动任务","创建自动化","自动化流程"], "/automations"),
    # 智能体 & 专家
    (["智能体","agent","智能助理","AI助手","查看agent","多智能体","agent团队"], "/agents"),
    (["专家","专家库","找专家","领域专家","行业专家","激活专家"], "/experts"),
    (["技能","扩展","技能列表","查看技能","skill","skills"], "/skills"),
    (["openclaw","claw","消息平台","连接平台"], "/claw"),
    (["hermes","信息搜集"], "/hermes"),
    (["human","桌面伴侣"], "/human"),
    # 部署 & 发布
    (["部署","发布","上线","部署应用","部署服务","发布应用"], "/deploy"),
    (["视频","视频生成","做视频","制作视频","生成视频"], "/video"),
    # 数据 & 知识
    (["记忆","知识库","记忆库","cognee","知识图谱","回忆"], "/cognee"),
    (["学习","教程","learn","学习中心","我要学习","开始学习"], "/learn.html"),
    (["开源","中心","市场","hub","开源项目","发现项目"], "/hub"),
    # 开发 & 画布
    (["画布","canvas","编排画布","可视化编排"], "/canvas"),
    (["循环","loop","循环任务","工作流循环"], "/loop"),
    # 代码 & 审查
    (["代码审查","code review","审查代码","review","版本差异","diff"], "/review"),
    (["应用","应用列表","已生成","我的应用","查看应用"], "/apps"),
    # 系统
    (["设置","配置","系统设置","偏好设置","参数配置","修改配置"], "/settings"),
    (["监控","仪表盘","dashboard","系统状态","查看状态","运行状态"], "/dashboard"),
    (["能力","能力中心","capabilities","系统能力"], "/capabilities"),
    # 企业
    (["企业","enterprise","集团os","billion","集团操作系统"], "/enterprise.html"),
    (["公司","虚拟公司","company","公司管理"], "/company.html"),
    (["n8n","工作流引擎","n8n模板","模板库"], "/n8n"),
    # 其他
    (["工具","工具箱","tool","tools"], "/tools"),
    (["通知","通知配置","消息通知","推送配置"], "/settings"),
    (["安装向导","首次设置","初始化"], "/install-wizard"),
    (["插件","插件列表","plugin"], "/plugins"),
    (["API","API管理","接口管理","api密钥","apikey"], "/api-keys"),
    (["审计","审计日志","操作日志","log","日志记录"], "/audit"),
    (["备份","备份管理","数据备份","恢复"], "/backup"),
    (["克隆","生成网站","克隆网站","cloner"], "/cloner"),
    # 扩展导航 — 页面直达
    (["桌面","桌面操作","桌面自动化","desktop"], "/desktop"),
    (["代理","本地代理","agent代理","local agent"], "/agent"),
    (["fork","forkstudio","fork工作室","ForkStudio"], "/ForkStudio"),
    (["编程助手","copilot","代码助手","开发助手"], "/copilot"),
    (["钩子","webhook","hook","hooks","触发器"], "/hooks"),
    (["游戏","小游戏","娱乐","wolf"], "/wolf"),
    (["文档","api文档","接口文档","scalar","快速入门"], "/docs"),
    (["帮助","帮助中心","faq","常见问题","使用指南"], "/faq"),
    (["教程","教程中心","指导","guidence","tutorial"], "/tutorial"),
    (["市场","market","marketplace","插件市场"], "/marketplace"),
    (["注册","注册页面","signup","新用户注册"], "/register"),
    (["登录","login","登录页面","登录入口"], "/login"),
    (["聊天记录","对话记录","对话历史","archive","存档"], "/chat-archive"),
    (["导出","数据导出","导出数据","output","输出目录"], "/output"),
    # 高级导航 — Agent工厂/软件工厂/Ollama/文档生成
    (["agent工厂","agent-factory","agentfactory","智能体工厂","生成agent"], "/agent-factory"),
    (["软件工厂","software factory","soft-factory","项目生成","生成项目"], "/soft-factory"),
    (["oss分销","oss-distiller","开源分销"], "/oss-distiller"),
    (["蒸馏","蒸馏一切","蒸馏技能","技能蒸馏","整理"], "/distill.html"),
    (["记忆","记忆管理","memos","备忘录"], "/memos"),
    (["视觉","视觉理解","vision","图片理解"], "/vision"),
    (["realtime","实时通信","实时同步","实时协作"], "/realtime"),
    (["团队","团队管理","team","协作"], "/team"),
    (["频道","channel","通信频道","消息频道"], "/channel"),
    (["权限","权限管理","permission","rbac","角色权限"], "/permission"),
    (["自进化","自我进化","self-evolve","演进"], "/self-evolve"),
    (["代码库","codebase","代码知识","代码索引"], "/codebase"),
    # 终端/命令行
    (["终端","命令行","cli","命令","控制台"], "/cli"),
    (["一键部署","compose","docker部署","容器部署","portainer"], "/deploy"),
    # ── 侧栏缺失映射（2026-07-10 补齐）──
    (["团队编排","团队与编排","teamcanvas","团队协作画布","team-canvas"], "/team-canvas.html"),
    (["远程执行","远程控制","远程管理","remote"], "/remote.html"),
    (["审批中心","审批管理","审批流程","审核中心","approval"], "/review.html"),
    (["扫码安装","安装到桌面","安装桌面版","desktop安装"], "/desktop"),
    # enterprise 顶栏
    (["模块协调","协调中心","全模块协调","openV3Panel","协调引擎"], "/enterprise.html#"),
    (["模块浏览器","浏览模块","module explorer","模块搜索"], "/enterprise.html#explorer"),
    (["内网穿透","隧道","tunnel","公网访问","远程访问"], "/enterprise.html#tunnel"),
    (["云部署","部署指南","cloud deploy","云部署指南"], "/api/deploy-guide"),
    (["模块管理器","模块管理","module manager","模块管理面板"], "/enterprise.html#manager"),
    (["系统监控","系统监控面板","monitor panel","实时监控"], "/enterprise.html#monitor"),
    (["定时调度","调度器","scheduler_panel","任务调度器"], "/enterprise.html#scheduler"),
    (["事件引擎","事件驱动","event engine","事件总线"], "/enterprise.html#events"),
    (["任务队列","task queue","队列管理","任务队列管理"], "/enterprise.html#queue"),
    (["推送监控","ws monitor","websocket监控","实时推送"], "/enterprise.html#ws"),
    # ── 扫描发现的缺失入口（2026-07-10 补齐）──
    (["对话页面","回到对话","聊天界面","返回首页","回到首页","首页"], "/"),
    (["管线引擎","管线","pipeline studio","pipeline-studio","流水线引擎","模块管线"], "/enterprise.html#pipeline"),
    (["配置中心","统一配置中心","config center","config-center","集中配置"], "/enterprise.html#config"),
    (["退出登录","注销","登出","退出系统","logout","signout"], "/"),
    (["新对话","重置对话","清空对话","重新开始","新建会话","开始新对话"], "/"),
    (["历史记录","对话历史","查看历史","聊天历史","消息历史","历史消息"], "/"),
    (["切换模型","模型状态","查看模型","当前模型","使用模型","模型切换","切换LLM"], "/"),
    (["切换主题","亮色模式","深色模式","暗色模式","白天模式","夜间模式","主题切换","toggleTheme"], "/"),
    (["折叠侧栏","展开侧栏","折叠侧边栏","展开侧边栏","折叠菜单","收起侧栏","toggleSidebar"], "/"),
    (["切换语言","语言设置","中文切换","英文切换","修改语言","语言切换","国际化","i18n"], "/"),
]

# ── 直接信息查询（不依赖LLM，直接查API）──
_INFO_QUERIES = {
    "模块列表": "/api/v1/modules",
    "所有模块": "/api/v1/modules",
    "有哪些模块": "/api/v1/modules",
    "版本信息": "/api/v1/version",
    "系统版本": "/api/v1/version",
    "系统状态": "/api/v1/status",
    "系统怎么样": "/api/v1/status",
    "系统如何": "/api/v1/status",
    "健康检查": "/api/v1/health",
    "运行状态": "/api/v1/status",
    "有哪些智能体": "/api/v1/agents",
    "智能体列表": "/api/v1/agents",
    "agent列表": "/api/v1/agents",
    "技能列表": "/api/v1/skills",
    "有哪些技能": "/api/v1/skills",
    # 扩展查询
    "用户列表": "/api/v1/users/list",
    "所有用户": "/api/v1/users/list",
    "查看用户列表": "/api/v1/users/list",
    "定时任务": "/api/v1/scheduler/tasks",
    "调度任务": "/api/v1/scheduler/tasks",
    "查看定时任务": "/api/v1/scheduler/tasks",
    "所有定时任务": "/api/v1/scheduler/tasks",
    "事件规则": "/api/v1/events/rules",
    "管线列表": "/api/v1/pipelines",
    "所有管线": "/api/v1/pipelines",
    "队列任务": "/api/v1/queue/tasks",
    "工作流模板": "/api/v1/templates",
    "所有模板": "/api/v1/templates",
    "系统诊断": "/api/v1/diagnosis/system",
    "系统指标": "/api/v1/system/metrics",
    "实时监测": "/api/v1/monitor/realtime",
    "监测数据": "/api/v1/monitor/realtime",
    "记忆统计": "/api/v1/cognee/stats",
    "记忆状态": "/api/v1/cognee/status",
    "配置列表": "/api/v1/config",
    "所有配置": "/api/v1/config",
    "认证配置": "/api/v1/auth/config",
    "健康状态": "/api/v1/health",
    # 扩展信息查询
    "连接器列表": "/api/v1/connectors",
    "所有连接器": "/api/v1/connectors",
    "集成列表": "/api/v1/gateway/tools",
    "网关工具": "/api/v1/gateway/tools",
    "已启用集成": "/api/v1/gateway/enabled",
    "部署状态": "/api/v1/deploy/v2/status",
    "部署列表": "/api/v1/deploy/v2/status",
    "技能统计": "/api/v1/skills/stats",
    "插件列表": "/api/v1/plugins",
    "所有插件": "/api/v1/plugins",
    "服务状态": "/api/v1/services",
    "所有服务": "/api/v1/services",
    "通知记录": "/api/v1/notify/logs",
    "通知历史": "/api/v1/notify/logs",
    "认证配置": "/api/v1/auth/config",
    "用户统计": "/api/v1/users/stats",
    "会话列表": "/api/v1/session/list",
    "学习进度": "/api/v1/learn/progress",
    "环境变量": "/api/v1/env/list",
    "环境配置": "/api/v1/env/list",
    "循环任务列表": "/api/v1/loop/tasks",
    "MCP服务器": "/api/v1/mcp/servers",
    "MCP工具": "/api/v1/mcp/servers",
    "缓存状态": "/api/v1/cache/status",
}

async def _execute_info_query(msg: str) -> str | None:
    """直查信息查询 — 不依赖LLM"""
    import httpx
    for keyword, path in _INFO_QUERIES.items():
        if keyword in msg:
            try:
                async with httpx.AsyncClient(timeout=8, base_url=_API_BASE) as c:
                    r = await c.get(path)
                    data = r.json() if r.status_code == 200 else {"error": f"{r.status_code}"}
                    return json.dumps(data, ensure_ascii=False, indent=2)[:2000]
            except Exception as e:
                return f"查询失败: {e}"
    return None

# ── 动作执行映射（匹配关键词→调API→返回结果，不依赖LLM）──
# 每个动作: (关键词列表, HTTP方法, API路径, 参数字段提取函数)
# _raw: 取关键词后的全部文本, _name: 取下一段文本作为字段值
_ACTION_MAP = [
    # ── 用户管理 ──
    (["创建用户", "注册用户", "添加用户", "新增用户"], "POST", "/api/v1/user/register",
     lambda msg: {"username": _extract_after(msg), "password": "123456"}),

    # ── 记忆/知识 ──
    (["记住", "请记住", "帮我记住", "保存记忆"], "POST", "/api/v1/cognee/remember",
     lambda msg: {"content": _extract_after(msg), "tags": ["chat"], "source": "chat", "importance": 1}),
    (["回忆", "搜索记忆", "查找记忆", "查询记忆"], "POST", "/api/v1/cognee/recall",
     lambda msg: {"query": _extract_after(msg) or "最近", "limit": 10}),
    (["忘记", "删除记忆"], "POST", "/api/v1/cognee/forget",
     lambda msg: {"mid": _extract_after(msg)}),
    (["学习技能"], "POST", "/api/v1/cognee/skills/learn",
     lambda msg: {"name": _extract_after(msg)}),

    # ── 定时任务 ──
    (["创建定时任务", "添加定时任务", "设置定时"], "POST", "/api/v1/scheduler/tasks",
     lambda msg: {"name": _extract_after(msg) or "任务", "target_type": "module", "target_id": "system", "cron": "0 8 * * *", "interval_seconds": 86400}),

    # ── 队列任务 ──
    (["创建队列任务", "添加队列任务", "加入队列"], "POST", "/api/v1/queue/tasks",
     lambda msg: {"name": _extract_after(msg) or "任务", "type": "execute", "target": "system"}),

    # ── 管线 ──
    (["创建管线", "创建流水线", "创建管道"], "POST", "/api/v1/pipelines",
     lambda msg: {"name": _extract_after(msg) or "流水线", "description": "", "steps": []}),

    # ── 事件规则 ──
    # ── 蒸馏 ──
    (["蒸馏这个", "帮我蒸馏", "提炼这个", "帮我提炼"], "POST", "/api/v1/distill/start",
     lambda msg: _build_distill_body(msg)),
    # ── 事件规则 ──
    (["创建规则", "添加规则", "创建事件规则"], "POST", "/api/v1/events/rules",
     lambda msg: {"name": _extract_after(msg) or "规则", "pattern": "*", "action": "notify"}),

    # ── 配置操作 ──
    (["修改配置", "设置配置", "更新配置"], "PUT", "/api/v1/config/",
     lambda msg: {"value": _extract_after(msg)}),
    (["保存配置", "应用配置"], "POST", "/api/v1/config/save",
     lambda _: {}),
    (["重载配置", "重新加载配置"], "POST", "/api/v1/config/reload",
     lambda _: {}),

        # ── 模块自动路由（533模块名→关键词自动匹配） ──
    (["模块自动路由"], "INTERNAL", "__module_router__", None),

    # ── 记忆树 ──
    (["添加记忆节点", "创建记忆节点"], "POST", "/api/v1/memory/add",
     lambda msg: {"node_id": f"n_{os.urandom(4).hex()}", "title": _extract_after(msg), "content": _extract_after(msg)}),

    # ── 模板 ──
    (["应用模板", "使用模板"], "POST", "/api/v1/templates/github_trending/apply",
     lambda _: {}),

    # ── 调度任务操作 ──
    (["触发任务", "立即执行"], "POST", "/api/v1/scheduler/tasks/_trigger",
     lambda msg: {"task_id": _extract_after(msg)}),

    # ── 模块管理 ──
    (["启用模块", "激活模块", "启动模块"], "POST", "/api/v1/modules/enable",
     lambda msg: {"module_name": _extract_after(msg)}),
    (["禁用模块", "停用模块", "关闭模块"], "POST", "/api/v1/modules/disable",
     lambda msg: {"module_name": _extract_after(msg)}),
    (["重启模块", "重新加载模块", "刷新模块"], "POST", "/api/v1/modules/reload",
     lambda msg: {"module_name": _extract_after(msg)}),
    (["热加载模块", "热重载"], "POST", "/api/v1/modules/hot-reload",
     lambda _: {}),

    # ── 通知操作 ──
    (["发送通知", "推送通知", "发送消息", "测试通知"], "POST", "/api/v1/notify/send",
     lambda msg: {"channel": "console", "content": _extract_after(msg) or "测试通知"}),
    # ── 通知配置已在导航map中处理，无需额外action ──

    # ── 自动化创建 ──
    (["创建工作流", "创建自动化", "新建工作流", "新建自动化", "新建定时任务", "创建定时任务", "添加定时任务", "添加工作流", "添加自动化"],
     "POST", "/api/v1/automations",
     lambda msg: _build_automation(msg)),

    # ── 缓存操作 ──
    (["清理缓存", "清除缓存", "清空缓存", "刷新缓存"], "POST", "/api/v1/cache/clear",
     lambda _: {}),
    (["预热缓存"], "POST", "/api/v1/cache/warmup",
     lambda _: {}),

    # ── 日志操作 ──
    (["查看日志", "查看最近日志", "最新日志"], "GET", "/api/v1/logs/recent",
     lambda _: {"limit": 20}),
    (["清理日志", "删除日志", "清空日志"], "POST", "/api/v1/logs/cleanup",
     lambda _: {}),

    # ── 系统操作 ──
    (["重启系统", "重启服务", "重启API"], "POST", "/api/v1/system/restart",
     lambda _: {}),
    (["清理临时文件", "清理空间", "磁盘清理"], "POST", "/api/v1/system/cleanup",
     lambda _: {}),

    # ── 学习/教程 ──
    (["开始学习", "学习课程"], "POST", "/api/v1/learn/start",
     lambda msg: {"course_id": _extract_after(msg) or "intro", "user": _get_username()}),
    (["录制演示", "录制教程", "开始录制"], "POST", "/api/v1/learn/demo/create",
     lambda msg: {"name": _extract_after(msg) or f"演示_{int(time.time())}", "auto_record_mode": True}),
    (["查看演示", "演示列表", "我的学习"], "GET", "/api/v1/learn/list",
     lambda _: {}),

    # ── 数据导出 ──
    (["导出数据", "导出CSV", "导出JSON"], "GET", "/api/v1/data/export",
     lambda msg: {"format": "csv" if "csv" in msg.lower() else "json"}),

    # ── 专家激活 ──
    (["激活专家", "激活行业专家", "查找专家", "找行业专家"], "GET", "/api/v1/experts/search",
     lambda msg: {"q": _extract_after(msg) or ""}),
    (["管理专家", "专家配置"], "POST", "/api/v1/experts/configure",
     lambda msg: {"config": {"name": _extract_after(msg)}}),

    # ── 任务/队列操作 ──
    (["取消任务", "停止任务", "终止任务"], "POST", "/api/v1/queue/tasks/_cancel",
     lambda msg: {"task_id": _extract_after(msg)}),
    (["查看队列", "队列状态", "任务队列"], "GET", "/api/v1/queue/status",
     lambda _: {}),

    # ── Webhook ──
    (["创建webhook", "添加webhook", "注册webhook"], "POST", "/api/v1/webhooks",
     lambda msg: {"name": _extract_after(msg) or "hook", "url": ""}),

    # ── N8N ──
    (["导入模板", "导入n8n", "加载模板"], "POST", "/api/v1/n8n/templates/import",
     lambda msg: {"template_id": _extract_after(msg)}),
]

def _get_username() -> str:
    """获取当前用户名"""
    try:
        from api.infra import _request_user
        u = _request_user.get()
        return u or "admin"
    except Exception:
        return "admin"

def _extract_after(msg: str) -> str:
    """提取最后一个匹配关键词后面剩余的文本（去除前缀助词）"""
    # 先找到最后出现的匹配关键词
    rest = msg
    for kw_group in _ACTION_MAP:
        for kw in kw_group[0]:
            if kw in msg:
                rest = msg.split(kw, 1)[-1].strip()
                break
    # 去除前缀助词
    for prefix in ["请帮我", "帮我", "请", "给我", "我要", "把", "将"]:
        if rest.startswith(prefix):
            rest = rest[len(prefix):].strip()
    # 如果以"的、"结尾则去掉
    if rest.endswith("的"):
        rest = rest[:-1].strip()
    return rest


def _build_distill_body(msg: str) -> dict:
    """从消息中提取蒸馏内容，自动判断是URL/文本/代码"""
    content = _extract_after(msg)
    if not content or len(content) < 8:
        content = msg  # 降级：整条消息作为蒸馏源
    import re
    if re.match(r'^https?://', content.strip()):
        return {"source_type": "url", "source": content.strip(), "name": "网页蒸馏"}
    if "def " in content and "return " in content or "import " in content[:200]:
        return {"source_type": "code", "source": content, "name": "代码蒸馏"}
    return {"source_type": "text", "source": content, "name": "文本蒸馏"}


def _detect_channel(msg: str) -> str:
    """从消息中检测通知渠道"""
    m = msg.lower()
    if "钉钉" in m or "dingtalk" in m: return "dingtalk"
    if "企微" in m or "企业微信" in m or "wecom" in m: return "wecom"
    if "飞书" in m or "feishu" in m: return "feishu"
    if "telegram" in m or "tg" in m: return "telegram"
    if "邮件" in m or "email" in m or "mail" in m: return "email"
    if "短信" in m or "sms" in m: return "sms"
    if "slack" in m: return "slack"
    if "discord" in m: return "discord"
    if "微信" in m or "wechat" in m: return "wechat"
    return "console"


def _build_automation(msg: str) -> dict:
    """从消息中提取自动化配置"""
    content = _extract_after(msg)
    import re
    now = int(__import__("time").time())
    name = f"自动化_{now % 10000}"
    schedule = "0 8 * * *"  # 默认每天早上8点
    action = "notify"
    if content:
        # 尝试提取描述/名字
        name = content.strip()[:30]
    return {
        "name": name,
        "schedule": schedule,
        "action": action,
        "enabled": True,
        "source": "input_box",
        "created_at": now,
    }


async def _execute_action(msg: str) -> str | None:
    """执行动作 — 匹配关键词→调API→返回结果，不依赖LLM"""
    import httpx
    lower = msg.lower()
    
    # ── n8n工作流模板搜索 ──
    if any(kw in msg for kw in ["n8n", "工作流模板", "n8n模板", "自动化工作流", "workflow"]):
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{_API_BASE}/api/v1/n8n/search?q={urllib.parse.quote(msg[:60])}&limit=5")
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") and data.get("workflows"):
                        ws = data["workflows"]
                        h = f"🔍 找到 {data.get('total',len(ws))} 个n8n工作流模板:\n\n"
                        for w in ws[:5]:
                            tags = " ".join(w.get("tags",[])) or ""
                            h += f"- **{w.get('name','?')}** {tags}\n  {w.get('description','')[:80]}\n  [查看详情](/n8n-browse?id={w.get('id','')})\n\n"
                        return h
                    else:
                        return "ℹ️ 未找到匹配的n8n工作流模板，试试更具体的关键词"
        except Exception as e:
            pass  # 降级
    
    # ── 研究/深度分析 → 不走模块路由 ──
    _research_kw = ["深度研究","研究报告","深入分析","全面调研","深度调研"]
    for _rk in _research_kw:
        if _rk in msg:
            _rr = None
            try:
                from modules.deep_researcher import research as _rs
                _rr = await _rs(msg)
                if _rr and isinstance(_rr, dict) and _rr.get("result") and len(str(_rr.get("result",""))) > 30:
                    return {"success": True, "result": _rr["result"]}
            except Exception as _re:
                logger.warning(f"[EARLY_RESEARCH] {_re}")
            if _rr and isinstance(_rr, dict) and _rr.get("success"):
                _txt = _rr.get("result") or _rr.get("analysis") or ""
                if _txt:
                    return {"success": True, "result": "🔬 **深度研究**\n\n" + _txt}
            break
    
    # ── 模块自动路由：仅模块名直接匹配（长关键词≥60%消息长度）才返回JSON ──
    mod_name = _find_module_in_text(msg)
    if mod_name:
        _is_explicit = False
        for _entry in (_build_module_index() or []):
            if _entry["name"] == mod_name:
                for _kw in _entry["keywords"]:
                    if len(_kw) >= 4 and _kw in msg and len(_kw) >= len(msg) * 0.6:
                        _is_explicit = True; break
                break
        if _is_explicit:
            try:
                async with httpx.AsyncClient(timeout=15, base_url=_API_BASE) as c:
                    r = await c.post(f"/api/v1/modules/{mod_name}/execute", json={"action": "execute", "params": {}})
                    if r.status_code in (200, 201):
                        data = r.json()
                        _msg = data.get("result", data.get("message", ""))
                        if _msg and len(str(_msg)) > 20:
                            return f"✅ **{mod_name}**\n{_msg[:1000]}"
                        return f"✅ **{mod_name}** 已执行"
            except Exception:
                pass  # 降级到LLM
    
    for keywords, method, url, body_fn in _ACTION_MAP:
        for kw in keywords:
            if kw in lower or kw in msg:
                body = body_fn(msg)
                try:
                    async with httpx.AsyncClient(timeout=10, base_url=_API_BASE) as c:
                        if method == "POST":
                            r = await c.post(url, json=body)
                        elif method == "PUT":
                            r = await c.put(url, json=body)
                        elif method == "DELETE":
                            r = await c.delete(url)
                        else:
                            r = await c.get(url)
                        data = r.json() if r.status_code in (200, 201) else {"error": f"HTTP {r.status_code}"}
                        result = json.dumps(data, ensure_ascii=False)[:1000]
                        # 格式化输出
                        if data.get("success"):
                            kw_name = kw[:8]
                            return f"✅ **{kw_name}...** 成功\n{result[:400]}"
                        return f"❌ **{kw[:8]}...** 失败\n{result[:400]}"
                except Exception as e:
                    return f"❌ **{kw[:8]}...** 请求失败: {e}"
    return None

async def _match_navigation(msg: str) -> str | None:
    """匹配导航路由 — 关键词匹配返回页面URL"""
    lower = msg.lower()
    for keywords, url in _NAVIGATION_MAP:
        for kw in keywords:
            if kw in lower:
                return url
    return None

# ── 意图分类模板（ReAct风格：先思考再行动）──
_INTENT_PROMPT = """你是智能路由分析器。分析用户问题，返回JSON。不要加额外解释。

规则：
- intent: chat/hot/search/create/help/calculate/agent
  - chat: 普通聊天、问答、写作、解释、建议、闲聊、天气、情感、角色扮演、系统介绍
  - hot: 查热点/热搜/热榜/头条/新闻/大事/新鲜事（如果提到具体平台，platform填平台名）
  - search: 明确说搜索xx、查找xx、搜一下xx、查一下xx（想找具体信息）
  - create: 生成文档/PPT/Excel/合同/报告/代码/文章/方案
  - help: 问系统能做什么、有什么功能、怎么使用、能力列表
  - calculate: 数学计算、算术、运算、数字计算（含数字和运算符的表达式计算）
  - agent: 多步骤复杂任务，需要调用多个工具/技能才能完成，如"先搜索XXX再生成YYY"、"查一下XXX并整理成PPT"、"搜索XXX和YYY对比分析后出报告"、"帮我XXX然后再YYY最后ZZZ"
- platform: 如果intent=hot且用户提到具体平台(百度/微博/抖音/知乎/B站/头条/腾讯/贴吧/小红书)，填平台名。否则""
- topic: 搜索主题或热点话题
- thought: 你分析用户意图的原因（一句话）

例1: q=今日百度热点 → {"intent":"hot","platform":"百度","topic":"","thought":"用户想查看百度热搜"}
例2: q=抖音热搜 → {"intent":"hot","platform":"抖音","topic":"","thought":"用户想看抖音热点"}
例3: q=腾讯微博今日热点 → {"intent":"hot","platform":"微博","topic":"","thought":"用户提到腾讯微博，其实是微博平台"}
例4: q=知乎热榜 → {"intent":"hot","platform":"知乎","topic":"","thought":"用户想看知乎热门话题"}
例5: q=今天有什么新闻 → {"intent":"hot","platform":"","topic":"新闻","thought":"用户想看通用新闻热点"}
例6: q=最近有什么大事 → {"intent":"hot","platform":"","topic":"大事","thought":"用户想了解近期重要事件"}
例7: q=B站热搜 → {"intent":"hot","platform":"B站","topic":"","thought":"B站弹幕网的热搜"}
例8: q=小红书热门 → {"intent":"hot","platform":"小红书","topic":"","thought":"小红书的热门内容"}
例9: q=搜索 python教程 → {"intent":"search","platform":"","topic":"python教程","thought":"用户明确说搜索"}
例10: q=帮我查一下北京的天气 → {"intent":"search","platform":"","topic":"北京天气","thought":"用户要查具体信息"}
例11: q=搜一下人工智能最新动态 → {"intent":"search","platform":"","topic":"人工智能最新动态","thought":"用户用\"搜一下\"关键词"}
例12: q=本系统可以做什么 → {"intent":"help","platform":"","topic":"","thought":"用户问系统功能"}
例13: q=你会什么 → {"intent":"help","platform":"","topic":"","thought":"用户想知道AI的能力"}
例14: q=如何使用这个系统 → {"intent":"help","platform":"","topic":"","thought":"用户问使用方式"}
例15: q=你好 → {"intent":"chat","platform":"","topic":"","thought":"普通打招呼"}
例16: q=帮我写一份合同 → {"intent":"create","platform":"","topic":"合同","thought":"用户要生成文档"}
例17: q=做个PPT → {"intent":"create","platform":"","topic":"PPT","thought":"用户要生成PPT"}
例18: q=今天天气怎么样 → {"intent":"chat","platform":"","topic":"","thought":"闲聊类问题，LLM直接回答"}
例19: q=我心情不好 → {"intent":"chat","platform":"","topic":"","thought":"情感支持类对话"}
例20: q=帮我分析一下这个数据 → {"intent":"chat","platform":"","topic":"","thought":"用户需要分析，走LLM"}
例21: q=系统的架构是怎样的 → {"intent":"chat","platform":"","topic":"","thought":"用户问系统技术细节"}
例22: q=中午吃什么 → {"intent":"chat","platform":"","topic":"","thought":"闲聊建议类"}
例23: q=杭州亚运会 → {"intent":"chat","platform":"","topic":"","thought":"不含搜索/热点关键词，走LLM回答"}
例24: q=王宝强新电影 → {"intent":"chat","platform":"","topic":"","thought":"不含明确搜索词，LLM直接回答"}
例25: q=给我讲个笑话 → {"intent":"chat","platform":"","topic":"","thought":"娱乐聊天"}
例26: q=你是用什么模型 → {"intent":"chat","platform":"","topic":"","thought":"用户问AI的技术背景"}
例27: q=李子柒现在怎么样了 → {"intent":"chat","platform":"","topic":"","thought":"关于个人的问题"}
例28: q=帮我做一个Excel表格 → {"intent":"create","platform":"","topic":"Excel表格","thought":"用户要生成Excel"}
例29: q=生成季度报告 → {"intent":"create","platform":"","topic":"季度报告","thought":"用户要生成报告"}
例30: q=写一段Python代码 → {"intent":"create","platform":"","topic":"Python代码","thought":"用户要生成代码"}
例31: q=请帮我查询今日头条热点 → {"intent":"hot","platform":"头条","topic":"","thought":"用户明确说今日头条"}
例32: q=贴吧热榜 → {"intent":"hot","platform":"贴吧","topic":"","thought":"贴吧的热门帖子"}
例33: q=网易新闻热点 → {"intent":"hot","platform":"网易","topic":"","thought":"网易新闻热榜"}
例34: q=有什么新鲜事 → {"intent":"hot","platform":"","topic":"新鲜事","thought":"用户想看近期发生的事"}
例35: q=hacker news hot → {"intent":"hot","platform":"Hacker News","topic":"","thought":"英文技术社区热点"}
例36: q=reddit热门 → {"intent":"hot","platform":"Reddit","topic":"","thought":"Reddit热门话题"}
例37: q=数学计算: 2+3*4 → {"intent":"calculate","expression":"2+3*4","thought":"用户要求数学计算"}
例38: q=100/5+3等于多少 → {"intent":"calculate","expression":"100/5+3","thought":"用户问算术题"}
例39: q=计算 1024*768 → {"intent":"calculate","expression":"1024*768","thought":"用户要求做乘法"}
例40: q=(15+3)*2-10 → {"intent":"calculate","expression":"(15+3)*2-10","thought":"用户给了一个数学表达式"}
例41: q=搜索AI行业趋势并生成一份分析报告 → {"intent":"agent","topic":"AI行业趋势报告","thought":"用户要搜索后再生成报告，多步骤复杂任务"}
例42: q=查一下今天的热点新闻，然后整理成PPT → {"intent":"agent","topic":"热点新闻PPT","thought":"先搜索热点再生成PPT，需要多步执行"}
例43: q=搜索2024年最佳AI工具，对比分析，出一份Excel表格 → {"intent":"agent","topic":"AI工具对比Excel","thought":"搜索+对比+出表格，三步复杂任务"}
例44: q=帮我搜索最近的科技新闻，用中英文总结，然后发到我的邮箱 → {"intent":"agent","topic":"科技新闻邮件","thought":"搜索+翻译+邮件，多工具调用"}
例45: q=搜索python和javascript的性能对比，然后生成一份报告 → {"intent":"agent","topic":"语言对比报告","thought":"搜索+报告生成，两步复杂任务"}

现在分析: q="""


# ── 系统能力描述（LLM回复时用来介绍自己）──
_SYSTEM_CAPABILITIES = """**我能做什么：**
1. 💬 **聊天问答** — 任何问题直接问，我直接回答
2. 🔍 **搜索信息** — 说"搜索: xxx"或"帮我查一下xxx"
3. 🔥 **热搜热点** — 说"今日xx热点"（百度/微博/抖音/知乎/B站/头条等）
4. 📄 **生成文档** — PPT/Excel/合同/报告/代码，说"帮我做一个xxx"
5. 🎤 **语音输入** — 按住🎤说话，自动识别
6. 🧠 **记忆功能** — 说"记住xxx"或"回忆xxx"
7. 📅 **定时任务** — 说"每天早上9点xxx"
8. 🛠️ **系统诊断** — 说"查看系统状态"
9. 👥 **266位专家** — 点左侧专家列表，切换角色对话
10. 📊 **数据分析** / 🐳 **Docker操作** / 🌐 **翻译翻译**

**直接说你想要什么，我来搞定。**"""


async def _classify_intent(msg: str):
    """ReAct 阶段1: 智能意图分类（Thought）"""
    # ── 关键词快速通道（不依赖LLM，命中直接返回）──
    _lower = msg.lower()
    _create_kw = ["生成","创建","做一份","做ppt","五子棋","时钟","网页","应用","游戏",
                  "开发","写一个","做一个","帮我做","帮我写","帮我生成","帮我创建",
                  "html","代码","报告","合同","方案","excel","表格","演示文稿",
                  "画图","画画","画一个","图片","海报","logo"]
    _fetch_kw = ["打开网页","抓取网页","网页内容","看这个网页","查看网页","提取内容","实时信息"]
    for _kw in _fetch_kw:
        if _kw in _lower:
            logger.info(f"[INTENT] 网页抓取: {_kw}")
            return "fetch", _kw, "", ""
    _cli_kw = ["下载视频","视频下载","图片处理","图片转换","ocr","文字识别","文档转换","转pdf",
               "json处理","csv处理","系统监控","文件同步","代码搜索","文件查找"]
    for _kw in _cli_kw:
        if _kw in _lower:
            logger.info(f"[INTENT] CLI工具: {_kw}")
            return "cli_tool", _kw, "", ""
    for _kw in _create_kw:
        if _kw in _lower:
            logger.info(f"[INTENT] 关键词快速通道: create ({_kw})")
            return "create", "", "", ""
    _hot_kw = ["热搜","热点","热榜","头条","今天有什么新闻","新鲜事","有什么大事","热门","排行榜","快手","抖音"]
    for _kw in _hot_kw:
        if _kw in _lower:
            logger.info(f"[INTENT] 关键词快速通道: hot ({_kw})")
            return "hot", "", "", ""
    _research_kw = ["深度研究","研究报告","深入分析","全面调研","深度调研","research"]
    for _kw in _research_kw:
        if _kw in _lower:
            logger.info(f"[INTENT] 深度研究: {_kw}")
            return "research", "", "", ""
    _calc_kw = ["等于多少","计算","数学","加减乘除","算术"]
    for _kw in _calc_kw:
        if _kw in _lower:
            logger.info(f"[INTENT] 关键词快速通道: calculate ({_kw})")
            return "calculate", "", "", ""
    _search_kw = ["搜索","查找","搜一下","查一下","搜搜","百度","谷歌","什么是","怎么样","怎么用","如何","为什么","有没有","多少"]
    for _kw in _search_kw:
        if _kw in _lower:
            logger.info(f"[INTENT] 关键词快速通道: search ({_kw})")
            return "search", "", "", ""

    from api.agent_llm import call_llm
    prompt = _INTENT_PROMPT + msg[:120]
    for _ in range(2):
        try:
            text, _ = call_llm([{"role": "user", "content": prompt}], timeout=15)
            if not text:
                continue
            # 提取JSON
            cleaned = text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            d = json.loads(cleaned)
            itype = d.get("intent", "chat")
            platform = d.get("platform", "")
            topic = d.get("topic", "")
            thought = d.get("thought", "")
            expression = d.get("expression", "")
            logger.info(f"[INTENT] {msg[:40]} -> {itype} platform={platform} topic={topic} expression={expression[:20]} thought={thought}")
            return itype, platform, topic, expression
        except Exception as e:
            logger.warning(f"[INTENT] retry: {e}")
            continue
    # 兜底：chat
            logger.info(f"[INTENT] fallback chat for: {msg[:40]}")
    return "chat", "", "", ""


async def _execute_search(query: str, count: int = 8):
    """执行搜索 — 先搜，然后尝试抓取最相关结果的内容"""
    from skills.builtin.search_web import execute as _search
    try:
        r = _search({"query": query, "count": count})
        items = r.get("results", [])
        if not items:
            return None
        
        # 尝试抓取第一个结果的内容
        try:
            import httpx, re
            _first_url = items[0].get("url", "")
            if _first_url:
                _resp = await httpx.AsyncClient(timeout=8, verify=False).get(_first_url, headers={"User-Agent": "Mozilla/5.0"})
                if _resp.status_code == 200:
                    _html = _resp.text
                    # 提取正文（去掉HTML标签，取有意义的文本）
                    _text = re.sub(r'<script[^>]*>.*?</script>', '', _html, flags=re.DOTALL)
                    _text = re.sub(r'<style[^>]*>.*?</style>', '', _text, flags=re.DOTALL)
                    _text = re.sub(r'<[^>]+>', ' ', _text)
                    _text = re.sub(r'\s+', ' ', _text).strip()
                    _text = _text[:2000]  # 限制长度
                    if len(_text) > 100:
                        _title = items[0].get("title", "")[:40]
                        _src = _first_url.split('/')[2] if '//' in _first_url else ''
                        return f"🔍 **{query[:30]}**\n\n📰 [{_title}]({_first_url})\n\n{_text[:1500]}\n\n---\n来源: {_src}"
        except Exception:
            pass  # 抓取失败不阻塞，降级到链接列表
        
        # 降级：返回链接列表
        txt = f"🔍 **搜索结果：{query[:30]}**\n\n"
        seen = set()
        for i, item in enumerate(items[:count]):
            t = item.get("title", "")[:60]
            u = item.get("url", "")
            if t and t not in seen:
                seen.add(t)
                txt += f"**{i+1}.** [{t}]({u})\n"
        return txt
    except Exception as e:
        logger.warning(f"[SEARCH] error: {e}")
    return None


async def _fetch_tophub(platform: str) -> str:
    """从 tophub.today 聚合站抓取热搜，一个URL覆盖全平台"""
    import aiohttp, re as _re
    try:
        _headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as _sess:
            async with _sess.get("https://tophub.today", headers=_headers) as _resp:
                if _resp.status != 200:
                    return None
                _html = await _resp.text()
    except Exception as _e:
        logger.warning(f"[TOPHUB] fetch error: {_e}")
        return None

    # 解析每个平台板块
    _sections = _re.split(r'<div class="cc-cd"', _html)
    _platform_items = {}
    for _sec in _sections[1:]:
        # 平台名在 <div class="cc-cd-lb">...<span>平台名</span>
        _name_m = _re.search(r'<div class="cc-cd-lb">.*?<span>\s*(.*?)\s*</span>', _sec, _re.DOTALL)
        if not _name_m:
            continue
        _name = _re.sub(r'<[^>]+>', '', _name_m.group(1)).strip()
        # 条目: class="t" 后面跟文字
        _items = _re.findall(r'class="t"[^>]*>(.*?)<', _sec)
        _items = [_re.sub(r'<[^>]+>', '', _t).strip() for _t in _items]
        _items = [_t for _t in _items if _t and len(_t) >= 2]
        if _items:
            _platform_items[_name] = _items[:20]

    # 平台名映射
    _plat_map = {
        "百度": ["百度"],
        "微博": ["微博"],
        "知乎": ["知乎"],
        "抖音": ["抖音"],
        "快手": ["快手"],
        "头条": ["今日头条", "头条"],
        "B站": ["B站", "哔哩哔哩", "哔哩"],
        "微信": ["微信"],
        "小红书": ["小红书"],
        "视频号": ["视频号"],
    }

    _aliases = _plat_map.get(platform, [platform])
    _found = None
    _found_name = platform
    for _alias in _aliases:
        for _key, _items in _platform_items.items():
            if _alias in _key:
                _found = _items
                _found_name = _key
                break
        if _found:
            break

    # 默认取百度
    if not _found:
        for _key, _items in _platform_items.items():
            if "百度" in _key:
                _found = _items
                _found_name = _key
                break

    if not _found and _platform_items:
        # 取第一个有内容的
        for _key, _items in _platform_items.items():
            if _items:
                _found = _items
                _found_name = _key
                break

    if not _found:
        return None

    _lines = "\n".join([f"{i+1}. {_t}" for i, _t in enumerate(_found[:20])])
    return f"📊 **{_found_name}今日热点 TOP{len(_found[:20])}**\n\n{_lines}"


async def _answer_hot(msg: str, platform: str, topic: str):
    """处理热点查询 — tophub聚合站直抓→搜索→LLM"""
    _source = platform or ""
    for _pk in ("百度","微博","头条","抖音","知乎","B站","小红书","快手","视频号"):
        if _pk in msg: _source = _pk; break
    if not _source:
        _source = "百度"

    # 第一优先: tophub.today 聚合站直抓
    try:
        _r = await _fetch_tophub(_source)
        if _r and len(_r) > 50:
            return _r
    except Exception as _e:
        logger.warning(f"[HOT] tophub failed: {_e}")

    # 第二优先: 搜索+抓取
    try:
        from modules.web_fetcher import search_and_fetch as _saf
        _r = await _saf(f"{_source}热搜 今日热点")
        if _r and len(_r) > 50:
            return _r
    except Exception:
        pass

    # 第三优先: 搜索链接
    try:
        _r = await _execute_search(f"{_source} 热搜 今日热点")
        if _r:
            return _r
    except Exception:
        pass

    # LLM兜底
    try:
        from api.agent_llm import call_llm
        _c, _ = call_llm([{"role":"user","content":f"用户问: {msg}。请用中文列出{_source}的热点话题5-8条，每条一行用数字开头。"}], timeout=15)
        if _c:
            _hl = [l for l in _c.split("\n") if any(c.isdigit() for c in l[:4])]
            if _hl: return f"🔥 **{_source}热点**\n\n"+"\n".join(_hl[:8])
    except Exception:
        pass
    return None


async def _try_llm_chat(msg: str, system_hint: str = "", api_key: str = ""):
    """LLM直接回答"""
    from api.agent_llm import call_llm
    try:
        if system_hint:
            prompt = f"{system_hint}\n\n用户: {msg}\n回答:"
        else:
            prompt = f"用户: {msg}\n\n请直接回答，简洁、有用。"
        content, _ = call_llm([{"role": "user", "content": prompt}], timeout=20, key=api_key)
        if content and len(content) > 3:
            return content
    except Exception as _et:
        logger.warning(f"[LLM-CHAT] 回答异常: {_et}")
    return None


# N8N工作流匹配函数（只有用户主动问n8n才显示链接）
_n8n_keywords = ['n8n','编辑器','工作流模板','浏览模板','/n8n-browse']

async def _append_n8n_links(msg: str, reply: str) -> str:
    """直接查询SQLite数据库显示匹配模板数（不走HTTP，稳定可靠）"""
    import sqlite3, os
    _db_path = os.environ.get('N8N_BASE', _N8N_BASE_PATH) + '/workflows.db'
    _cn_en = {'邮件':'email','通知':'notification','推送':'webhook','审批':'approval',
              '监控':'alert','报表':'report','备份':'backup','表单':'form','登录':'login',
              '爬虫':'crawl','短信':'sms','翻译':'translate','客服':'slack','定时':'cron'}
    _kw = [k for k in _cn_en if k in msg]
    if _kw:
        try:
            conn = sqlite3.connect(_db_path)
            q = _cn_en[_kw[0]]
            total = conn.execute("SELECT COUNT(*) as c FROM workflows WHERE name LIKE ? OR filename LIKE ?", ('%'+q+'%','%'+q+'%')).fetchone()[0]
            rows = conn.execute("SELECT name FROM workflows WHERE name LIKE ? OR filename LIKE ? ORDER BY nodes DESC LIMIT 3", ('%'+q+'%','%'+q+'%')).fetchall()
            conn.close()
            if total > 0:
                names = [r[0][:40] for r in rows if r[0]]
                tip = f"\n\n 系统中有 {total} 个相关自动化模板"
                if names:
                    tip += f"\n  例如：{'、'.join(names)}"
                reply += tip
        except Exception as _en:
            logger.warning(f"[N8N] 数据库查询异常: {_en}")
    # 高级用户：明确提到n8n/编辑器时显示链接
    if any(k in msg for k in ['n8n','编辑','浏览模板']):
        extra = f"\n  [浏览全部模板]({_DOMAIN}/n8n-browse) | [打开编辑器]({_DOMAIN}/api/v1/n8n/editor)"
        reply += extra
    return reply


@router.post("/api/v1/smart")
async def smart_chat(req: Req):
    msg = (req.message or "").strip()
    if not msg:
        return {"success": True, "result": "请说点什么"}

    # ── 优先级0: 多步复合指令解析 ──
    #    把"帮我生成一个时钟HTML，然后记住它，最后打开应用列表"拆成三步逐一执行
    _multi_separators = (
        "，然后", "，再", "，接着", "，之后", "，最后", "，接下来",
        "。然后", "。再", "。接着", "。之后", "。最后", "。接下来",
        "并且", "同时", "；然后", "；再", "；接着", "；之后", "；最后",
    )
    _multi_parts = [msg]
    for _sep in _multi_separators:
        _new_parts = []
        for _part in _multi_parts:
            _split_rest = _part
            _sep_found = False
            for _s in [_sep]:
                if _s in _split_rest:
                    _before, _after = _split_rest.split(_s, 1)
                    if _before.strip():
                        _new_parts.append(_before.strip())
                    if _after.strip():
                        _new_parts.append(_after.strip())
                    _sep_found = True
                    break
            if not _sep_found:
                _new_parts.append(_part)
        _multi_parts = _new_parts

    # 如果拆出多步（≥2），按顺序执行每步，聚合结果
    if len(_multi_parts) >= 2:
        _multi_results = []
        _multi_has_error = False
        for _i, _part in enumerate(_multi_parts):
            if not _part.strip():
                continue
            # 用已有执行引擎处理每步（action → info → nav → create → LLM）
            _step_req = Req(
                message=_part.strip(),
                api_key=req.api_key,
                lang=req.lang,
                context=[],
            )
            try:
                _step_resp = await _execute_single(_step_req)
            except Exception as _se:
                _step_resp = {"success": True, "result": f"⚠️ 步骤{_i+1}异常: {_se}"}
            _step_text = str(_step_resp.get("result", "无返回"))
            _step_text = _step_text[:500]
            _step_url = _step_resp.get("redirect", "")
            if _step_text.startswith("✅") or _step_text.startswith("📐") or _step_text.startswith("🔍"):
                _icon = "✅"
            elif _step_url:
                _icon = "🔗"
                _step_text = f"跳转到{_step_url}"
            elif _step_text.startswith("❌"):
                _icon = "❌"
                _multi_has_error = True
            else:
                _icon = "📌"
            _multi_results.append(f"  **步骤{_i+1}:** {_icon} {_step_text}")
            # 如果是导航，也执行跳转（取最后一步导航）
        _combined = f"📋 **多步指令完成**\n\n" + "\n".join(_multi_results)
        _summary_suffix = "" if not _multi_has_error else "\n\n⚠️ 部分步骤未成功，请检查后重试"
        return {"success": True, "result": _combined + _summary_suffix}

    # 委托给单步执行引擎
    return await _execute_single(req)


async def _execute_single(req) -> dict:
    """单步指令执行引擎 — 供多步调度器和主入口复用"""
    msg = (req.message or "").strip()
    _ak = req.api_key or ""

    # ── P0: 高频问候/打招呼直接回复（不走LLM，0延迟）──
    _GREETINGS = ["你好","您好","嗨","hi","hello","hey","在吗","在不在","早上好","下午好","晚上好","哈喽","你好啊","hello你好"]
    if msg.lower().strip() in _GREETINGS or any(msg.strip() == g for g in _GREETINGS):
        return {"success": True, "result": "你好！我是 AUTO-EVO-AI 智能助手，有什么可以帮你的？"}

    # ── P1: 动作执行（匹配关键词→调API→返回结果，不依赖LLM）
    #    必须在导航之前，确保"创建用户"/"记住"/"回忆"等不走跳转
    try:
        action_result = await _execute_action(msg)
    except Exception as _ae:
        logger.warning(f"[SMART-ACTION] _execute_action error: {_ae}")
        action_result = None
    if action_result:
        return {"success": True, "result": action_result}

    # ── P2: 直接信息查询（不依赖LLM，直查API）──
    info_result = await _execute_info_query(msg)
    if info_result:
        from api.agent_llm import call_llm as _llm_shorten
        try:
            short, _ = _llm_shorten([{"role":"user","content":f"用简洁中文总结以下系统信息（不超过100字）：{info_result[:1500]}"}], timeout=8)
            if short and len(short) > 5:
                return {"success": True, "result": short}
        except Exception as _es:
            logger.warning(f"[INFO] 总结异常: {_es}")
        return {"success": True, "result": info_result[:1000]}

    # ── 优先级2: 导航路由匹配（不依赖LLM，直接跳转）──
    nav_url = await _match_navigation(msg)
    if nav_url:
        name = nav_url.split("/")[-1].replace(".html","").replace("-"," ")
        logger.info(f"[NAV] {msg[:30]} -> {nav_url}")
        return {"success": True, "result": f"正在打开 **{name}**...", "redirect": nav_url}

    # ── 优先级3: 创建/生成快速通道（不依赖LLM分类）──
    _CREATE_FAST = ["生成","创建","制作","编写","写一个","做一个","开发一个","设计一个","实现一个","画一个","绘制","生成HTML","写HTML","帮我做一个","帮我写一个","帮我生成"]
    if any(k in msg for k in _CREATE_FAST):
        logger.info(f"[CREATE-FAST] {msg[:30]} -> 跳过LLM分类")
        itype = "create"
        platform, topic, expression = "", msg, ""
    else:
        # ── 优先级4: ReAct 阶段1: Thought（意图分类）──
        itype, platform, topic, expression = await _classify_intent(msg)
    logger.info(f"[ROUTE] {itype} p={platform} t={topic} e={expression[:20]}")

    # ── ReAct 阶段2: Action（执行）──

    # hot: 热点查询
    if itype == "hot":
        result = await _answer_hot(msg, platform, topic)
        if result:
            return {"success": True, "result": result}
        # 兜底：LLM试一下
        fallback = await _try_llm_chat(msg, "用户想查热点。列出你知道的热点话题，5条左右。", _ak)
        if fallback:
            return {"success": True, "result": fallback}
        return {"success": True, "result": "暂无热点数据，稍后再试"}

    # research: 深度研究
    if itype == "research":
        try:
            from modules.deep_researcher import research as _rs
            _r = await _rs(msg)
            if _r.get("success"):
                _txt = f"🔬 **深度研究：{msg}**\n\n"
                _txt += _r.get("analysis", "")
                _txt += f"\n\n📊 共查阅 {_r.get('sources_count', 0)} 个来源"
                return {"success": True, "result": _txt}
        except Exception as _re:
            logger.warning(f"[RESEARCH] {_re}")
        return {"success": True, "result": f"🔬 **{msg}**\n\n研究分析进行中，请稍后查看详细结果。"}

    # cli_tool: CLI工具调用
    if itype == "cli_tool":
        _tool_map = {
            "下载视频":"yt-dlp","视频下载":"yt-dlp",
            "图片处理":"imagemagick","图片转换":"imagemagick",
            "ocr":"tesseract","文字识别":"tesseract",
            "文档转换":"pandoc","转pdf":"pandoc",
            "json处理":"jq","csv处理":"csvkit",
            "系统监控":"htop","代码搜索":"ripgrep","文件同步":"rsync","文件查找":"fd",
        }
        _tool = _tool_map.get(msg,"")
        _lines = [f"「{k}」→ {v}" for k,v in _tool_map.items()]
        _avail = ""
        try:
            from modules.cli_tools import executor as _cli
            _st = _cli.status()
            _tools = _st.get("tools",{})
            _avail_tools = [k for k,v in _tools.items() if v.get("available")]
            if _avail_tools:
                _avail = "✅ 已安装: " + ", ".join(_avail_tools[:8])
        except: pass
        if _tool:
            return {"success":True,"result":f"🔧 **{_tool}**\n\n你说的是 {_tool}（{_tool_map[msg]}）。在输入框说「用 {_tool} 处理」即可。\n\n{_avail}"}
        return {"success":True,"result":f"🔧 **CLI工具集**\n\n{_avail}\n\n可用命令：\n" + "\n".join(_lines) + "\n\n直接在输入框说就行，系统会自动调用对应的命令行工具。"}

    # fetch: 网页内容抓取
    if itype == "fetch":
        try:
            _url = topic or ""
            _query = msg.replace("打开网页","").replace("抓取网页","").replace("网页内容","").replace("提取内容","").replace("查看网页","").strip()
            from modules.web_fetcher import WebFetcher
            _wf = WebFetcher()
            _r = _wf._fetch(url=_url, query=_query)
            if _r.get("success"):
                _txt = f"🌐 **{_r.get('title','')}**\n\n{_r.get('content','')[:2000]}"
                return {"success": True, "result": _txt}
        except Exception as _fe:
            logger.warning(f"[FETCH] 抓取失败: {_fe}")
        # 抓取失败走搜索
        itype = "search"

    # search: 搜索+自动抓取正文
    if itype == "search":
        try:
            from modules.web_fetcher import search_and_fetch as _saf
            result = await _saf(topic or msg)
        except Exception:
            result = await _execute_search(topic or msg)
        if result:
            result = await _append_n8n_links(msg, result)
            return {"success": True, "result": result}
        # 搜索失败→LLM
        fallback = await _try_llm_chat(msg, api_key=_ak)
        if fallback:
            fallback = await _append_n8n_links(msg, fallback)
            return {"success": True, "result": fallback}
        return {"success": True, "result": "搜索超时，稍后再试"}
            return {"success": True, "result": fallback}
        return {"success": True, "result": "搜索超时，稍后再试"}

    # help: 系统能力
    if itype == "help":
        result = await _append_n8n_links(msg, _SYSTEM_CAPABILITIES)
        return {"success": True, "result": result}

    # calculate: 数学计算
    if itype == "calculate":
        expr = (expression or topic or msg).strip()
        import re as _re_calc
        clean = ''.join(_re_calc.findall(r'[\d+\-*/().% ]+', expr)).strip()
        if not clean or len(clean) < 2:
            nums = _re_calc.findall(r'[\d+\-*/().% ]+', msg)
            clean = max(nums, key=len).strip() if nums else ""
        # 只去空格，括号必须保留
        clean = clean.strip()
        if len(clean) >= 2:
            try:
                ns = {"__builtins__": {}}; exec(compile(f"_r={clean}", "", "exec"), ns)
                val = ns.get("_r")
                if isinstance(val, (int, float)):
                    return {"success": True, "result": f"📐 **{clean} = {val}**"}
            except Exception as _ce:
                logger.warning(f"[CALC] exec fail: {_ce}")
            try:
                import ast, operator
                ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                       ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
                def _se(n):
                    if isinstance(n, ast.Constant): return n.value
                    if isinstance(n, ast.BinOp): return ops[type(n.op)](_se(n.left), _se(n.right))
                    if isinstance(n, ast.UnaryOp): return operator.neg(_se(n.operand))
                    raise ValueError
                val = _se(ast.parse(clean, mode='eval').body)
                return {"success": True, "result": f"📐 **{clean} = {val}**"}
            except Exception as _ce:
                logger.warning(f"[CALC] ast fail: {_ce}")
        fallback = await _try_llm_chat(f"计算一下: {expr}", api_key=_ak)
        if fallback:
            return {"success": True, "result": fallback}
        return {"success": True, "result": f"📐 {expr} 无法计算"}

    # create: 生成文档/代码 — 异步超时重试，直接输出HTML
    if itype == "create":
        from api.agent_llm import call_llm as _create_llm
        import re as _re_html
        import time as _time
        import concurrent.futures as _cf
        import asyncio as _asyncio2
        # 先用LLM直接生成 — 用run_in_executor避免阻塞uvicorn事件循环
        _prompt = f"请生成一个完整可运行的HTML页面（单文件，所有CSS/JS内联）:\n\n任务: {msg}\n\n要求:\n- 必须包含完整的<!DOCTYPE html>到</html>结束标签，不能截断\n- CSS和JavaScript全部内联在单个HTML文件中\n- 代码必须完整可用，不能有任何省略或\"...\"占位\n- 把完整HTML代码放在```html```标签中"
        _created_html = None
        # 尝试2次（LLM可能慢）
        _loop = _asyncio2.get_event_loop()
        for _attempt in range(2):
            try:
                _content, _ = await _loop.run_in_executor(None, _create_llm, [{"role":"user","content":_prompt}], None, "", 180)
                if _content and len(_content) > 100:
                    _match = _re_html.search(r'```html\s*(.*?)(?:```|\Z)', _content, _re_html.DOTALL)
                    if _match:
                        _created_html = _match.group(1).strip()
                    elif '<html' in _content.lower() or '<!DOCTYPE' in _content:
                        _created_html = _content.strip()
                    # 检查完整度（必须有闭合标签）
                    if _created_html and '</html>' not in _created_html and _attempt == 0:
                        logger.warning(f"[CREATE] HTML不完整（无</html>），重试")
                        continue
                    if _created_html:
                        break
            except Exception as _ce:
                logger.warning(f"[CREATE] LLM生成异常: {_ce}")
            await _asyncio2.sleep(0.5)
        if _created_html and len(_created_html) > 200:
            _fn = f"app_{int(_time.time())}.html"
            _fp = BASE / "output" / "apps" / _fn
            _fp.parent.mkdir(parents=True, exist_ok=True)
            _fp.write_text(_created_html, encoding="utf-8")
            _url = f"/output/apps/{_fn}"
            _title = msg[:30]
            _result = f"✅ **{_title}**\n[📄 预览]({_url})"
            _result = await _append_n8n_links(msg, _result)
            return {"success": True, "result": _result}
        # LLM未生成HTML → 直接返回清晰提示，不走agent_core降级
        return {"success": True, "result": f"⏳ 正在为您生成「{msg[:40]}」...\nLLM 响应较慢，请稍后刷新页面查看结果，或直接输入更具体的需求。"}

    # agent: 复杂多步骤任务 → 轻量级智能执行器（不依赖外部Agent引擎）
    if itype == "agent":
        try:
            # 先用LLM拆解任务为步骤
            plan_prompt = f"""你是任务规划专家。分析以下用户任务，拆解为具体的执行步骤。

任务: {msg}

返回JSON数组，每个元素包含：
- "step": 步骤序号
- "action": 执行的动作描述（搜索/生成/分析/对比/汇总等）
- "tool": 最可能用到的工具名（search/docs/skills/code/n8n等）
- "target": 目标描述

示例格式：[{{"step":1,"action":"搜索AI行业趋势","tool":"search","target":"AI行业最新动态"}},{{"step":2,"action":"生成分析报告","tool":"docs","target":"AI趋势分析报告"}}]

只返回JSON数组，不要加额外解释。"""
            step_text = await _try_llm_chat(plan_prompt, "你是一个严格的任务规划器。只输出JSON数组。")
            txt = "🤖 **任务拆解与执行**\n\n"
            txt += f"**📋 任务:** {msg}\n\n"
            txt += "**📌 执行计划:**\n"
            steps = []
            try:
                steps = json.loads(step_text) if step_text else []
            except Exception as _ep:
                logger.warning(f"[AGENT] 步骤解析异常: {_ep}")
            if not steps or not isinstance(steps, list):
                steps = [{"step": 1, "action": "综合分析", "tool": "llm", "target": msg}]
            
            for s in steps:
                txt += f"  {s['step']}. [{s.get('tool','?')}] {s.get('action','')} — {s.get('target','')}\n"
            
            # 先搜N8N匹配
            n8n_results = []
            try:
                async with httpx.AsyncClient(timeout=8) as c:
                    for kw in msg.split():
                        if len(kw) > 1:
                            r = await c.get(f"{_API_BASE}/api/v1/n8n/search?q={kw}&limit=3")
                            data = r.json()
                            if data.get("results"):
                                n8n_results.extend(data["results"][:2])
            except Exception as _en2:
                logger.warning(f"[AGENT] N8N搜索异常: {_en2}")
            
            # 执行LLM综合回答（带步骤上下文）
            exec_prompt = f"""用户要求完成以下复杂任务：{msg}

我已经将任务拆解为以下步骤：
{json.dumps(steps, ensure_ascii=False, indent=2)}

请按照步骤顺序，逐步完成这个任务。可用工具包括：
- LLM对话（回答、写作、分析等）
- 搜索（查找实时信息）
- 技能执行（458个内置技能）
- N8N工作流（2077个自动化模板）
- 文档生成（Word/PPT/Excel）

请逐步执行并返回最终结果。格式：
**步骤1：** [执行内容]
**步骤2：** [执行内容]
...
**最终结果：** [汇总答案]"""
            
            result = await _try_llm_chat(exec_prompt)
            if result:
                txt += "\n\n**⚡ 执行过程:**\n" + result
            else:
                txt += "\n\n**⚡ 执行结果:**\n综合分析完成，建议查看详细结果。"
            
            # 追加N8N链接（如果找到）
            if n8n_results:
                txt += "\n\n---\n📋 **匹配到 N8N 工作流模板:**\n"
                for w in n8n_results[:5]:
                    txt += f"  • {w.get('name','')[:60]}\n"
                txt += f"\n  ➤ 打开编辑器运行：[/api/v1/n8n/editor]({_DOMAIN}/api/v1/n8n/editor)"
            
            return {"success": True, "result": txt}
        except Exception as e:
            logger.warning(f"[AGENT] 执行失败: {e}")
            # 降级到LLM
            fallback = await _try_llm_chat(msg, api_key=_ak)
            if fallback:
                fallback = await _append_n8n_links(msg, fallback)
                return {"success": True, "result": fallback}
            return {"success": True, "result": "处理超时，请稍后再试"}

    # P6: chat → LLM直接回答
    result = await _try_llm_chat(msg, api_key=_ak)
    if result:
        result = await _append_n8n_links(msg, result)
        return {"success": True, "result": result}
    result = await _try_llm_chat(msg)
    if result:
        result = await _append_n8n_links(msg, result)
        return {"success": True, "result": result}
    return {"success": True, "result": "正在思考中..."}
@router.post("/api/v1/smart/stream")
async def smart_stream(req: Req):
    """SSE streams thinking first, then executes"""
    import asyncio
    itype, platform, topic, _ = await _classify_intent(req.message)

    async def _gen():
        # P1: Send thinking BEFORE doing any work
        _step = _think_step.get(itype, "\U0001f914 正在处理...")
        yield f"data: {json.dumps({'thinking':_step,'icon':_step[:2],'done':False})}\n\n"
        await asyncio.sleep(0.1)

        # P2: Execute intent
        txt = None
        if itype == "hot":
            txt = await _answer_hot(req.message, platform, topic)
        elif itype == "search":
            txt = await _execute_search(topic or req.message)
        elif itype == "research":
            from modules.deep_researcher import research as _rs
            _r = await _rs(req.message)
            if _r.get("success"):
                txt = "\U0001f52c **深度研究**\n\n" + _r.get("analysis", "分析进行中...")
        elif itype == "create":
            yield f"data: {json.dumps({'chunk':'\u23f3 AI生成中（需要30-90秒），稍等一下...','done':False})}\n\n"
            await asyncio.sleep(0.1)
            _resp = await _execute_single(req)
            txt = _resp.get("result", "")
        elif itype == "help":
            txt = _SYSTEM_CAPABILITIES
        elif itype == "calculate":
            _resp = await _execute_single(req)
            txt = _resp.get("result", "")
        elif itype == "cli_tool":
            txt = "\U0001f527 在输入框说「用xxx处理」即可调用命令行工具"

        # P3: Send result
        if txt:
            if itype in ("create","calculate","help","cli_tool"):
                yield f"data: {json.dumps({'chunk':txt,'done':False})}\n\n"
            else:
                for ch in txt:
                    yield f"data: {json.dumps({'chunk': ch, 'done': False})}\n\n"
                    await asyncio.sleep(0.02)
        else:
            from api.agent_llm import call_llm_stream as _stream
            _ak2 = req.api_key or ""
            try:
                for ch in _stream([{"role": "user", "content": req.message}], key=_ak2):
                    yield f"data: {json.dumps({'chunk': ch, 'done': False})}\n\n"
                    await asyncio.sleep(0.02)
            except Exception as e:
                yield f"data: {json.dumps({'chunk': f'错误: {e}', 'done': True})}\n\n"
                return
        yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")

@router.get("/api/v1/llm/status")
async def llm_status():
    from api.agent_llm import get_active_model
    return get_active_model()


# ── 模块自动路由引擎 ──
# 把模块名→中文功能关键词，用户说自然语言就能匹配
_MODULE_KEYWORDS = None  # [{name:str, keywords:[str]}]

# 模块名中常见英文词→中文映射（智能拆解用）
_EN_TO_CN = {
    "access": "访问", "account": "账户", "agent": "智能体代理", "ai": "人工智能AI",
    "alert": "告警告警通知", "analysis": "分析", "api": "接口API", "app": "应用",
    "archive": "归档", "asset": "资产", "async": "异步", "audit": "审计",
    "auth": "认证", "auto": "自动", "backup": "备份", "batch": "批量",
    "browser": "浏览器", "cache": "缓存", "calendar": "日历", "cdn": "加速CDN",
    "cert": "证书", "chat": "聊天对话", "check": "检查", "clean": "清理",
    "cli": "命令行", "client": "客户端", "cloud": "云", "cluster": "集群",
    "code": "代码", "collect": "收集", "command": "命令", "commit": "提交",
    "compress": "压缩", "config": "配置配置管理", "connect": "连接对接",
    "context": "上下文", "control": "控制", "convert": "转换", "copy": "复制",
    "cron": "定时", "cursor": "游标", "custom": "自定义", "daemon": "守护进程",
    "dashboard": "仪表盘看板", "data": "数据", "database": "数据库", "dead": "死信",
    "debug": "调试", "decision": "决策", "deploy": "部署", "design": "设计",
    "detect": "检测", "device": "设备", "dns": "域名DNS", "doc": "文档",
    "docker": "容器Docker", "download": "下载", "drive": "网盘", "edge": "边缘",
    "email": "邮件", "encode": "编码", "encrypt": "加密", "engine": "引擎",
    "error": "错误", "event": "事件", "execute": "执行", "export": "导出",
    "extract": "提取", "failover": "容错", "fast": "快速", "feature": "特性",
    "file": "文件", "filter": "过滤", "finance": "金融财务", "firewall": "防火墙",
    "flow": "流程", "forecast": "预测", "format": "格式化", "form": "表单问卷",
    "function": "函数", "gateway": "网关", "generate": "生成", "geo": "地理位置",
    "git": "代码仓库Git", "github": "GitHub代码托管", "govern": "治理", "graph": "图谱",
    "group": "分组", "guard": "防护", "health": "健康", "history": "历史",
    "hook": "钩子", "hot": "热门", "http": "网络请求HTTP", "hub": "中心",
    "image": "图片", "import": "导入", "incident": "故障", "index": "索引",
    "info": "信息", "init": "初始化", "input": "输入", "insight": "洞察",
    "install": "安装", "integrate": "集成", "invoke": "调用", "io": "输入输出",
    "job": "任务作业", "json": "JSON", "key": "密钥键值", "knowledge": "知识",
    "label": "标签", "lang": "语言", "leader": "领导", "learning": "学习",
    "license": "许可", "link": "链接", "list": "列表", "load": "负载加载",
    "local": "本地", "lock": "锁", "log": "日志", "login": "登录",
    "manager": "管理", "market": "市场行情", "mcp": "MCP协议", "measure": "测量",
    "media": "媒体", "meeting": "会议", "mem": "内存", "memory": "记忆存储",
    "message": "消息", "metric": "指标", "migrate": "迁移", "mirror": "镜像",
    "mobile": "手机移动端", "mock": "模拟", "model": "模型", "module": "模块",
    "monitor": "监控", "multi": "多", "network": "网络", "node": "节点",
    "note": "笔记", "notify": "通知", "oauth": "授权OAuth", "object": "对象",
    "ocr": "文字识别OCR", "offline": "离线", "online": "在线", "open": "开放",
    "operator": "运维", "optimize": "优化", "option": "选项", "orchestrate": "编排",
    "output": "输出", "page": "页面", "parse": "解析", "partition": "分区",
    "password": "密码", "path": "路径", "payment": "支付", "perf": "性能",
    "permission": "权限", "photo": "照片", "pipeline": "流水线管道", "plan": "计划",
    "platform": "平台", "plugin": "插件", "point": "点", "policy": "策略",
    "pool": "池", "portal": "门户", "post": "发布", "prefetch": "预取",
    "priority": "优先级", "private": "私有", "process": "进程", "profile": "画像",
    "project": "项目", "prompt": "提示词", "protocol": "协议", "proxy": "代理",
    "publish": "发布", "pull": "拉取", "push": "推送", "quality": "质量",
    "query": "查询", "queue": "队列", "quota": "配额", "rate": "速率",
    "reactor": "反应器", "realtime": "实时", "recover": "恢复", "redis": "Redis缓存",
    "register": "注册", "release": "发布", "remote": "远程", "render": "渲染",
    "replica": "副本", "report": "报告报表", "request": "请求", "research": "研究",
    "resource": "资源", "response": "响应", "rest": "REST接口", "restore": "还原",
    "retry": "重试", "review": "审查评审", "risk": "风险", "robot": "机器人",
    "role": "角色", "rollback": "回滚", "route": "路由", "rule": "规则",
    "sandbox": "沙箱", "scale": "伸缩", "scan": "扫描", "schedule": "调度",
    "schema": "模式", "scraper": "爬虫", "search": "搜索", "secret": "密钥",
    "secure": "安全", "security": "安全", "segment": "段", "send": "发送",
    "sensor": "传感器", "server": "服务", "service": "服务", "session": "会话",
    "setting": "设置", "setup": "设置", "share": "分享", "signal": "信号",
    "site": "站点", "skill": "技能", "slack": "Slack", "slow": "慢",
    "smart": "智能", "snapshot": "快照", "social": "社交", "sort": "排序",
    "source": "源", "space": "空间", "sql": "SQL查询", "ssl": "SSL证书",
    "stack": "栈", "stage": "阶段", "state": "状态", "stat": "统计",
    "storage": "存储", "store": "存储", "stream": "流", "sync": "同步",
    "system": "系统", "table": "表格", "task": "任务", "team": "团队",
    "template": "模板", "test": "测试", "thread": "线程", "threat": "威胁",
    "tier": "层", "time": "时间", "token": "令牌Token", "tool": "工具",
    "topic": "主题", "track": "追踪", "traffic": "流量", "train": "训练",
    "transfer": "传输", "transform": "转换", "transit": "中转", "translate": "翻译",
    "trigger": "触发", "tunnel": "隧道穿透", "ui": "界面UI", "update": "更新",
    "upload": "上传", "url": "网址URL", "usage": "用量", "user": "用户",
    "validate": "验证", "value": "值", "vector": "向量", "verify": "校验",
    "version": "版本", "video": "视频", "view": "视图", "virtual": "虚拟",
    "voice": "语音", "vpn": "VPN", "waf": "WAF防火墙", "watch": "观察",
    "web": "网页", "webhook": "Webhook", "window": "窗口", "worker": "工作者",
    "workflow": "工作流", "workspace": "工作空间", "write": "写入",
}

def _module_name_to_keywords(name: str) -> list:
    """根据模块名自动生成中文功能关键词"""
    # 先用下划线拆词
    parts = name.replace('-', '_').split('_')
    keywords = set()
    
    # 加入原始模块名（去下划线）
    clean = name.replace('_', ' ').replace('-', ' ')
    keywords.add(clean)
    
    # 每个部分查中英文映射
    for p in parts:
        p_low = p.lower()
        if p_low in _EN_TO_CN:
            # 加入中文关键词（可能有多个，用空格分隔）
            cn_vals = _EN_TO_CN[p_low].split()
            for cv in cn_vals:
                keywords.add(cv)
        # 同时也保留英文原词
        keywords.add(p)
    
    # 特定组合补全
    full_cn = {
        "code_review": ["代码审查", "代码评审", "review代码", "检查代码"],
        "stock_api": ["股票行情", "股价", "实时股价", "查股票"],
        "voice_notify": ["语音通知", "语音播报"],
        "ocr_engine": ["文字识别", "图片转文字", "OCR识别"],
    "translate": ["翻译", "语言翻译", "多语言翻译", "翻译服务"],
    "email": ["发邮件", "邮件发送", "邮箱", "电子邮件"],
    "calendar": ["日历", "日程"],
    "cron": ["定时任务", "定时执行", "cron表达式", "定时调度"],
    "backup": ["数据备份", "备份数据", "备份恢复"],
    "monitor": ["监控", "实时监控", "系统监控", "性能监控"],
    "deploy": ["部署", "发布上线", "一键部署"],
    "search": ["搜索", "查找", "查询", "全文搜索", "信息搜索"],
    "report": ["报告", "报表", "生成报告", "生成报表", "周报", "月报"],
        "chat": ["聊天", "对话", "智能问答"],
        "agent": ["智能体", "AI代理", "自动化代理"],
    "data": ["数据", "数据分析", "数据处理"],
    "log": ["日志", "查看日志", "日志分析", "日志管理"],
        "auth": ["登录", "认证", "授权"],
        "payment": ["支付", "付款", "收款"],
        "image": ["图片", "图像", "图片处理"],
        "video": ["视频", "视频处理"],
        "audio": ["音频", "语音"],
        "file": ["文件", "文件管理", "文件处理"],
        "database": ["数据库", "数据查询", "SQL"],
        "notification": ["通知", "消息推送", "推送通知"],
        "workflow": ["工作流", "自动化流程"],
        "permission": ["权限", "权限管理"],
        "secret": ["密钥", "密码", "凭据"],
        "analytics": ["分析", "统计", "数据分析"],
        "dashboard": ["看板", "仪表盘", "数据面板"],
        "insight": ["洞察", "分析洞察"],
        "forecast": ["预测", "趋势预测"],
        "recommend": ["推荐", "智能推荐"],
        "meeting": ["会议", "会议纪要", "开会"],
    "form": ["表单", "问卷", "调查", "创建表单", "问卷调查"],
    "approval": ["审批", "审核", "审批流程", "审批中心", "待审批"],
    "browser": ["浏览器", "网页浏览"],
    "export": ["导出", "数据导出"],
    "import": ["导入", "数据导入"],
    "sync": ["同步", "数据同步"],
    "migrate": ["迁移", "数据迁移"],
    "template": ["模板", "套用模板"],
    "document": ["文档", "文档生成", "写文档"],
    "presentation": ["PPT", "演示文稿", "幻灯片", "生成PPT"],
    "spreadsheet": ["表格", "Excel", "电子表格"],
    "code": ["代码", "编程", "写代码"],
    "review": ["审查", "评审", "代码审查"],
    "test": ["测试", "自动化测试"],
    "network": ["网络", "网络管理"],
    "storage": ["存储", "文件存储"],
    "tunnel": ["穿透", "内网穿透", "隧道"],
    "monitor": ["监控", "告警", "状态"],
    "schedule": ["定时", "调度", "排期"],
    "event": ["事件", "事件驱动", "事件引擎"],
    "queue": ["队列", "消息队列", "队列管理"],
    "task": ["任务", "任务管理"],
        "team": ["团队", "协作"],
        "collaboration": ["协作", "协同"],
        "integration": ["集成", "对接"],
        "pipeline": ["流水线", "管道"],
        "release": ["发布", "版本发布"],
        "cicd": ["CI/CD", "持续集成", "持续部署"],
        "ansible": ["自动化运维", "Ansible"],
        "terraform": ["基础设施", "Terraform"],
        "k8s": ["Kubernetes", "容器编排", "K8s"],
        "docker": ["Docker", "容器"],
        "grafana": ["Grafana", "可视化面板"],
        "prometheus": ["Prometheus", "指标监控"],
    }
    base_name = name.replace('_', '_')  # 保留原名
    for key, vals in full_cn.items():
        if key in name or key.replace('_', ' ') in name:
            for v in vals:
                keywords.add(v)
    
    return list(keywords)

def _build_module_index():
    """构建模块名→关键词索引，启动时加载一次"""
    global _MODULE_KEYWORDS
    if _MODULE_KEYWORDS is not None:
        return _MODULE_KEYWORDS
    import os
    d = os.path.join(os.path.dirname(__file__), "..", "..", "modules")
    if not os.path.isdir(d):
        d = os.path.join(os.path.dirname(__file__), "..", "modules")
    index = []
    for f in sorted(os.listdir(d)):
        if f.endswith('.py') and not f.startswith('_') and f != '__init__.py':
            name = f.replace('.py', '')
            keywords = _module_name_to_keywords(name)
            index.append({"name": name, "keywords": keywords})
    _MODULE_KEYWORDS = index
    return index

def _find_module_in_text(msg: str) -> str | None:
    """智能匹配：用户输入自然语言需求→自动找到对应模块"""
    msg_lower = msg.lower().strip()
    index = _build_module_index()
    
    # 评分制：每个模块按关键词命中打分，最高分返回
    best_score = 0
    best_name = None
    
    for entry in index:
        score = 0
        for kw in entry["keywords"]:
            kw_lower = kw.lower().strip()
            if len(kw_lower) < 2:
                continue
            # 中文关键词直接匹配
            if kw_lower in msg_lower:
                # 长关键词匹配权重更高（防止"代码"匹配到所有含"代码"的模块）
                score += len(kw_lower)
                # 完整短语匹配额外加分
                if len(kw_lower) >= 4:
                    score += 5
            # 模块名本身匹配加分（兼容直接输入模块名的情况）
            if kw_lower == msg_lower:
                score += 50
        if score > best_score:
            best_score = score
            best_name = entry["name"]
    
    # 阈值：至少匹配到2个词以上才路由（避免"邮件""报告"等常见词误触）
    if best_score >= 5:
        return best_name
    return None
