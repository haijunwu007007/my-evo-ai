import py_compile
files = [
    "api/routes/routes_llm_chat.py",
    "api/routes/routes_services.py",
    "api/routes/routes_desktop_control.py",
]
ok = 0
for f in files:
    try:
        py_compile.compile(f"D:/AUTO-EVO-AI-V0.1/{f}", doraise=True)
        logger.info(f"OK {f}"))
        ok += 1
    except Exception as e:
        logger.info(f"ERR {f}: {e}"))
logger.info(f"{ok}/{len(files)} OK"))
