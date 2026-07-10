import logging
logger = logging.getLogger("evo.modules.home_assistant")
class HomeAssistant:
    def __init__(self): self._ready = True
    def status(self): return {"name": "home_assistant", "ready": self._ready}
    def execute(self, action="", params=None):
        if action == "status": return self.status()
        return {"success": False, "error": "unsupported"}
def get_status(): return HomeAssistant().status()
def register(): return {"name": "home_assistant", "class": "HomeAssistant"}
