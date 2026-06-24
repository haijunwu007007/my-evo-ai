"""修复模块文件中 execute 方法内的 if 缩进问题"""
import re, os

path = r"D:\AUTO-EVO-AI-V0.1\modules"
files = ["qodo_review.py","testsigma_agent.py","dagger_pipeline.py","airbyte_etl.py","grafana_monitor.py","sentry_tracker.py","docling_processor.py","invoice_agent.py","chatwoot_support.py","postiz_social.py","cal_scheduler.py"]

for f in files:
    fp = os.path.join(path, f)
    with open(fp, "r", encoding="utf-8") as fh:
        content = fh.read()
    
    # Fix: the first 'if action ==' in execute method is not indented
    # Pattern: after 'return {}' there's a blank line then unindented 'if action'
    content = re.sub(
        r'return self\.get_status\(\)\n\nif action ==',
        'return self.get_status()\n        if action ==',
        content
    )
    
    with open(fp, "w", encoding="utf-8") as fh:
        fh.write(content)
    
    # Verify indentation
    with open(fp, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines):
        if "if action ==" in line and not line.startswith("        if"):
            print(f"  STILL BAD {f}:{i+1} {line.rstrip()[:60]}")
    
    print(f"  FIXED {f}")

print("\nAll done")
