import re, os
path = r"D:\AUTO-EVO-AI-V0.1\modules"
files = ["qodo_review.py","testsigma_agent.py","dagger_pipeline.py","airbyte_etl.py","grafana_monitor.py","sentry_tracker.py","docling_processor.py","invoice_agent.py","chatwoot_support.py","postiz_social.py","cal_scheduler.py"]
for f in files:
    fp = os.path.join(path, f)
    with open(fp, "r", encoding="utf-8") as fh:
        c = fh.read()
    c = c.replace('self._status = { "', 'self._status = {"name": "')
    with open(fp, "w", encoding="utf-8") as fh:
        fh.write(c)
    print("FIXED", f)
