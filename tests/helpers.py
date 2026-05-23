# -*- coding: utf-8 -*-
"""测试工具函数"""
import os, sys, json, http.client
from pathlib import Path
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
HOST, PORT = "localhost", 8765

def api_get(path, timeout=10):
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    c.request("GET", path, headers={"Content-Type":"application/json"})
    r = c.getresponse(); data = r.read()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw": data[:500]}

def api_post(path, body=None, timeout=10):
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    c.request("POST", path, body=json.dumps(body) if body else None, headers={"Content-Type":"application/json"})
    r = c.getresponse(); data = r.read()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw": data[:500]}

def api_put(path, body=None, timeout=10):
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    c.request("PUT", path, body=json.dumps(body) if body else None, headers={"Content-Type":"application/json"})
    r = c.getresponse(); data = r.read()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw": data[:500]}

def api_delete(path, timeout=10):
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    c.request("DELETE", path, headers={"Content-Type":"application/json"})
    r = c.getresponse(); data = r.read()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw": data[:500]}
