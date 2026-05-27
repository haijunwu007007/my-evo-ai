"""Fix asyncio.Semaphore -> threading.Semaphore in web_scraper"""
f = open("modules/web_scraper.py", encoding="utf-8").read()
f = f.replace("asyncio.Semaphore(self._max_concurrent)", "threading.Semaphore(self._max_concurrent)")
# Ensure threading is imported
if "import threading" not in f:
    f = f.replace("import asyncio", "import asyncio, threading")
open("modules/web_scraper.py", "w", encoding="utf-8").write(f)
print("Fixed")
