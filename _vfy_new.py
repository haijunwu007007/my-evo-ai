import time, urllib.request, json; time.sleep(8)
base = "http://122.51.144.227:8765"
tests = ["/api/v1/qodo-review/status","/api/v1/testsigma-agent/status","/api/v1/dagger-pipeline/status","/api/v1/airbyte-etl/status","/api/v1/grafana-monitor/status","/api/v1/sentry-tracker/status","/api/v1/docling-processor/status","/api/v1/invoice-agent/status","/api/v1/chatwoot-support/status","/api/v1/postiz-social/status","/api/v1/cal-scheduler/status"]
ok = 0
for t in tests:
    try:
        r = urllib.request.urlopen(base + t, timeout=15)
        d = json.loads(r.read())
        s = "OK" if d.get("success", False) else "ERR:" + d.get("error","?")
        ok += 1
        print(t.split("/")[-2][:25], r.status, s)
    except Exception as e:
        print(t.split("/")[-2][:25], "ERR", str(e)[:20])
print(ok, "/", len(tests), "OK")
