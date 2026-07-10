"""工具注册表 — tool() 装饰器 + exec_tool() 执行入口"""
import logging
logger = logging.getLogger("evo.registry")

import os, json, re, time, hashlib, tempfile, subprocess
from typing import Any

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_tools: dict = {}

def tool(name: str, category: str, description: str):
    """装饰器：注册工具"""
    def deco(fn):
        fn._meta = {"name": name, "category": category, "description": description}
        _tools[name] = fn
        return fn
    return deco

def exec_tool(name: str, args: dict, **kw) -> dict:
    """执行指定工具"""
    if name in _tools:
        try:
            result = _tools[name](args, **kw)
            result["tool"] = name
            return result
        except Exception as e:
            return {"ok": False, "data": f"工具执行失败: {e}", "tool": name}
    return {"ok": False, "data": f"未知工具: {name}"}

def _llm(prompt: str, system: str = "") -> str:
    """调用 LLM（Qwen3.6 优先，DSR1 次之）"""
    try:
        from api.agent_llm import call_llm
        messages = [{"role": "user", "content": prompt}]
        if system:
            messages.insert(0, {"role": "system", "content": system})
        text, _ = call_llm(messages)
        return text or ""
    except Exception:
        return ""

def list_tools():
    """列出所有注册的工具"""
    result = []
    for n, fn in _tools.items():
        meta = getattr(fn, '_meta', None)
        if meta:
            result.append({"name": n, **meta})
        else:
            result.append({"name": n, "category": "集成", "description": ""})
    return result
