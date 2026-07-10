import logging
logger = logging.getLogger("evo.modules.sentry_tracker")
class SentryTracker:
    def __init__(self): self._ready = True
    def status(self): return {"name": "sentry_tracker", "ready": self._ready}
    def execute(self, action="", params=None):
        if action == "status": return self.status()
        return {"success": False, "error": "unsupported"}
def get_status(): return SentryTracker().status()
def register(): return {"name": "sentry_tracker", "class": "SentryTracker"}
