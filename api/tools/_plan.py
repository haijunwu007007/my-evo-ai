"""提取 agent_tools.py 中各节代码并写出到 api/tools/*.py"""
import re, os, sys

SCRIPT = os.environ.get("EVO_AGENT_TOOLS") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent_tools.py")
OUT = os.environ.get("EVO_TOOLS_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

with open(SCRIPT, encoding="utf-8") as f:
    text = f.read()

# Remove header (docstring + imports) — they go into registry/__init__
header = text[:text.index("# ── 🌐 浏览器自动化")]

# Split by section headers
pattern = r'(# ── .+? ──+\n)(.*?)(?=\n# ── |\n# ════════════════|\Z)'
sections = re.findall(pattern, text, re.DOTALL)

for header_line, body in sections:
    # Extract section name and category
    name_match = re.search(r'# ── ([^─]+) ──', header_line)
    if not name_match:
        continue
    section_name = name_match.group(1).strip()

    # Determine target file
    section_lower = section_name.lower()
    if section_lower in ("浏览器自动化", "ai智能爬虫", "搜索内容"):
        target = "browser"
    elif section_lower in ("自主研究", "ai工具", "多智能体", "语音合成", "视频脚本", "自主任务", "aitest"):
        target = "ai"
    elif section_lower in ("pr审查", "修复issue", "生成测试", "ai编辑代码", "代码分析", "代码审计", "claude写代码", "全栈项目", "生成项目", "生成web应用"):
        target = "code"
    elif section_lower in ("文档转markdown", "图片ocr", "pdf识别", "文档提取", "文档系统"):
        target = "document"
    elif section_lower in ("数据可视化", "仪表盘", "bi图表", "自然语言查库", "etl管道", "数据api", "数据表格", "电子表格", "低代码", "低代码平台"):
        target = "data"
    elif section_lower in ("crm联系人", "开发票", "创建工单", "发社交媒体", "营销邮件", "发短信", "邮件", "消息平台", "发通知", "erp", "ai-erp", "项目管理", "wikiknowledge", "文件共享", "记费用", "日程调度", "查员工", "创建问卷", "合同审查", "法律协议", "身份认证", "密码管理", "智能家居"):
        target = "enterprise"
    else:
        # Default to system
        target = "system"

    print(f"  {section_name:20s} → {target}.py")

# For now just print the mapping, actual splitting will be done carefully
print(f"\nTotal sections: {len(sections)}")
print(f"Need to create: browser.py, code.py, document.py, data.py, ai.py, enterprise.py, system.py")
