# -*- coding: utf-8 -*-
"""桌面Agent — 远程桌面+文件操作"""
from __future__ import annotations
import os, json, sqlite3, time, subprocess
from typing import Optional

class DesktopAgent:
    def __init__(self):
        self._allowed_cmds = ["ls","dir","pwd","whoami","echo","cat","type","head","tail","wc","date"]
    
    def execute(self, cmd: str, cwd: str = "") -> dict:
        """执行安全命令"""
        base = cmd.strip().split()[0].lower() if cmd.strip() else ""
        if base not in self._allowed_cmds:
            return {"success": False, "error": f"命令 '{base}' 不在安全白名单中", "allowed": self._allowed_cmds}
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=cwd or os.getcwd())
            return {"success": True, "stdout": r.stdout[:500], "stderr": r.stderr[:200], "code": r.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "执行超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_file(self, path: str) -> dict:
        try:
            c = open(path, "r", encoding="utf-8", errors="replace").read(5000)
            return {"success": True, "content": c, "size": len(c)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write_file(self, path: str, content: str) -> dict:
        try:
            with open(path, "w", encoding="utf-8") as f: f.write(content)
            return {"success": True, "path": path, "bytes": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_dir(self, path: str = ".") -> dict:
        try:
            items = os.listdir(path)
            return {"success": True, "path": path, "items": items[:50], "count": len(items)}
        except Exception as e:
            return {"success": False, "error": str(e)}
