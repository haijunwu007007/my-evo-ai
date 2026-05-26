# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - Web 远程控制（A级）"""
__module_meta__ = {"id":"web-remote","name":"WebRemote","version":"V0.1","group":"network","grade":"A",
    "tags":["network","remote","control","execution"],"description":"基于 subprocess 的真实远程命令执行"}
import time, uuid, logging, os, subprocess, base64
from pathlib import Path
from typing import Any, Dict, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin, Result)
logger = logging.getLogger("evo.web-remote")

class WebRemote(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID = "web-remote"
    MODULE_NAME = "远程控制"
    VERSION = "v1.0"
    MODULE_LEVEL = "A"

    def __init__(self, config=None):
        super().__init__(config)
        self._commands: list = []
        self._max_history = int(config.get("max_history", 200)) if config else 200
        self._allowed_prefixes = config.get("allowed_commands", []) if config else []
        self._sandbox_dir = config.get("sandbox_dir", "") if config else ""

    def initialize(self) -> None:
        self.status = ModuleStatus.RUNNING

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=self.status.value, healthy=True,
            module_id=self.MODULE_ID,
            checks={"history": len(self._commands)}
        )

    async def execute(self, action=None, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)

    def _check_allowed(self, cmd: str) -> bool:
        if not self._allowed_prefixes:
            return True
        return any(cmd.strip().startswith(p) for p in self._allowed_prefixes)

    def _run_cmd(self, cmd: str, timeout: int = 30) -> dict:
        if not self._check_allowed(cmd):
            return {"error": f"command not in allowed list", "allowed_prefixes": self._allowed_prefixes}
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self._sandbox_dir or None
            )
            return {
                "success": True,
                "command": cmd,
                "stdout": r.stdout[:32000],
                "stderr": r.stderr[:8000],
                "exit_code": r.returncode,
                "duration_seconds": round(getattr(r, '_duration', 0), 3)
            }
        except subprocess.TimeoutExpired:
            return {"error": f"timeout after {timeout}s", "command": cmd}
        except Exception as e:
            return {"error": str(e), "command": cmd}

    def _dispatch(self, p: dict) -> dict:
        a = p.get("action", "status")

        if a == "status":
            return {
                "success": True,
                "history_count": len(self._commands),
                "allowed_commands": self._allowed_prefixes or "*",
                "sandbox": self._sandbox_dir or "(current dir)"
            }

        if a == "execute":
            cmd = p.get("command", "")
            timeout = int(p.get("timeout", 30))
            t0 = time.time()
            result = self._run_cmd(cmd, timeout)
            result["duration_seconds"] = round(time.time() - t0, 3)
            self._commands.append({
                "command": cmd, "timestamp": time.time(),
                "exit_code": result.get("exit_code", -1),
                "duration": result.get("duration_seconds", 0)
            })
            if len(self._commands) > self._max_history:
                self._commands = self._commands[-self._max_history:]
            return result

        if a == "read_file":
            path = p.get("path", "")
            max_bytes = int(p.get("max_bytes", 65536))
            try:
                fp = Path(path).resolve()
                if not fp.exists() or not fp.is_file():
                    return {"error": f"file not found: {path}"}
                content = fp.read_bytes()[:max_bytes]
                return {
                    "success": True,
                    "path": str(fp),
                    "size": len(content),
                    "data_base64": base64.b64encode(content).decode("ascii"),
                    "truncated": fp.stat().st_size > max_bytes
                }
            except Exception as e:
                return {"error": f"read error: {e}"}

        if a == "write_file":
            path = p.get("path", "")
            data_b64 = p.get("data_base64", "")
            try:
                fp = Path(path).resolve()
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(base64.b64decode(data_b64))
                return {"success": True, "path": str(fp), "size": fp.stat().st_size}
            except Exception as e:
                return {"error": f"write error: {e}"}

        if a == "list_dir":
            path = p.get("path", ".")
            try:
                fp = Path(path).resolve()
                if not fp.exists():
                    return {"error": f"path not found: {path}"}
                entries = []
                for entry in sorted(fp.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                    try:
                        st = entry.stat()
                        entries.append({
                            "name": entry.name,
                            "type": "dir" if entry.is_dir() else "file",
                            "size": st.st_size,
                            "modified": st.st_mtime
                        })
                    except OSError:
                        continue
                return {"success": True, "path": str(fp), "entries": entries,
                        "dirs": sum(1 for e in entries if e["type"] == "dir"),
                        "files": sum(1 for e in entries if e["type"] == "file")}
            except Exception as e:
                return {"error": f"list error: {e}"}

        if a == "disk_usage":
            path = p.get("path", ".")
            try:
                st = os.statvfs(path) if hasattr(os, 'statvfs') else None
                if st:
                    total = st.f_frsize * st.f_blocks
                    free = st.f_frsize * st.f_bfree
                    used = total - free
                    return {
                        "success": True,
                        "path": path,
                        "total_bytes": total,
                        "used_bytes": used,
                        "free_bytes": free,
                        "used_percent": round(used / total * 100, 1) if total else 0
                    }
                else:
                    # Windows fallback
                    import ctypes
                    free_bytes = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes)
                    )
                    return {"success": True, "path": path, "free_bytes": free_bytes.value}
            except Exception as e:
                return {"error": f"disk usage error: {e}"}

        if a == "history":
            limit = int(p.get("limit", 50))
            return {
                "success": True,
                "history": self._commands[-min(limit, self._max_history):]
            }

        if a == "clear_history":
            self._commands.clear()
            return {"success": True, "cleared": True}

        return {"error": f"unknown action: {a}"}

    async def shutdown(self) -> None:
        self._commands.clear()
        self.status = ModuleStatus.STOPPED

module_class = WebRemote
