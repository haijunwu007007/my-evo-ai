"""
AUTO-EVO-AI V0.1 — Evolution Engine 进化引擎
基于执行数据的自适应优化系统

原理：
  每条模块执行记录 -> 评分 -> 自适应路由 -> 自我修复 -> 优化建议

评分维度:
  success_rate: 成功率 (50%)
  avg_latency:  平均耗时 (20%)
  error_trend:  错误趋势 (15%)
  usage_freq:   使用频率 (15%)

自适应:
  evo_brain 查询引擎 -> 获取当前最优模块/路由策略
  失败时自动降级到次优模块

自我修复:
  连续 N 次失败 -> 标记 degraded -> 自动 reload 模块
  连续 M 分钟恢复 -> 标记 recovered
"""

import time
import json
import logging
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("evolution_engine")

# ─── 评分常量 ─────────────────────────────────────────
WEIGHT_SUCCESS_RATE = 0.50
WEIGHT_LATENCY      = 0.20
WEIGHT_ERROR_TREND  = 0.15
WEIGHT_USAGE_FREQ   = 0.15

DEGRADE_THRESHOLD   = 5    # 连续 N 次失败 -> degraded
RECOVERY_WINDOW     = 300  # 连续 N 秒无失败 -> recovered
HISTORY_MAX         = 200  # 单模块最多保留记录数
TOP_N               = 5    # 评分报告取 TOP N


class EvolutionEngine:
    """进化引擎 - 单例"""

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
        # module_name -> deque of record
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=HISTORY_MAX))
        # module_name -> { consecutive_failures, last_fail_time, state }
        self._states: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        # 定时评分线程
        self._scoring_active = False
        self._scoring_thread: Optional[threading.Thread] = None
        logger.info("[EVO] EvolutionEngine initialized")

    # ─── 记录接口 ───────────────────────────────────

    def record(
        self,
        module: str,
        action: str,
        success: bool,
        latency_ms: float,
        error: str = "",
        context: dict = None,
    ) -> None:
        """
        记录一次模块执行。
        - module:  模块名
        - action:  执行的 action
        - success: 是否成功
        - latency_ms: 耗时(ms)
        - error:   错误信息
        - context: 上下文(可选)
        """
        now = time.time()
        rec = {
            "ts": now,
            "module": module,
            "action": action,
            "success": success,
            "latency_ms": round(latency_ms, 2),
            "error": error[:200] if error else "",
            "context": context or {},
        }
        with self._lock:
            self._history[module].append(rec)
            self._update_state(module, success, now)
        logger.debug(f"[EVO] record {module}.{action} success={success} latency={latency_ms:.0f}ms")

    def _update_state(self, module: str, success: bool, now: float):
        """更新模块状态机"""
        st = self._states.get(module, {
            "consecutive_failures": 0,
            "last_fail_time": 0.0,
            "state": "normal",        # normal | degraded | recovering
            "total_calls": 0,
            "total_fails": 0,
            "total_success": 0,
            "state_changed": 0.0,
        })
        st["total_calls"] += 1
        if success:
            st["total_success"] += 1
            st["consecutive_failures"] = 0
            # 检查是否可恢复
            if st["state"] == "degraded" and (now - st["last_fail_time"]) > RECOVERY_WINDOW:
                st["state"] = "recovering"
                st["state_changed"] = now
                logger.info(f"[EVO] {module} recovering (no failures for {RECOVERY_WINDOW}s)")
        else:
            st["total_fails"] += 1
            st["consecutive_failures"] += 1
            st["last_fail_time"] = now
            if st["consecutive_failures"] >= DEGRADE_THRESHOLD and st["state"] == "normal":
                st["state"] = "degraded"
                st["state_changed"] = now
                logger.warning(f"[EVO] {module} DEGRADED ({st['consecutive_failures']} consecutive failures)")
        self._states[module] = st

    # ─── 评分 ───────────────────────────────────────

    def score_module(self, module: str) -> Optional[Dict]:
        """
        给模块打分，返回评分详情。
        如果模块记录不足 3 条，返回 None。
        """
        with self._lock:
            records = list(self._history.get(module, []))
            state = self._states.get(module, {})
        if len(records) < 3:
            return None

        total = len(records)
        successes = sum(1 for r in records if r["success"])
        failures = total - successes
        success_rate = successes / max(total, 1)
        avg_latency = sum(r["latency_ms"] for r in records) / max(total, 1)
        recent = records[-10:]
        recent_fails = sum(1 for r in recent if not r["success"])
        error_trend = recent_fails / max(len(recent), 1)

        # 使用频率: 最近 1 小时的总调用数 / 所有模块的最高调用数
        one_hour_ago = time.time() - 3600
        freq_count = sum(1 for r in records if r["ts"] > one_hour_ago)

        # 归一化延迟 (0~1, 1=最好)
        latency_score = max(0, min(1, 1.0 - (avg_latency / 10000.0)))

        # 综合评分
        score = (
            success_rate * WEIGHT_SUCCESS_RATE +
            latency_score * WEIGHT_LATENCY +
            (1.0 - error_trend) * WEIGHT_ERROR_TREND +
            min(1.0, freq_count / 100.0) * WEIGHT_USAGE_FREQ
        )

        return {
            "module": module,
            "score": round(score, 4),
            "success_rate": round(success_rate, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "error_trend": round(error_trend, 4),
            "frequency_1h": freq_count,
            "state": state.get("state", "unknown"),
            "consecutive_failures": state.get("consecutive_failures", 0),
            "last_fail_time": state.get("last_fail_time", 0),
        }

    def ranking(self, top_n: int = TOP_N) -> List[Dict]:
        """返回评分最高的 N 个模块"""
        with self._lock:
            modules = list(self._history.keys())
        scored = []
        for m in modules:
            s = self.score_module(m)
            if s:
                scored.append(s)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

    def degraded_modules(self) -> List[Dict]:
        """返回所有 degraded 状态的模块"""
        with self._lock:
            return [
                {"module": k, **v}
                for k, v in self._states.items()
                if v.get("state") in ("degraded",)
            ]

    # ─── 优化建议 ───────────────────────────────────

    def suggestions(self) -> List[Dict]:
        """生成优化建议"""
        suggestions_list = []
        with self._lock:
            for module, st in self._states.items():
                if st.get("state") == "degraded":
                    suggestions_list.append({
                        "type": "degraded",
                        "module": module,
                        "message": f"{module} degraded ({st['consecutive_failures']} consecutive failures), consider restarting",
                        "action": "restart",
                        "severity": "high",
                    })
                if st.get("total_calls", 0) > 50 and st.get("total_success", 0) / max(st["total_calls"], 1) < 0.5:
                    suggestions_list.append({
                        "type": "low_success",
                        "module": module,
                        "message": f"{module} success rate < 50%, consider review",
                        "action": "audit",
                        "severity": "medium",
                    })
        return suggestions_list

    # ─── 定期评分报告（后台线程） ───────────────────

    def start_scoring_loop(self, interval_sec: int = 300):
        """启动后台评分循环"""
        if self._scoring_active:
            return
        self._scoring_active = True

        def _loop():
            while self._scoring_active:
                self._run_scoring_cycle()
                time.sleep(interval_sec)

        self._scoring_thread = threading.Thread(target=_loop, daemon=True, name="evo-scoring")
        self._scoring_thread.start()
        logger.info(f"[EVO] scoring loop started (interval={interval_sec}s)")

    def stop_scoring_loop(self):
        self._scoring_active = False

    def _run_scoring_cycle(self):
        """执行一轮评分+优化"""
        try:
            ranked = self.ranking(5)
            degraded = self.degraded_modules()
            logger.info(f"[EVO] scoring cycle: {len(ranked)} ranked, {len(degraded)} degraded")
        except Exception as e:
            logger.error(f"[EVO] scoring cycle error: {e}")

    # ─── 状态查询 -------------------------------

    def summary(self) -> Dict:
        """返回引擎概要"""
        with self._lock:
            total_modules = len(self._history)
            total_records = sum(len(q) for q in self._history.values())
            states = {}
            for st in self._states.values():
                s = st.get("state", "unknown")
                states[s] = states.get(s, 0) + 1
        return {
            "modules_tracked": total_modules,
            "total_records": total_records,
            "state_distribution": states,
            "top_ranked": self.ranking(5),
            "suggestions": self.suggestions(),
        }

    def module_detail(self, module: str) -> Optional[Dict]:
        """返回模块的详细进化数据"""
        with self._lock:
            records = list(self._history.get(module, []))[-20:]
            state = self._states.get(module, {})
        score = self.score_module(module)
        return {
            "module": module,
            "score": score,
            "state": state,
            "recent": [
                {
                    "ts": r["ts"],
                    "action": r["action"],
                    "success": r["success"],
                    "latency_ms": r["latency_ms"],
                    "error": r.get("error", ""),
                }
                for r in records
            ],
        }


# ─── 全局单例 ──────────────────────────────────────
engine = EvolutionEngine()
