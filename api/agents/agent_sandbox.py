"""智能体 — 代码沙箱（Open Interpreter式代码验证）"""
import logging
logger = logging.getLogger("evo.agent_sandbox")

import subprocess, tempfile, os, re, time
from pathlib import Path

class CodeSandbox:
    """轻量代码沙箱——验证生成代码的语法和基本功能"""

    @staticmethod
    def validate_html(html_code):
        """验证HTML语法"""
        issues = []
        # 基本结构检查
        if "<!DOCTYPE html>" not in html_code: issues.append("缺少DOCTYPE声明")
        if "<html" not in html_code: issues.append("缺少<html>标签")
        if "<head>" not in html_code: issues.append("缺少<head>标签")
        if "<body>" not in html_code: issues.append("缺少<body>标签")
        # 标签闭合检查
        open_tags = re.findall(r'<(\w+)[^>]*>', html_code)
        close_tags = re.findall(r'</(\w+)>', html_code)
        tag_stack = []
        for t in open_tags:
            if t not in ("br", "hr", "img", "input", "meta", "link"):
                tag_stack.append(t)
        for t in close_tags:
            if tag_stack and tag_stack[-1] == t:
                tag_stack.pop()
        if tag_stack: issues.append(f"未闭合标签: {', '.join(tag_stack[:5])}")
        # JS语法检查
        js_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html_code, re.DOTALL)
        for js in js_blocks:
            try: compile(js, '<sandbox>', 'exec')
            except SyntaxError as e: issues.append(f"JS语法错误: {e}")
        return issues

    @staticmethod
    def validate_python(py_code):
        """验证Python语法"""
        try: compile(py_code, '<sandbox>', 'exec'); return []
        except SyntaxError as e: return [f"Python语法错误: {e}"]

    @staticmethod
    def save_and_report(code, filepath):
        """保存代码并返回验证报告"""
        issues = []
        if str(filepath).endswith(".html"):
            issues = CodeSandbox.validate_html(code)
        elif str(filepath).endswith(".py"):
            issues = CodeSandbox.validate_python(code)
        Path(filepath).write_text(code, encoding='utf-8')
        return {"saved": True, "path": str(filepath), "issues": issues, "size": len(code)}

sandbox = CodeSandbox()
