"""修复剩余9处 except:pass"""
import re
files = {
    "api_server.py": [(23, "pass  # .env 文件不存在不影响启动"),
                      ("need more lines")],
}
# Let me just find them directly and fix with replace
import pathlib
ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1")

# Read api_server.py and find all except:pass
with open(ROOT / "api_server.py") as f:
    lines = f.readlines()

# Fix 1: line 23-24 (0-index: 22-23)
for i, line in enumerate(lines):
    if "except:" in line and i+1 < len(lines) and lines[i+1].strip() == "pass":
        indent = len(lines[i]) - len(lines[i].lstrip())
        next_indent = len(lines[i+1]) - len(lines[i+1].lstrip())
        if next_indent > indent:  # pass is indented more than except line
            lines[i+1] = " " * next_indent + "logger.warning(\"[startup] .env 加载失败: {e}\")\n"

with open(ROOT / "api_server.py", "w") as f:
    f.writelines(lines)
logger.info("api_server.py fixed"))

# Fix modules/ files
for fname in ["modules/agent_s_bridge.py", "modules/cluster_proxy.py", "modules/_base/compat.py"]:
    fp = ROOT / fname
    c = fp.read_text("utf-8")
    # Use importlib to check if logger exists, if not add
    if "get_logger" not in c and "logger" not in c.split("except"):
        # Add import at top
        c = "from core.logging_config import get_logger\nlogger = get_logger(\"evo." + fname.replace("/",".").replace(".py","") + "\")\n" + c
    # Replace except: pass with except: logger.warning(...)
    c = re.sub(
        r'^( +)except[^:]*:[^\n]*\n\1+pass',
        r'\1except Exception as _e:\1    logger.warning(f"[\1.strip() module] 异常: {_e}")',
        c,
        flags=re.MULTILINE
    )
    fp.write_text(c, "utf-8")
    logger.info(f"{fname} fixed"))

# scripts/gen_module_docs.py
fp = ROOT / "scripts/gen_module_docs.py"
c = fp.read_text("utf-8")
c = re.sub(
    r'^( +)except[^:]*:[^\n]*\n\1+pass',
    logger.info(cept Exception as _e:\1    print(f"警告: {_e}")',)
    c,
    flags=re.MULTILINE
)
fp.write_text(c, "utf-8")
logger.info("gen_module_docs.py fixed"))

# skills/builtin/voice_tts.py
fp = ROOT / "skills/builtin/voice_tts.py"
c = fp.read_text("utf-8")
if "get_logger" not in c:
    c = "from core.logging_config import get_logger\nlogger = get_logger(\"evo.skills.voice_tts\")\n" + c
c = re.sub(
    r'^( +)except[^:]*:[^\n]*\n\1+pass',
    r'\1except Exception as _e:\1    logger.warning(f"[voice_tts] 异常: {_e}")',
    c,
    flags=re.MULTILINE
)
fp.write_text(c, "utf-8")
logger.info("voice_tts.py fixed"))

logger.info("\nDone"))
