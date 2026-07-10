# AUTO-EVO-AI Python SDK
# 封装 API 所有端点，pip install 即可使用

import urllib.request, urllib.parse, json

BASE = "https://autoevoai.com"

class EvoClient:
    def __init__(self, base_url=BASE, api_key=None):
        self.base = base_url.rstrip("/")
        self.api_key = api_key

    def _req(self, path, method="GET", data=None):
        url = f"{self.base}{path}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        kwargs = {"headers": headers}
        if data is not None:
            kwargs["data"] = json.dumps(data).encode()
        req = urllib.request.Request(url, **kwargs)
        req.method = method
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return {"status": r.status, "data": json.loads(r.read())}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            return {"status": e.code, "error": body}
        except Exception as e:
            return {"status": 0, "error": str(e)}

    # ── 对话 ──
    def chat(self, msg):
        return self._req("/api/v1/chat", "POST", {"message": msg})

    def smart_chat(self, msg):
        return self._req("/api/v2/chat", "POST", {"message": msg})

    # ── 模块 ──
    def modules(self, category=None):
        q = f"?category={urllib.parse.quote(category)}" if category else ""
        return self._req(f"/api/v1/modules{q}")

    def module_detail(self, name):
        return self._req(f"/api/v1/modules/{urllib.parse.quote(name)}")

    # ── 技能 ──
    def skills(self, category=None):
        q = f"?category={urllib.parse.quote(category)}" if category else ""
        return self._req(f"/api/v1/skills{q}")

    def skill_execute(self, name, **params):
        return self._req(f"/api/v1/skills/{urllib.parse.quote(name)}/execute", "POST", params)

    # ── 系统 ──
    def status(self):
        return self._req("/api/v1/status")

    def version(self):
        return self._req("/api/v1/version")

    def health(self):
        return self._req("/api/v1/health")

    # ── MCP ──
    def mcp_servers(self):
        return self._req("/api/v1/mcp/servers")

    def mcp_call(self, server, tool, **args):
        return self._req(f"/api/v1/mcp/{server}/{tool}", "POST", args)

    # ── A2A Agent ──
    def a2a_rooms(self):
        return self._req("/api/v1/a2a/rooms")

    def a2a_create_room(self):
        return self._req("/api/v1/a2a/create-room", "POST")

    # ── 语音 ──
    def speech_recognize(self, wav_data):
        from urllib.request import Request
        req = Request(f"{self.base}/api/v1/speech/recognize", data=wav_data,
                      headers={"Content-Type": "audio/wav"})
        req.method = "POST"
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    # ── 搜索 ──
    def search(self, query):
        return self._req(f"/api/v1/search?q={urllib.parse.quote(query)}")

    # ── Gateway ──
    def gateway_call(self, slug, **params):
        return self._req(f"/api/v1/gateway/call", "POST", {"slug": slug, **params})

    # ── RAG ──
    def rag_query(self, query, collection="default"):
        return self._req("/api/v1/rag/query", "POST", {"query": query, "collection": collection})

    # ── Cognee ──
    def cognee_search(self, query):
        return self._req(f"/api/v1/cognee/search?query={urllib.parse.quote(query)}")

    def cognee_add(self, text, source="sdk"):
        return self._req("/api/v1/cognee/add", "POST", {"text": text, "source": source})

    # ── coordinator ──
    def coordinator_status(self):
        return self._req("/api/v1/coordinator/status")

    # ── 平台管理 ──
    def register(self, user, pwd=""):
        return self._req("/api/v1/auth/register", "POST", {"username": user, "password": pwd})

    def login(self, user, pwd=""):
        return self._req("/api/v1/auth/login", "POST", {"username": user, "password": pwd})


def main():
    """命令行 demo"""
    import sys
    c = EvoClient()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "chat" and len(sys.argv) > 2:
            r = c.chat(sys.argv[2])
            logger.info(json.dumps(r["data"], indent=2, ensure_ascii=False) if r["data"] else r))
        elif cmd == "status":
            logger.info(json.dumps(c.status(), indent=2, ensure_ascii=False)))
        elif cmd == "version":
            logger.info(json.dumps(c.version(), indent=2, ensure_ascii=False)))
        elif cmd == "modules":
            cat = sys.argv[2] if len(sys.argv) > 2 else None
            r = c.modules(cat)
            ms = r["data"].get("modules", []) if r.get("data") else []
            logger.info(f"Total: {len(ms)} modules"))
            for m in ms[:20]:
                logger.info(f"  {m}"))
        elif cmd == "skills":
            r = c.skills()
            ss = r["data"].get("skills", []) if r.get("data") else []
            logger.info(f"Total: {len(ss)} skills"))
        else:
            logger.info(f"Unknown: {cmd}"))
    else:
        v = c.version()
        s = c.status()
        logger.info(f"AUTO-EVO-AI SDK — {v.get('version','?')}"))
        logger.info(f"Status: {s.get('status','?')}"))


if __name__ == "__main__":
    main()
