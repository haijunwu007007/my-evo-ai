import sys, os
os.chdir("/home/ubuntu/my-evo-ai")
sys.path.insert(0, ".")
modules_to_test = [
    "qodo_review.QodoReviewModule",
    "testsigma_agent.TestSigmaModule", 
    "dagger_pipeline.DaggerPipelineModule",
    "airbyte_etl.AirbyteETLModule",
    "grafana_monitor.GrafanaMonitorModule",
    "sentry_tracker.SentryTrackerModule",
    "docling_processor.DoclingProcessorModule",
    "invoice_agent.InvoiceModule",
    "chatwoot_support.ChatwootModule",
    "postiz_social.PostizModule",
    "cal_scheduler.CalModule",
]
for mt in modules_to_test:
    mod_name, cls_name = mt.split(".")
    try:
        exec(f"from modules.{mod_name} import {cls_name}")
        m = eval(f"{cls_name}()")
        s = m.get_status()
        print(f"OK {mod_name}")
    except Exception as e:
        print(f"FAIL {mod_name}: {e}")
