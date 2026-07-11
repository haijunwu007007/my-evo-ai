"""CLI工具集成 — 统一调用20+常用命令行工具"""
from __future__ import annotations
import os, subprocess, json, shutil, tempfile, re
from pathlib import Path

TOOLS = {
    "yt-dlp":   {"desc":"视频下载","cmds":["yt-dlp","youtube-dl"]},
    "ffmpeg":   {"desc":"音视频转换","cmds":["ffmpeg"]},
    "ffprobe":  {"desc":"媒体信息","cmds":["ffprobe"]},
    "imagemagick": {"desc":"图片处理","cmds":["convert","magick"]},
    "pandoc":   {"desc":"文档转换","cmds":["pandoc"]},
    "tesseract": {"desc":"OCR文字识别","cmds":["tesseract"]},
    "sox":      {"desc":"音频处理","cmds":["sox"]},
    "jq":       {"desc":"JSON处理","cmds":["jq"]},
    "yq":       {"desc":"YAML处理","cmds":["yq"]},
    "csvkit":   {"desc":"CSV处理","cmds":["csvcut","csvstat","csvsql"]},
    "ripgrep":  {"desc":"代码搜索","cmds":["rg","ripgrep"]},
    "fd":       {"desc":"文件查找","cmds":["fd","fdfind"]},
    "bat":      {"desc":"文件查看","cmds":["bat","batcat"]},
    "htop":     {"desc":"系统监控","cmds":["htop"]},
    "ncdu":     {"desc":"磁盘分析","cmds":["ncdu"]},
    "rsync":    {"desc":"文件同步","cmds":["rsync"]},
    "aria2c":   {"desc":"多线程下载","cmds":["aria2c"]},
    "qpdf":     {"desc":"PDF处理","cmds":["qpdf"]},
    "pdftotext":{"desc":"PDF转文本","cmds":["pdftotext"]},
    "wkhtmltopdf":{"desc":"HTML转PDF","cmds":["wkhtmltopdf"]},
}

class CLIExecutor:
    def status(self):
        available = {}
        for name, info in TOOLS.items():
            for cmd in info["cmds"]:
                if shutil.which(cmd):
                    available[name] = {"available":True,"cmd":cmd,"desc":info["desc"]}
                    break
                available[name] = {"available":False,"desc":info["desc"]}
        return {"ready":True,"tools":available,"total":len(TOOLS),"available":sum(1 for v in available.values() if v["available"])}

    def execute(self, action, params=None):
        if action == "status":
            return self.status()
        if action == "run":
            tool = (params or {}).get("tool","")
            args = (params or {}).get("args","")
            if not tool or tool not in TOOLS:
                return {"success":False,"error":f"未知工具: {tool}，可用: {', '.join(list(TOOLS.keys())[:10])}"}
            info = TOOLS[tool]
            cmd = None
            for c in info["cmds"]:
                if shutil.which(c):
                    cmd = c; break
            if not cmd:
                return {"success":False,"error":f"{tool} 未安装"}
            full_cmd = [cmd] + (args.split() if isinstance(args,str) else args)
            try:
                r = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
                return {"success":r.returncode==0,"stdout":r.stdout[:2000],"stderr":r.stderr[:500],"exit_code":r.returncode}
            except subprocess.TimeoutExpired:
                return {"success":False,"error":"执行超时(60s)"}
            except Exception as e:
                return {"success":False,"error":str(e)}
        if action == "find":
            q = (params or {}).get("query","")
            if not q: return {"success":False,"error":"请输入搜索关键词"}
            matches = {k:v for k,v in TOOLS.items() if q.lower() in k.lower() or q.lower() in v["desc"].lower()}
            return {"success":True,"results":matches,"count":len(matches)}
        return {"success":False,"error":f"未知操作: {action}"}

    def register(self):
        return {"name":"cli_tools","title":"CLI工具集","desc":"集成20+常用命令行工具(yt-dlp/ffmpeg/imagemagick/pandoc/tesseract等)"}

executor = CLIExecutor()
