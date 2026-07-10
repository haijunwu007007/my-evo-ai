
class BookstackKB:
    def __init__(self): self.pages = {}; self._ready = True
    def status(self): return {"name": "bookstack_kb", "ready": self._ready, "pages": len(self.pages)}
    def search(self, q): return [p for p in self.pages.values() if q in p.get("title", "")]
    def execute(self, action="", params=None):
        if action == "search": return self.search((params or {}).get("query", ""))
        return self.status()
get_status = lambda: BookstackKB().status()
