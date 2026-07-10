"""系统能力差距分析"""
import logging
logger = logging.getLogger("evo.gap_analyzer")

import os, json

BASE = os.path.dirname(os.path.dirname(__file__))

gaps = []

# 1. 能自动搜索/分析代码吗
try:
    from api.tools.code import code_analyze
    r = code_analyze({"code": "def f(): pass"})
    if "LLM" not in r.get("data",""):
        gaps.append({"gap": "代码自动理解/重构", "current": "仅简单分析", "target": "自动理解→重构→优化→测试"})
except: pass

# 2. 能自动生成完整项目吗
try:
    from api.hub.generate_project import generate_project
    r = generate_project({"name":"test","type":"vue"})
    if r.get("ok"):
        gaps.append({"gap": "从需求→完整项目生成", "current": "脚手架模板生成", "target": "自然语言→完整多文件项目→部署"})
except: pass

# 3. 能自动修复bug吗
try:
    from api.tools.code import fix_issue
    r = fix_issue({"body":"app crashes on empty input"})
    if "LLM" not in r.get("data",""):
        gaps.append({"gap": "自动Bug修复", "current": "Issue分析", "target": "自动定位→生成补丁→PR"})
except: pass

# 4. 能自动搜索/学习吗
try:
    from api.tools.code import code_edit
    r = code_edit({"code":"x=1","instruction":"add comment"})
    if "LLM" not in r.get("data",""):
        gaps.append({"gap": "自动代码编辑", "current": "基础修改", "target": "需求→精确修改→验证"})
except: pass

# 5. 浏览器自动化深度
try:
    from api.tools.browser import browser_automate
    r = browser_automate({"url":"https://example.com","action":"fill","selector":"#search","value":"test"})
    if "screenshot" in r.get("data",""):
        gaps.append({"gap": "深度浏览器自动化", "current": "仅截图/爬取", "target": "导航→点击→填写→提取→截图全链路"})
except: pass

logger.info(f"发现 {len(gaps)} 个能力差距:")
for g in gaps:
    logger.info(f"  [{g['gap']}] 当前: {g['current']}")
