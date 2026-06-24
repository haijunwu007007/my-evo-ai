"""强制重新上传11个修复后的模块并重启"""
import paramiko, os

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)
sf = s.open_sftp()

modules = [
    "qodo_review.py", "testsigma_agent.py", "dagger_pipeline.py",
    "airbyte_etl.py", "grafana_monitor.py", "sentry_tracker.py",
    "docling_processor.py", "invoice_agent.py", "chatwoot_support.py",
    "postiz_social.py", "cal_scheduler.py"
]

local_dir = r"D:\AUTO-EVO-AI-V0.1\modules"
remote_dir = "/home/ubuntu/my-evo-ai/modules"

for m in modules:
    local = os.path.join(local_dir, m)
    remote = os.path.join(remote_dir, m)
    # Check local file has fix
    with open(local, "r", encoding="utf-8") as f:
        content = f.read()
    has_fix = '"name":' in content
    sf.put(local, remote)
    size = os.path.getsize(local)
    print(f"  {m:35s} {size}B fix={has_fix}")

sf.close()
print("\nRestarting service...")
s.exec_command("sudo systemctl restart evo.service")
s.close()
print("DONE")
