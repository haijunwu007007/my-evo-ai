import logging
logger = logging.getLogger("evo.modules.perplexica_search")
class PerplexicaSearch:
    def __init__(self): self._ready = True
    def status(self): return {"name": "perplexica_search", "ready": self._ready}
    def execute(self, action="", params=None):
        if action == "status": return self.status()
        return {"success": False, "error": "unsupported"}
def get_status(): return PerplexicaSearch().status()
def register(): return {"name": "perplexica_search", "class": "PerplexicaSearch"}
