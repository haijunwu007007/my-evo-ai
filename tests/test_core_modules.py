# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 — 核心模块 API 测试"""
import sys, json, http.client
from pathlib import Path
BASE = Path(__file__).parent.parent; sys.path.insert(0, str(BASE))
HOST, PORT = "localhost", 8765

def g(p):
    c = http.client.HTTPConnection(HOST, PORT, timeout=15)
    c.request("GET", p, headers={"Content-Type":"application/json"})
    r = c.getresponse()
    try: return r.status, json.loads(r.read())
    except: return r.status, {}

def po(p, b=None):
    c = http.client.HTTPConnection(HOST, PORT, timeout=15)
    c.request("POST", p, body=json.dumps(b) if b else None, headers={"Content-Type":"application/json"})
    r = c.getresponse()
    try: return r.status, json.loads(r.read())
    except: return r.status, {}

class TestSystemAPI:
    def test_scheduler_status(self):
        s, d = g("/api/scheduler/status"); assert s == 200
    def test_llm_providers(self):
        s, d = g("/api/llm/providers"); assert s == 200; assert "providers" in d
    def test_config(self):
        s, d = g("/api/config"); assert s == 200; assert isinstance(d, dict)
    def test_health(self):
        s, d = g("/api/status"); assert s == 200
    def test_notify_channels(self):
        s, d = g("/api/notify/channels"); assert s == 200
    def test_security(self):
        s, d = g("/api/security/status"); assert s == 200
    def test_auth(self):
        s, d = g("/api/auth/status"); assert s == 200
    def test_diagnosis(self):
        s, d = g("/api/diagnosis/system"); assert s == 200
    def test_events_stats(self):
        s, d = g("/api/events/stats"); assert s == 200
