"""
AUTO-EVO-AI V0.1 — ML Intern：线性回归+K-Means
"""
VERSION = "V0.1"
__module_meta__ = {"id": "ml-intern", "name": "MLIntern", "version": VERSION, "group": "ai"}

import json, math, random, statistics
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

class MLIntern(EnterpriseModule):
    MODULE_ID = "ml-intern"; MODULE_NAME = "MLIntern"
    
    def __init__(self, config=None): EnterpriseModule.__init__(self, config or {})
    
    def get_status(self): return {"ready": True}
    
    def execute(self, action, **kwargs):
        if action == "linear_regression":
            xs = kwargs.get("x", [])
            ys = kwargs.get("y", [])
            if len(xs) < 2: return {"error": "need at least 2 points"}
            n = len(xs)
            mx = sum(xs)/n; my = sum(ys)/n
            num = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
            den = sum((xs[i]-mx)**2 for i in range(n))
            slope = num/den if den else 0
            intercept = my - slope*mx
            pred = [slope*x + intercept for x in xs]
            return {"slope": round(slope,4), "intercept": round(intercept,4), "predictions": [round(p,2) for p in pred]}
        if action == "kmeans":
            points = kwargs.get("points", [])
            k = kwargs.get("k", 3)
            if len(points) < k: return {"error": "not enough points"}
            centroids = random.sample(points, k)
            for _ in range(20):
                clusters = {i:[] for i in range(k)}
                for p in points:
                    dists = [sum((p[j]-c[j])**2 for j in range(len(p))) for c in centroids]
                    clusters[dists.index(min(dists))].append(p)
                new_c = []
                for i in range(k):
                    if clusters[i]:
                        new_c.append([sum(d)/len(d) for d in zip(*clusters[i])])
                    else:
                        new_c.append(centroids[i])
                if new_c == centroids: break
                centroids = new_c
            return {"clusters": {i: len(v) for i,v in clusters.items()}, "centroids": centroids}
        if action == "hello":
            return {"message": "ML Intern ready. Try: linear_regression, kmeans"}
        return {"error": "unknown: " + str(action)}

    def health_check(self) -> dict:
        return {"status": "healthy", "module": getattr(self, "name", self.__class__.__name__)}

    def initialize(self) -> dict:
        self._initialized = True
        return {"success": True, "module": getattr(self, "name", self.__class__.__name__)}

    def shutdown(self) -> dict:
        self._initialized = False
        return {"success": True, "module": getattr(self, "name", self.__class__.__name__)}

    async def status(self) -> dict:
        return {"name": getattr(self, "name", self.__class__.__name__), "status": "ok", "initialized": getattr(self, "_initialized", False)}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        try:
            if action in ("status", "info", "stats"):
                return self.health_check()
            elif action == "help":
                return {"actions": ["status", "help"], "module": getattr(self, "name", self.__class__.__name__)}
            return {"success": True, "action": action, "module": getattr(self, "name", self.__class__.__name__)}
        except Exception as e:
            return {"success": False, "error": str(e)}
