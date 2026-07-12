"""
AUTO-EVO-AI V0.1 — 推荐系统：协同过滤
"""
VERSION = "V0.1"
__module_meta__ = {"id": "recommend", "name": "RecommendationSystem", "version": VERSION, "group": "ai"}

import json, math, time, statistics
from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._persist import PersistMixin

class RecommendationSystem(PersistMixin, EnterpriseModule):
    MODULE_ID = "recommend"; MODULE_NAME = "RecommendationSystem"
    
    def __init__(self, config=None):
        EnterpriseModule.__init__(self, config or {})
        PersistMixin.__init__(self, "recommend")
        self._users = {}
        self._items = {}
    
    def get_status(self): return {"users": len(self._users), "items": len(self._items)}
    
    def execute(self, action, **kwargs):
        if action == "rate":
            user = kwargs.get("user", "")
            item = kwargs.get("item", "")
            rating = kwargs.get("rating", 0)
            if user not in self._users: self._users[user] = {}
            self._users[user][item] = rating
            self.persist(f"rating:{user}:{item}", json.dumps({"user":user,"item":item,"rating":rating}))
            return {"user": user, "item": item, "rating": rating}
        if action == "recommend":
            user = kwargs.get("user", "")
            n = kwargs.get("count", 5)
            if user not in self._users: return {"error": "user not found", "suggestions": ["请先评分"]}
            # Simple collaborative: find similar users
            known = set(self._users[user].keys())
            scores = {}
            for u, ratings in self._users.items():
                if u == user: continue
                common = known & set(ratings.keys())
                if not common: continue
                sim = len(common) / math.sqrt(len(known) * len(ratings))
                for item, r in ratings.items():
                    if item not in known:
                        scores[item] = scores.get(item, 0) + sim * r / len(common)
            ranked = sorted(scores.items(), key=lambda x: -x[1])[:n]
            return {"recommendations": [{"item": item, "score": round(score, 3)} for item, score in ranked]}
        if action == "popular":
            counts = {}
            for user, ratings in self._users.items():
                for item in ratings:
                    counts[item] = counts.get(item, 0) + 1
            ranked = sorted(counts.items(), key=lambda x: -x[1])[:10]
            return {"popular": [{"item": item, "users": c} for item, c in ranked]}
        return {"error": "unknown: " + str(action)}
