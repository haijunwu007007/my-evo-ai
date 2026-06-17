"""CLI项目集成 — chatgpt-cli + CodeMachine + aidevops + loop-engineering"""
import os, json, subprocess, logging

logger = logging.getLogger("evo.cli_integrations")

# ── chatgpt-cli (Go, 935★) — 多提供商LLM CLI ──

_chatgpt_cli_available = None

def chatgpt_cli_available():
    global _chatgpt_cli_available
    if _chatgpt_cli_available is None:
        try:
            subprocess.run(["chatgpt", "--version"], capture_output=True, timeout=5)
            _chatgpt_cli_available = True
        except:
            _chatgpt_cli_available = False
    return _chatgpt_cli_available

def call_chatgpt_cli(prompt, provider="openai", stream=False):
    """通过chatgpt-cli调用LLM（支持OpenAI/Azure/Perplexity/LLaMA）"""
    if not chatgpt_cli_available():
        return {"ok": False, "data": "chatgpt-cli未安装 (go install github.com/kardolus/chatgpt-cli@latest)"}
    try:
        cmd = ["chatgpt", "-p", provider, "-m", prompt]
        if stream: cmd.append("--stream")
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return {"ok": r.returncode == 0, "data": r.stdout.decode()[:3000] or r.stderr.decode()[:500]}
    except Exception as e:
        return {"ok": False, "data": f"chatgpt-cli调用失败: {e}"}

# ── CodeMachine-CLI (TypeScript, 2491★) — AI编码Agent编排 ──

_codemachine_available = None

def codemachine_available():
    global _codemachine_available
    if _codemachine_available is None:
        try:
            subprocess.run(["npx", "codemachine", "--version"], capture_output=True, timeout=10)
            _codemachine_available = True
        except:
            _codemachine_available = False
    return _codemachine_available

def run_codemachine(task, workflow="auto"):
    """运行CodeMachine工作流"""
    if not codemachine_available():
        return {"ok": False, "data": "CodeMachine未安装 (npx codemachine)"}
    try:
        cmd = ["npx", "codemachine", "--task", task, "--workflow", workflow]
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        return {"ok": r.returncode == 0, "data": r.stdout.decode()[:3000]}
    except Exception as e:
        return {"ok": False, "data": f"CodeMachine失败: {e}"}

# ── aidevops (Shell, 269★) — AI Agent DevOps工具栈 ──

_aidevops_available = None

def aidevops_available():
    global _aidevops_available
    if _aidevops_available is None:
        try:
            subprocess.run(["aidevops", "--version"], capture_output=True, timeout=5)
            _aidevops_available = True
        except:
            _aidevops_available = False
    return _aidevops_available

def run_aidevops(action, target=""):
    """运行aidevops自动化流水线"""
    if not aidevops_available():
        return {"ok": False, "data": "aidevops未安装 (git clone + chmod +x)"}
    try:
        cmd = ["aidevops", action, target] if target else ["aidevops", action]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return {"ok": r.returncode == 0, "data": r.stdout.decode()[:2000]}
    except Exception as e:
        return {"ok": False, "data": f"aidevops失败: {e}"}

# ── loop-engineering (JS, 350★) — AI循环工程 ──

_loop_available = None

def loop_available():
    global _loop_available
    if _loop_available is None:
        try:
            subprocess.run(["npx", "loop-audit", "--version"], capture_output=True, timeout=10)
            _loop_available = True
        except:
            _loop_available = False
    return _loop_available

def run_loop_audit(path="."):
    """审计代码库的AI编码质量"""
    if not loop_available():
        return {"ok": False, "data": "loop-engineering未安装 (npx loop-audit)"}
    try:
        r = subprocess.run(["npx", "loop-audit", path], capture_output=True, timeout=60)
        return {"ok": r.returncode == 0, "data": r.stdout.decode()[:2000]}
    except Exception as e:
        return {"ok": False, "data": f"loop-audit失败: {e}"}

# ── 集成注册表 ──

INTEGRATIONS = {
    "chatgpt-cli": {
        "name": "chatgpt-cli",
        "stars": 935,
        "lang": "Go",
        "desc": "多提供商LLM CLI — 作为ToolRouter的LLM后端",
        "available": chatgpt_cli_available(),
        "functions": ["call_chatgpt_cli"],
    },
    "CodeMachine": {
        "name": "CodeMachine-CLI",
        "stars": 2491,
        "lang": "TypeScript",
        "desc": "AI编码Agent编排 — 长运行工作流",
        "available": codemachine_available(),
        "functions": ["run_codemachine"],
    },
    "aidevops": {
        "name": "aidevops",
        "stars": 269,
        "lang": "Shell",
        "desc": "AI Agent DevOps工具栈",
        "available": aidevops_available(),
        "functions": ["run_aidevops"],
    },
    "loop-engineering": {
        "name": "loop-engineering",
        "stars": 350,
        "lang": "JavaScript",
        "desc": "AI循环工程 — 审计编码质量",
        "available": loop_available(),
        "functions": ["run_loop_audit"],
    },
}

def list_integrations():
    return {k: {"name": v["name"], "stars": v["stars"], "available": v["available"],
                "desc": v["desc"]} for k, v in INTEGRATIONS.items()}
