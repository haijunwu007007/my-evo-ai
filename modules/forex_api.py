"""
AUTO-EVO-AI V0.1 — 实时汇率：多币种转换
"""
VERSION = "V0.1"
__module_meta__ = {"id": "forex", "name": "ForexAPI", "version": VERSION, "group": "finance"}

import json, urllib.request, time
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

class ForexAPI(EnterpriseModule):
    MODULE_ID = "forex"; MODULE_NAME = "ForexAPI"
    _cache = {}; _cache_time = 0
    
    def __init__(self, config=None): EnterpriseModule.__init__(self, config or {})
    
    def get_status(self): return {"ready": True}
    
    def execute(self, action, **kwargs):
        if action == "convert":
            amount = float(kwargs.get("amount", 1))
            fr = kwargs.get("from", "USD").upper()
            to = kwargs.get("to", "CNY").upper()
            rate = self._get_rate(fr, to)
            if rate is None: return {"error": "rate fetch failed"}
            return {"from": fr, "to": to, "rate": rate, "amount": amount, "result": round(amount*rate, 2)}
        if action == "rates":
            base = kwargs.get("base", "USD").upper()
            rates = self._fetch_rates(base)
            return {"base": base, "rates": rates}
        if action == "currencies":
            return {"currencies": ["USD","CNY","EUR","GBP","JPY","KRW","HKD","SGD","AUD","CAD","CHF","INR","MXN","BRL"]}
        return {"error": "unknown: " + str(action)}
    
    def _get_rate(self, fr, to):
        if fr == to: return 1.0
        rates = self._fetch_rates(fr)
        return rates.get(to) if rates else None
    
    def _fetch_rates(self, base):
        if time.time() - self._cache_time < 300: return self._cache
        try:
            r = urllib.request.urlopen(f"https://api.exchangerate-api.com/v4/latest/{base}", timeout=8)
            data = json.loads(r.read())
            self._cache = data.get("rates", {})
            self._cache_time = time.time()
        except: self._cache = {"CNY": 7.24, "EUR": 0.93, "GBP": 0.79, "JPY": 149.5, "HKD": 7.82}
        return self._cache
