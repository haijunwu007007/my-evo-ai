"""修复execute方法中第一个if未缩进的问题"""
import os

path = r"D:\AUTO-EVO-AI-V0.1\modules"
files = ["qodo_review.py","testsigma_agent.py","dagger_pipeline.py","airbyte_etl.py","grafana_monitor.py","sentry_tracker.py","docling_processor.py","invoice_agent.py","chatwoot_support.py","postiz_social.py","cal_scheduler.py"]

for f in files:
    fp = os.path.join(path, f)
    with open(fp, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    
    fixed = False
    for i in range(len(lines)):
        # Find un-indented 'if action ==' line right after 'return self.get_status()'
        if i > 0 and lines[i].startswith("if action ==") and lines[i-1].strip() == "return self.get_status()":
            lines[i] = "        " + lines[i]
            fixed = True
            print(f"  FIXED {f} line {i+1}")
            break
    
    if not fixed:
        print(f"  SKIP (no fix needed) {f}")
    
    with open(fp, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
