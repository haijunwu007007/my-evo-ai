"""Split agent_tools.py into api/tools submodules"""
import re, os

SRC = r"./api\agent_tools.py"
DST = r"./api\tools"

with open(SRC, encoding="utf-8") as f:
    text = f.read()

# Category → file mapping
CAT_MAP = {
    "浏览器自动化": "browser", "AI智能爬虫": "browser", "搜索内容": "browser",
    "自主研究": "ai", "数据可视化": "data", "仪表盘": "data", "BI图表": "data",
    "生成项目": "code", "生成Web应用": "code", "PR审查": "code", "修复Issue": "code",
    "生成测试": "code", "AI编辑代码": "code", "代码分析": "code", "安全扫描": "system",
    "代码审计": "code", "CRM联系人": "enterprise", "开发票": "ai", "创建工单": "enterprise",
    "发社交媒体": "ai", "营销邮件": "enterprise", "自然语言查库": "data", "ETL管道": "data",
    "发通知": "enterprise", "发短信": "enterprise", "ERP": "enterprise", "AI-ERP": "ai",
    "项目管理": "enterprise", "Wiki知识": "enterprise", "文件共享": "enterprise",
    "IaC部署": "system", "运维自动化": "system", "CMS管理": "system", "数据API": "data",
    "站点监控": "system", "可观测": "system", "APM监控": "system", "安全监控": "system",
    "消息队列": "system", "消息代理": "system", "Git管理": "system", "桌面自动化": "system",
    "远程桌面": "system", "电脑控制": "system", "截图转代码": "ai", "语音合成": "system",
    "视频脚本": "ai", "多智能体": "system", "自主任务": "ai", "合同审查": "ai",
    "查员工": "enterprise", "记费用": "enterprise", "日程调度": "enterprise",
    "创建问卷": "ai", "身份认证": "system", "文件存储": "system", "记忆管理": "system",
    "搜索记忆": "system", "低代码": "data", "低代码平台": "data", "MLOps": "system",
    "LLM观测": "system", "API测试": "system", "电子表格": "data", "RSS聚合": "system",
    "音频转录": "system", "AI测试": "ai", "技能学习": "system", "外部工具": "system",
    "API发现": "system", "Agent评测": "ai", "Claude写代码": "code", "法律协议": "ai",
    "密码管理": "enterprise", "流程图": "system", "电子签名": "enterprise",
    "智能家居": "enterprise", "PaaS部署": "system", "数据表格": "data",
    "消息平台": "enterprise", "全栈项目": "code", "文档提取": "document",
    "文档系统": "document", "邮件": "enterprise", "文档转Markdown": "document",
    "图片OCR": "document", "PDF识别": "document",
}

# Find all tool blocks
tool_blocks = re.findall(
    r'(@tool\("(\w+)",\s*"([^"]+)".*?)(?=\n@tool|\n# ══|\ndef exec_tool|\Z)',
    text, re.DOTALL
)

files = {}
for full_block, name, cat in tool_blocks:
    target = CAT_MAP.get(cat, "misc")
    files.setdefault(target, []).append(full_block)

# Create files
head = '''"""AUTO-EVO-AI 工具模块"""
import os, json, subprocess, tempfile, time, hashlib, re, urllib, pathlib
from pathlib import Path
from typing import Any
try:
    from api.tools.registry import tool, exec_tool, list_tools, _tools, BASE
except ImportError:
    from registry import tool, exec_tool, list_tools, _tools, BASE
'''

for fname, blocks in files.items():
    path = os.path.join(DST, f"{fname}.py")
    content = head + "\n" + "\n\n".join(b.strip() for b in blocks)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  {fname}.py: {len(blocks)} tools")

# Create __init__.py
init = '''"""tools 包 — 导入所有子模块"""
from api.tools import registry
from api.tools import browser, code, document, data, ai, enterprise, system, misc
from api.tools.registry import tool, exec_tool, list_tools, _tools
__all__ = ["tool", "exec_tool", "list_tools"]
'''
with open(os.path.join(DST, "__init__.py"), "w", encoding="utf-8") as f:
    f.write(init)

print(f"\nTotal: {sum(len(b) for b in files.values())} tools across {len(files)} files")
