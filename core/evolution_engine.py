"""
AUTO-EVO-AI V0.1 — Adaptive Engine (自适应引擎)
基于执行数据的自适应优化系统

核心功能:
  1. 执行记录 + SQLite 持久化 (重启不丢)
  2. 模块评分 (成功率/延迟/错误趋势/使用频率)
  3. 自适应路由 (evo_brain 调用)
  4. 自修复 (degraded 时自动 reload)
  5. 优化建议

评分维度:
  success_rate: 成功率 (50%)
  avg_latency:  平均耗时 (20%)
  error_trend:  错误趋势 (15%)
  usage_freq:   使用频率 (15%)

自修复:
  连续 N 次失败 -> 标记 degraded -> 自动 reload 模块
  连续 M 分钟恢复 -> 标记 recovered
"""

import os
import sqlite3
import time
from core.logging_config import get_logger
import threading
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

logger = get_logger("adaptive_engine")

# ─── 常量 ────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adaptive_engine.db")
WEIGHT_SUCCESS_RATE = 0.50
WEIGHT_LATENCY      = 0.20
WEIGHT_ERROR_TREND  = 0.15
WEIGHT_USAGE_FREQ   = 0.15
DEGRADE_THRESHOLD   = 5
RECOVERY_WINDOW     = 300
HISTORY_MAX         = 200
TOP_N               = 5


class AdaptiveEngine:
    """自适应引擎 - 单例 + SQLite 持久化"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._mem_lock = threading.Lock()
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=HISTORY_MAX))
        self._states: Dict[str, Dict] = {}
        self._scoring_active = False
        self._scoring_thread: Optional[threading.Thread] = None
        # SQLite 初始化
        self._init_db()
        self._load_from_db()
        logger.info(f"[ADAPT] AdaptiveEngine initialized (DB: {DB_PATH})")

    # ════════════════════════════════════════════════════
    # SQLite 持久化
    # ════════════════════════════════════════════════════

    def _init_db(self):
        """创建/迁移 SQLite 表"""
        try:
            self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS evo_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL,
                    action TEXT DEFAULT '',
                    success INTEGER DEFAULT 1,
                    latency_ms REAL DEFAULT 0,
                    error TEXT DEFAULT '',
                    ts REAL DEFAULT (strftime('%%s','now'))
                );
                CREATE TABLE IF NOT EXISTS evo_scores (
                    module TEXT PRIMARY KEY,
                    score REAL DEFAULT 0,
                    success_rate REAL DEFAULT 0,
                    avg_latency_ms REAL DEFAULT 0,
                    total_calls INTEGER DEFAULT 0,
                    total_success INTEGER DEFAULT 0,
                    total_fails INTEGER DEFAULT 0,
                    consecutive_failures INTEGER DEFAULT 0,
                    state TEXT DEFAULT 'normal',
                    last_fail_time REAL DEFAULT 0,
                    state_changed REAL DEFAULT 0,
                    last_updated REAL DEFAULT (strftime('%%s','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_records_module ON evo_records(module);
                CREATE INDEX IF NOT EXISTS idx_records_ts ON evo_records(ts);
                CREATE TABLE IF NOT EXISTS evo_params (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL, action TEXT DEFAULT '',
                    params_json TEXT, total_calls INTEGER DEFAULT 0,
                    total_success INTEGER DEFAULT 0, avg_latency_ms REAL DEFAULT 0,
                    effectiveness REAL DEFAULT 0, last_used REAL DEFAULT (strftime('%%s','now')),
                    UNIQUE(module, action, params_json)
                );
                CREATE TABLE IF NOT EXISTS evo_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL, strategy_id TEXT, prompt_template TEXT,
                    total_calls INTEGER DEFAULT 0, total_success INTEGER DEFAULT 0,
                    effectiveness REAL DEFAULT 0, is_active INTEGER DEFAULT 1,
                    created REAL DEFAULT (strftime('%%s','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_params_module ON evo_params(module,action);
                CREATE INDEX IF NOT EXISTS idx_prompts_module ON evo_prompts(module);
            """)
            self._conn.commit()
            logger.info(f"[ADAPT] DB ready at {DB_PATH}")
        except Exception as e:
            logger.error(f"[ADAPT] DB init failed: {e}")
            self._conn = None

    def _persist_record(self, module: str, action: str, success: bool,
                        latency_ms: float, error: str):
        """写入执行记录到 SQLite"""
        if not self._conn:
            return
        try:
            self._conn.execute(
                "INSERT INTO evo_records(module,action,success,latency_ms,error,ts) VALUES(?,?,?,?,?,?)",
                (module, action, 1 if success else 0, latency_ms, error[:200], time.time())
            )
            # upsert 分数摘要
            self._conn.execute("""
                INSERT INTO evo_scores(module,score,success_rate,avg_latency_ms,
                    total_calls,total_success,total_fails,consecutive_failures,state,
                    last_fail_time,state_changed,last_updated)
                VALUES(?,0,0,0,1,?,?,0,'normal',0,?,?)
                ON CONFLICT(module) DO UPDATE SET
                    total_calls=total_calls+1,
                    total_success=total_success+?,
                    total_fails=total_fails+?,
                    last_updated=?
            """, (module, 1 if success else 0, 1 if not success else 0,
                  time.time(), time.time(),
                  1 if success else 0, 1 if not success else 0, time.time()))
            self._conn.commit()
        except Exception as e:
            logger.error(f"[ADAPT] persist error: {e}")

    def _load_from_db(self):
        """重启时从 SQLite 恢复历史记录和状态"""
        if not self._conn:
            return
        try:
            # 恢复最近记录到内存
            rows = self._conn.execute(
                "SELECT * FROM evo_records ORDER BY ts DESC LIMIT ?",
                (HISTORY_MAX,)
            ).fetchall()
            for row in reversed(rows):
                m = row["module"]
                rec = {
                    "ts": row["ts"],
                    "module": m,
                    "action": row["action"],
                    "success": bool(row["success"]),
                    "latency_ms": row["latency_ms"],
                    "error": row["error"] or "",
                    "context": {},
                }
                self._history[m].append(rec)
            # 恢复状态
            states = self._conn.execute("SELECT * FROM evo_scores").fetchall()
            for s in states:
                self._states[s["module"]] = {
                    "consecutive_failures": s["consecutive_failures"],
                    "last_fail_time": s["last_fail_time"],
                    "state": s["state"],
                    "total_calls": s["total_calls"],
                    "total_success": s["total_success"],
                    "total_fails": s["total_fails"],
                    "state_changed": s["state_changed"],
                }
            logger.info(f"[ADAPT] loaded {len(rows)} records, {len(states)} module states from DB")
        except Exception as e:
            logger.error(f"[ADAPT] load error: {e}")

    # ─── 记录接口 ───────────────────────────────────────

    def record(self, module: str, action: str, success: bool,
               latency_ms: float, error: str = "", context: dict = None) -> None:
        now = time.time()
        rec = {
            "ts": now, "module": module, "action": action,
            "success": success, "latency_ms": round(latency_ms, 2),
            "error": error[:200] if error else "", "context": context or {},
        }
        with self._mem_lock:
            self._history[module].append(rec)
            self._update_state(module, success, now)
        self._persist_record(module, action, success, latency_ms, error)
        self._try_auto_reload(module)
        logger.debug(f"[ADAPT] record {module}.{action} success={success} latency={latency_ms:.0f}ms")

    def _update_state(self, module: str, success: bool, now: float):
        st = self._states.get(module, {
            "consecutive_failures": 0, "last_fail_time": 0.0, "state": "normal",
            "total_calls": 0, "total_fails": 0, "total_success": 0, "state_changed": 0.0,
        })
        st["total_calls"] += 1
        if success:
            st["total_success"] += 1
            st["consecutive_failures"] = 0
            if st["state"] == "degraded" and (now - st["last_fail_time"]) > RECOVERY_WINDOW:
                st["state"] = "recovering"
                st["state_changed"] = now
                logger.info(f"[ADAPT] {module} recovering")
        else:
            st["total_fails"] += 1
            st["consecutive_failures"] += 1
            st["last_fail_time"] = now
            if st["consecutive_failures"] >= DEGRADE_THRESHOLD and st["state"] == "normal":
                st["state"] = "degraded"
                st["state_changed"] = now
                logger.warning(f"[ADAPT] {module} DEGRADED ({st['consecutive_failures']} fails)")
        self._states[module] = st

    # ─── 自修复 ────────────────────────────────────────

    def _try_auto_reload(self, module: str):
        """degraded 时尝试自动 reload 模块"""
        st = self._states.get(module)
        if not st or st.get("state") != "degraded":
            return
        try:
            from core.module_manager import module_manager as mm
            mm.reload_module(module)
            logger.info(f"[ADAPT] auto-reloaded {module}")
            st["state"] = "recovering"
            st["state_changed"] = time.time()
        except Exception as e:
            logger.warning(f"[ADAPT] auto-reload {module} failed: {e}")

    # ─── 评分 ───────────────────────────────────────────

    def score_module(self, module: str) -> Optional[Dict]:
        with self._mem_lock:
            records = list(self._history.get(module, []))
            state = self._states.get(module, {})
        if len(records) < 3:
            return None
        total = len(records)
        successes = sum(1 for r in records if r["success"])
        success_rate = successes / max(total, 1)
        avg_latency = sum(r["latency_ms"] for r in records) / max(total, 1)
        recent = records[-10:]
        recent_fails = sum(1 for r in recent if not r["success"])
        error_trend = recent_fails / max(len(recent), 1)
        one_hour_ago = time.time() - 3600
        freq_count = sum(1 for r in records if r["ts"] > one_hour_ago)
        latency_score = max(0, min(1, 1.0 - (avg_latency / 10000.0)))
        score = (
            success_rate * WEIGHT_SUCCESS_RATE +
            latency_score * WEIGHT_LATENCY +
            (1.0 - error_trend) * WEIGHT_ERROR_TREND +
            min(1.0, freq_count / 100.0) * WEIGHT_USAGE_FREQ
        )
        return {
            "module": module, "score": round(score, 4),
            "success_rate": round(success_rate, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "error_trend": round(error_trend, 4),
            "frequency_1h": freq_count,
            "state": state.get("state", "unknown"),
            "consecutive_failures": state.get("consecutive_failures", 0),
        }

    def ranking(self, top_n: int = TOP_N) -> List[Dict]:
        with self._mem_lock:
            modules = list(self._history.keys())
        scored = [s for m in modules if (s := self.score_module(m))]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

    def degraded_modules(self) -> List[Dict]:
        with self._mem_lock:
            return [{"module": k, **v} for k, v in self._states.items()
                    if v.get("state") in ("degraded",)]

    # ─── 优化建议 ───────────────────────────────────────

    def suggestions(self) -> List[Dict]:
        result = []
        with self._mem_lock:
            for module, st in self._states.items():
                if st.get("state") == "degraded":
                    result.append({
                        "type": "degraded", "module": module,
                        "message": f"{module} degraded ({st['consecutive_failures']} fails), auto-reload triggered",
                        "action": "auto_reload", "severity": "high",
                    })
                if st.get("total_calls", 0) > 50 and st.get("total_success", 0) / max(st["total_calls"], 1) < 0.5:
                    result.append({
                        "type": "low_success", "module": module,
                        "message": f"{module} success rate < 50%", "action": "audit", "severity": "medium",
                    })
        return result

    # ─── 后台评分 ───────────────────────────────────────

    def start_scoring_loop(self, interval_sec: int = 300):
        if self._scoring_active:
            return
        self._scoring_active = True
        def _loop():
            while self._scoring_active:
                self._run_scoring_cycle()
                time.sleep(interval_sec)
        self._scoring_thread = threading.Thread(target=_loop, daemon=True, name="evo-scoring")
        self._scoring_thread.start()
        logger.info(f"[ADAPT] scoring loop started ({interval_sec}s)")

    def stop_scoring_loop(self):
        self._scoring_active = False

    def _run_scoring_cycle(self):
        try:
            ranked = self.ranking(5)
            degraded = self.degraded_modules()
            logger.info(f"[ADAPT] cycle: {len(ranked)} ranked, {len(degraded)} degraded")
        except Exception as e:
            logger.error(f"[ADAPT] cycle error: {e}")

    # ─── 查询 ───────────────────────────────────────────

    def summary(self) -> Dict:
        with self._mem_lock:
            total_modules = len(self._history)
            total_records = sum(len(q) for q in self._history.values())
            states = {}
            for st in self._states.values():
                s = st.get("state", "unknown")
                states[s] = states.get(s, 0) + 1
        return {
            "modules_tracked": total_modules, "total_records": total_records,
            "state_distribution": states, "top_ranked": self.ranking(5),
            "suggestions": self.suggestions(),
        }

    def module_detail(self, module: str) -> Optional[Dict]:
        with self._mem_lock:
            records = list(self._history.get(module, []))[-20:]
            state = self._states.get(module, {})
        return {"module": module, "score": self.score_module(module), "state": state, "recent": records}

    def module_info(self, module: str) -> Optional[Dict]:
        return self.module_detail(module)

    # ════════════════════════════════════════════════════
    # 参数自进化
    # ════════════════════════════════════════════════════

    def record_params(self, module: str, action: str, params: dict,
                      success: bool, latency_ms: float):
        """记录某次调用的参数组合及效果"""
        key = (module, action, json.dumps(params, sort_keys=True))
        if not self._conn:
            return
        try:
            pj = json.dumps(params, sort_keys=True)
            self._conn.execute("""
                INSERT INTO evo_params(module,action,params_json,total_calls,total_success,avg_latency_ms,effectiveness,last_used)
                VALUES(?,?,?,1,?,?,0,?)
                ON CONFLICT(module,action,params_json) DO UPDATE SET
                    total_calls=total_calls+1,
                    total_success=total_success+?,
                    avg_latency_ms=(avg_latency_ms*(total_calls-1)+?)/total_calls,
                    last_used=?
            """, (module, action, pj, 1 if success else 0, latency_ms, time.time(),
                 1 if success else 0, latency_ms, time.time()))
            self._conn.commit()
            # 重新计算 effectiveness
            self._recalc_param_effectiveness(module, action, pj)
        except Exception as e:
            logger.warning(f"[ADAPT] record_params error: {e}")

    def _recalc_param_effectiveness(self, module: str, action: str, params_json: str):
        """计算参数组合的有效性得分"""
        try:
            row = self._conn.execute(
                "SELECT total_calls,total_success,avg_latency_ms FROM evo_params WHERE module=? AND action=? AND params_json=?",
                (module, action, params_json)
            ).fetchone()
            if not row or row["total_calls"] < 2:
                return
            tc = row["total_calls"]
            sr = row["total_success"] / max(tc, 1)
            latency = row["avg_latency_ms"]
            lat_score = max(0, 1.0 - latency / 5000.0)
            eff = sr * 0.6 + lat_score * 0.4
            self._conn.execute(
                "UPDATE evo_params SET effectiveness=? WHERE module=? AND action=? AND params_json=?",
                (round(eff, 4), module, action, params_json)
            )
            self._conn.commit()
        except Exception as e:
            logger.warning(f"[ADAPT] recalc eff error: {e}")

    def suggest_params(self, module: str, action: str = "") -> Optional[dict]:
        """返回该(module, action)下最高分的参数组合"""
        if not self._conn:
            return None
        try:
            rows = self._conn.execute(
                "SELECT params_json,effectiveness,total_calls FROM evo_params "
                "WHERE module=? AND action=? AND total_calls>=2 ORDER BY effectiveness DESC LIMIT 1",
                (module, action)
            ).fetchall()
            if rows:
                return {"params": json.loads(rows[0]["params_json"]),
                        "effectiveness": rows[0]["effectiveness"],
                        "total_calls": rows[0]["total_calls"]}
            # 尝试不指定 action
            if action:
                rows = self._conn.execute(
                    "SELECT params_json,effectiveness,total_calls FROM evo_params "
                    "WHERE module=? AND total_calls>=2 ORDER BY effectiveness DESC LIMIT 1",
                    (module,)
                ).fetchall()
                if rows:
                    return {"params": json.loads(rows[0]["params_json"]),
                            "effectiveness": rows[0]["effectiveness"],
                            "total_calls": rows[0]["total_calls"]}
        except Exception as e:
            logger.warning(f"[ADAPT] suggest_params error: {e}")
        return None

    def get_param_profiles(self, module: str) -> List[Dict]:
        """获取模块所有参数配置及其效果"""
        if not self._conn:
            return []
        try:
            rows = self._conn.execute(
                "SELECT action,params_json,total_calls,total_success,avg_latency_ms,effectiveness "
                "FROM evo_params WHERE module=? ORDER BY effectiveness DESC",
                (module,)
            ).fetchall()
            return [{"action": r["action"], "params": json.loads(r["params_json"]),
                      "calls": r["total_calls"], "success": r["total_success"],
                      "latency": r["avg_latency_ms"], "score": r["effectiveness"]} for r in rows]
        except Exception as e:
            logger.warning(f"[ADAPT] get_params error: {e}")
            return []

    def evolve_params(self):
        """参数进化：清除低效参数配置，保留高效变体"""
        if not self._conn:
            return
        try:
            # 清除 超过20次调用但 effectiveness<0.3 的配置
            deleted = self._conn.execute(
                "DELETE FROM evo_params WHERE total_calls>=20 AND effectiveness<0.3"
            ).rowcount
            if deleted:
                self._conn.commit()
                logger.info(f"[ADAPT] evolved: pruned {deleted} low-effectiveness param profiles")
        except Exception as e:
            logger.warning(f"[ADAPT] evolve error: {e}")

    # ─── 进化循环 ───────────────────────────────────────

    def start_evolution_loop(self, interval_sec: int = 600):
        """启动参数进化循环（默认每10分钟）"""
        if getattr(self, "_evo_active", False):
            return
        self._evo_active = True
        def _loop():
            while self._evo_active:
                time.sleep(interval_sec)
                try:
                    self.evolve_params()
                except Exception as e:
                    logger.warning(f"[ADAPT] evolution loop error: {e}")
        t = threading.Thread(target=_loop, daemon=True, name="evo-evolution")
        t.start()
        logger.info(f"[ADAPT] evolution loop started ({interval_sec}s)")

    def stop_evolution_loop(self):
        self._evo_active = False


# ─── 全局单例 ──────────────────────────────────────────
engine = AdaptiveEngine()
