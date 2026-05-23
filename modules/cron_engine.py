import time

"""
AUTO-EVO-AI - Cron调度引擎 v3.0
版本: V0.1 | 自研 + APScheduler集成
功能: 真实定时调度( cron / interval / date )、任务链、超时控制、错误回调、持久化
降级: APScheduler不可用时自动切换到线程池手动轮询模式
"""

__module_meta__ = {
    "id": "cron-engine",
    "name": "Cron Engine",
    "version": "1.0.0",
    "group": "scheduler",
    "inputs": [
        {"name": "data_dir", "type": "string", "required": True, "description": ""},
        {"name": "scheduler_type", "type": "string", "required": True, "description": ""},
        {"name": "action", "type": "string", "required": True, "description": ""},
        {"name": "detail", "type": "string", "required": True, "description": ""},
        {"name": "success", "type": "string", "required": True, "description": ""},
        {"name": "expression", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [{"type": "schedule", "config": {"cron": "0 0 * * *"}}],
    "depends_on": [],
    "tags": ["engine", "cron"],
    "grade": "C",
    "description": "AUTO-EVO-AI - Cron调度引擎 v3.0 版本: V0.1 | 自研 + APScheduler集成",
}
import json, os, re, time, threading, traceback, logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger(__name__)

# ─── 延迟导入 APScheduler ─────────────────────────────────
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False
    logger.warning("APScheduler未安装，将使用手动轮询模式 (pip install apscheduler)")

class CronEngine(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """Cron调度引擎 - 支持真实定时调度"""

    VERSION = "V0.1"
    MODE_APSCHEDULER = "apscheduler"
    MODE_MANUAL = "manual"

    def __init__(self, data_dir: str = ".evo_data/cron", scheduler_type: str = "apscheduler"):

        super().__init__()
        self.metrics_collector = self._NoopMetricsCollector()

        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.scheduler_type = scheduler_type if scheduler_type == "apscheduler" else "manual"
        self._jobs: Dict[str, Dict] = {}  # name -> job config
        self._handlers: Dict[str, Callable] = {}  # name -> callable handler
        self._history: List[Dict] = []
        self._error_callbacks: List[Callable] = []
        self._started = False
        self._scheduler = None
        self._manual_thread = None
        self._manual_stop = threading.Event()

        # 启动时加载持久化的jobs
        self._load_jobs()

    # ─── 持久化 ─────────────────────────────────────────
    def _jobs_file(self) -> str:
        return os.path.join(self.data_dir, "jobs.json")

    def _load_jobs(self):
        fp = self._jobs_file()
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, cfg in data.get("jobs", {}).items():
                    self._jobs[name] = cfg
                logger.info(f"从 {fp} 加载了 {len(self._jobs)} 个任务")
            except Exception as e:
                logger.warning(f"加载任务失败: {e}")

    def _save_jobs(self):
        fp = self._jobs_file()
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump({"jobs": self._jobs, "saved_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务失败: {e}")

    def _log(self, action: str, detail: str = "", success: bool = True):
        entry = {"action": action, "detail": detail, "time": datetime.now().isoformat(), "success": success}
        self._history.append(entry)
        if len(self._history) > 10000:
            self._history = self._history[-5000:]

    # ─── Cron表达式解析 ─────────────────────────────────
    def parse_cron(self, expression: str) -> Dict:
        """验证和解析标准5字段Cron表达式 (分 时 日 月 周)"""
        try:
            parts = expression.strip().split()
            if len(parts) != 5:
                return {"success": False, "valid": False, "error": "需要5个字段: 分 时 日 月 周"}
            names = ["minute", "hour", "day", "month", "weekday"]
            parsed = {}
            for name, part in zip(names, parts):
                if part == "*":
                    parsed[name] = "*"
                elif re.match(r"^[\d,\-\/]+$", part):
                    parsed[name] = part
                else:
                    return {"success": False, "valid": False, "error": f"{name} 格式错误: {part}"}
            return {"success": True, "valid": True, "parsed": parsed, "human_readable": self._describe(parsed)}
        except Exception as e:
            return {"success": False, "valid": False, "error": str(e)}

    def _describe(self, parsed: Dict) -> str:
        h, m, wd = parsed.get("hour", "*"), parsed.get("minute", "*"), parsed.get("weekday", "*")
        if h == "*" and m == "*":
            return "每分钟执行"
        if wd != "*":
            day_names = {"0": "周日", "1": "周一", "2": "周二", "3": "周三", "4": "周四", "5": "周五", "6": "周六"}
            wd_text = day_names.get(wd, wd)
            return f"每{wd_text} {h}:{m} 执行"
        return f"每天 {h}:{m} 执行"

    # ─── 任务管理 ──────────────────────────────────────
    def add_job(
        self,
        name: str,
        trigger_type: str = "cron",
        trigger_expr: str = "*/5 * * * *",
        handler: Optional[Callable] = None,
        description: str = "",
        misfire_grace_time: int = 60,
        max_instances: int = 1,
        coalesce: bool = True,
        timeout: int = 0,
        chain: Optional[List[str]] = None,
        replace: bool = True,
    ) -> Dict:
        """
        添加调度任务
        Args:
            name: 任务唯一名称
            trigger_type: cron / interval / date
            trigger_expr: cron表达式 | "interval:秒数" | ISO日期时间
            handler: 可调用对象
            description: 描述
            misfire_grace_time: 错过执行的宽限时间(秒)
            max_instances: 最大并发实例数
            coalesce: 是否合并错过的执行
            timeout: 超时秒数(0=不限)
            chain: 任务链 - 完成后触发的下一个任务名列表
            replace: 同名任务是否替换
        """
        if name in self._jobs and not replace:
            return {"success": False, "error": f"任务 {name} 已存在"}

        # 验证cron表达式
        if trigger_type == "cron":
            validation = self.parse_cron(trigger_expr)
            if not validation["valid"]:
                return validation

        # 解析触发器
        trigger_config = self._build_trigger(trigger_type, trigger_expr)

        job = {
            "name": name,
            "trigger_type": trigger_type,
            "trigger_expr": trigger_expr,
            "description": description,
            "status": "active",
            "misfire_grace_time": misfire_grace_time,
            "max_instances": max_instances,
            "coalesce": coalesce,
            "timeout": timeout,
            "chain": chain or [],
            "last_run": None,
            "next_run": None,
            "run_count": 0,
            "fail_count": 0,
            "created": datetime.now().isoformat(),
        }
        self._jobs[name] = job
        if handler:
            self._handlers[name] = handler

        # 如果调度器已启动，立即注册
        if self._started:
            self._register_to_scheduler(job)

        self._save_jobs()
        self._log("add_job", f"{name} [{trigger_type}] {trigger_expr}")
        return {"success": True, "job": name, "trigger_type": trigger_type, "expr": trigger_expr}

    def _build_trigger(self, trigger_type: str, expr: str) -> Dict:
        if trigger_type == "cron":
            parts = expr.split()
            return {
                "type": "cron",
                "minute": parts[0],
                "hour": parts[1],
                "day": parts[2],
                "month": parts[3],
                "weekday": parts[4],
            }
        elif trigger_type == "interval":
            seconds = int(expr.split(":")[-1]) if ":" in expr else int(expr)
            return {"type": "interval", "seconds": seconds}
        elif trigger_type == "date":
            return {"type": "date", "run_date": expr}
        return {"type": "cron", "minute": "*", "hour": "*", "day": "*", "month": "*", "weekday": "*"}

    def remove_job(self, name: str) -> Dict:
        if name not in self._jobs:
            return {"success": False, "error": "任务不存在"}
        if self._started and self._scheduler:
            try:
                self._scheduler.remove_job(name)
            except Exception:
                pass
        del self._jobs[name]
        self._handlers.pop(name, None)
        self._save_jobs()
        self._log("remove_job", name)
        return {"success": True}

    def pause_job(self, name: str) -> Dict:
        job = self._jobs.get(name)
        if not job:
            return {"success": False, "error": "任务不存在"}
        job["status"] = "paused"
        if self._started and self._scheduler:
            try:
                self._scheduler.pause_job(name)
            except Exception:
                pass
        self._save_jobs()
        return {"success": True}

    def resume_job(self, name: str) -> Dict:
        job = self._jobs.get(name)
        if not job:
            return {"success": False, "error": "任务不存在"}
        job["status"] = "active"
        if self._started and self._scheduler:
            try:
                self._scheduler.resume_job(name)
            except Exception:
                pass
        self._save_jobs()
        return {"success": True}

    def run_job(self, name: str) -> Dict:
        """手动立即执行任务"""
        job = self._jobs.get(name)
        if not job:
            return {"success": False, "error": "任务不存在"}
        return self._execute_job(job)

    def _execute_job(self, job: Dict) -> Dict:
        """执行单个任务(含超时控制)"""
        name = job["name"]
        handler = self._handlers.get(name)
        timeout = job.get("timeout", 0)

        job["last_run"] = datetime.now().isoformat()
        job["run_count"] += 1

        if not handler:
            self._log("run_job", f"{name}: 无handler，跳过", success=True)
            self._save_jobs()
            return {"success": True, "job": name, "note": "no_handler", "run_count": job["run_count"]}

        def _run():
            try:
                result = handler()
                self._log("run_job", f"{name}: 成功", success=True)
                # 执行任务链
                for next_name in job.get("chain", []):
                    next_job = self._jobs.get(next_name)
                    if next_job:
                        logger.info(f"任务链: {name} -> {next_name}")
                        self._execute_job(next_job)
                return {"success": True, "result": str(result)[:500]}
            except Exception as e:
                job["fail_count"] = job.get("fail_count", 0) + 1
                self._log("run_job", f"{name}: 失败 - {e}", success=False)
                for cb in self._error_callbacks:
                    try:
                        cb(name, e)
                    except Exception:
                        pass
                return {"success": False, "error": str(e)}

        if timeout > 0:
            result_container = {}

            def _run_with_timeout():
                result_container["r"] = _run()

            t = threading.Thread(target=_run_with_timeout, daemon=True)
            t.start()
            t.join(timeout=timeout)
            if t.is_alive():
                self._log("run_job", f"{name}: 超时({timeout}s)", success=False)
                return {"success": False, "error": f"任务超时({timeout}秒)"}
            return result_container.get("r", {"success": False, "error": "未知"})
        else:
            result = _run()
            self._save_jobs()
            return result

    # ─── APScheduler 调度器 ──────────────────────────────
    def _register_to_scheduler(self, job: Dict):
        """将任务注册到调度器"""
        if not self._scheduler or job.get("status") != "active":
            return

        name = job["name"]
        trigger_type = job["trigger_type"]
        trigger_expr = job["trigger_expr"]

        try:
            if trigger_type == "cron" and _HAS_APSCHEDULER:
                parts = trigger_expr.split()
                trigger = CronTrigger(
                    minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4]
                )
                self._scheduler.add_job(
                    self._execute_job,
                    trigger,
                    id=name,
                    args=[job],
                    misfire_grace_time=job.get("misfire_grace_time", 60),
                    max_instances=job.get("max_instances", 1),
                    coalesce=job.get("coalesce", True),
                    replace_existing=True,
                )
            elif trigger_type == "interval" and _HAS_APSCHEDULER:
                seconds = int(trigger_expr.split(":")[-1]) if ":" in trigger_expr else int(trigger_expr)
                trigger = IntervalTrigger(seconds=seconds)
                self._scheduler.add_job(
                    self._execute_job,
                    trigger,
                    id=name,
                    args=[job],
                    max_instances=job.get("max_instances", 1),
                    replace_existing=True,
                )
            elif trigger_type == "date" and _HAS_APSCHEDULER:
                trigger = DateTrigger(run_date=trigger_expr)
                self._scheduler.add_job(self._execute_job, trigger, id=name, args=[job], replace_existing=True)
        except Exception as e:
            logger.error(f"注册任务到调度器失败 [{name}]: {e}")

    # ─── 手动轮询模式 ──────────────────────────────────
    def _manual_loop(self):
        """手动轮询线程 - 每秒检查是否有任务需要执行"""
        logger.info("手动轮询模式启动")
        while not self._manual_stop.is_set():
            now = datetime.now()
            for name, job in self._jobs.items():
                if job.get("status") != "active":
                    continue
                next_run = self._calc_next_run_manual(job, now)
                if next_run and next_run <= now:
                    job["next_run"] = self._calc_next_run_manual(job, now + timedelta(seconds=1))
                    threading.Thread(target=self._execute_job, args=(job,), daemon=True).start()
            self._manual_stop.wait(1.0)
        logger.info("手动轮询模式停止")

    def _calc_next_run_manual(self, job: Dict, after: datetime) -> Optional[datetime]:
        """计算下次执行时间(简化版cron匹配)"""
        tt = job["trigger_type"]
        expr = job["trigger_expr"]

        if tt == "interval":
            seconds = int(expr.split(":")[-1]) if ":" in expr else int(expr)
            last = job.get("last_run")
            if last:
                last_dt = datetime.fromisoformat(last)
                return last_dt + timedelta(seconds=seconds)
            return after
        elif tt == "cron":
            parts = expr.split()
            if len(parts) != 5:
                return None
            min_part, hour_part, day_part, month_part, wd_part = parts
            now = after + timedelta(minutes=1)
            now = now.replace(second=0, microsecond=0)
            for _ in range(525600):  # 最多搜索1年
                if (
                    (min_part == "*" or now.minute == int(min_part))
                    and (hour_part == "*" or now.hour == int(hour_part))
                    and (day_part == "*" or now.day == int(day_part))
                    and (month_part == "*" or now.month == int(month_part))
                    and (wd_part == "*" or now.weekday() in [int(x) for x in wd_part.split(",")])
                ):
                    return now
                now += timedelta(minutes=1)
            return None
        elif tt == "date":
            try:
                return datetime.fromisoformat(expr)
            except Exception:
                return None
        return None

    # ─── 启动/停止 ──────────────────────────────────────
    def start(self) -> Dict:
        """启动调度器"""
        if self._started:
            return {"success": False, "error": "调度器已在运行"}

        active_jobs = {k: v for k, v in self._jobs.items() if v.get("status") == "active"}

        if _HAS_APSCHEDULER and self.scheduler_type == self.MODE_APSCHEDULER:
            self._scheduler = BackgroundScheduler()
            self._scheduler.add_listener(self._on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
            for name, job in active_jobs.items():
                self._register_to_scheduler(job)
            self._scheduler.start()
            self._started = True
            logger.info(f"APScheduler调度器已启动, 注册了 {len(active_jobs)} 个任务")
        else:
            self._manual_stop.clear()
            self._manual_thread = threading.Thread(target=self._manual_loop, daemon=True)
            self._manual_thread.start()
            self._started = True
            logger.info(f"手动轮询调度器已启动, 监控 {len(active_jobs)} 个任务")

        return {
            "success": True,
            "mode": "apscheduler" if (_HAS_APSCHEDULER and self.scheduler_type == self.MODE_APSCHEDULER) else "manual",
            "jobs": len(active_jobs),
        }

    def stop(self) -> Dict:
        """停止调度器"""
        if not self._started:
            return {"success": False, "error": "调度器未运行"}

        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        if self._manual_thread:
            self._manual_stop.set()
            self._manual_thread.join(timeout=5)
            self._manual_thread = None

        self._started = False
        self._save_jobs()
        self._log("stop_scheduler", "调度器已停止")
        return {"success": True}

    def _on_job_event(self, event):
        """APScheduler事件监听"""
        if event.exception:
            logger.error(f"任务 {event.job_id} 执行异常: {event.exception}")
            self._log("job_error", f"{event.job_id}: {event.exception}", success=False)
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"任务 {event.job_id} 错过了执行窗口")

    # ─── 错误回调 ──────────────────────────────────────
    def on_error(self, callback: Callable):
        """注册全局错误回调 callback(job_name, exception)"""
        self._error_callbacks.append(callback)

    # ─── 查询 ──────────────────────────────────────────
    def get_next_run_time(self, name: str) -> Optional[str]:
        job = self._jobs.get(name)
        if not job:
            return None
        if self._scheduler and _HAS_APSCHEDULER:
            try:
                sched_job = self._scheduler.get_job(name)
                if sched_job and sched_job.next_run_time:
                    return sched_job.next_run_time.isoformat()
            except Exception:
                pass
        if not job.get("next_run"):
            job["next_run"] = self._calc_next_run_manual(job, datetime.now())
            if job["next_run"]:
                return job["next_run"].isoformat()
        return job.get("next_run")

    def get_job_history(self, name: str, limit: int = 50) -> List[Dict]:
        return [h for h in self._history if name in h.get("detail", "") or name in h.get("action", "")][-limit:]

    def list_jobs(self) -> Dict:
        jobs_list = []
        for name, job in self._jobs.items():
            info = dict(job)
            info["has_handler"] = name in self._handlers
            info["next_run"] = self.get_next_run_time(name)
            jobs_list.append(info)
        return {"success": True, "jobs": jobs_list, "count": len(jobs_list), "scheduler_running": self._started}

    def get_stats(self) -> Dict:
        active = sum(1 for j in self._jobs.values() if j.get("status") == "active")
        total_runs = sum(j.get("run_count", 0) for j in self._jobs.values())
        total_fails = sum(j.get("fail_count", 0) for j in self._jobs.values())
        return {
            "total_jobs": len(self._jobs),
            "active_jobs": active,
            "paused_jobs": len(self._jobs) - active,
            "total_runs": total_runs,
            "total_failures": total_fails,
            "with_handlers": len(self._handlers),
            "scheduler_running": self._started,
            "mode": "apscheduler" if (_HAS_APSCHEDULER and self.scheduler_type == self.MODE_APSCHEDULER) else "manual",
            "operations": len(self._history),
            "version": self.VERSION,
        }

    def health_check(self) -> Dict:
        return {"healthy": True, "running": self._started, "jobs_count": len(self._jobs), "version": self.VERSION}

    # ─── 便捷函数 ──────────────────────────────────────────

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口"""
        params = params or {}
        self.trace("cron_engine.execute", "start", action=action)
        self.metrics_collector.counter("cron_engine.execute.total", 1)
        try:
            action = action.lower().strip()
            if action in ("status", "info", "stats"):
                result = self.health_check()
            elif action == "analyze":
                result = self._analyzer.analyze(params)
            elif action == "help":
                result = {"actions": ["status", "analyze", "help"], "module": "cron_engine"}
            else:
                result = {"success": True, "action": action, "module": "cron_engine", "note": "use status/analyze/help"}
            self.metrics_collector.counter("cron_engine.execute.success", 1)
            self.trace("cron_engine.execute", "end")
            return result
        except Exception as e:
            self.metrics_collector.counter("cron_engine.execute.error", 1)
            self.trace("cron_engine.execute", "error", error=str(e))
            return {"success": False, "error": str(e)}

    # --- Auto-generated action dispatch methods ---
    def _action_add_job(self, params=None):
        """Auto-generated action wrapper for add_job"""
        if params is None:
            params = {}
        return self.add_job(**params)

    def _action_get_job_history(self, params=None):
        """Auto-generated action wrapper for get_job_history"""
        if params is None:
            params = {}
        return self.get_job_history(**params)

    def _action_get_next_run_time(self, params=None):
        """Auto-generated action wrapper for get_next_run_time"""
        if params is None:
            params = {}
        return self.get_next_run_time(**params)

    def _action_get_stats(self, params=None):
        """Auto-generated action wrapper for get_stats"""
        if params is None:
            params = {}
        return self.get_stats(**params)

    def _action_list_jobs(self, params=None):
        """Auto-generated action wrapper for list_jobs"""
        if params is None:
            params = {}
        return self.list_jobs(**params)

    def _action_on_error(self, params=None):
        """Auto-generated action wrapper for on_error"""
        if params is None:
            params = {}
        return self.on_error(**params)

    def _action_parse_cron(self, params=None):
        """Auto-generated action wrapper for parse_cron"""
        if params is None:
            params = {}
        return self.parse_cron(**params)

    def _action_pause_job(self, params=None):
        """Auto-generated action wrapper for pause_job"""
        if params is None:
            params = {}
        return self.pause_job(**params)

    def _action_remove_job(self, params=None):
        """Auto-generated action wrapper for remove_job"""
        if params is None:
            params = {}
        return self.remove_job(**params)

    def _action_resume_job(self, params=None):
        """Auto-generated action wrapper for resume_job"""
        if params is None:
            params = {}
        return self.resume_job(**params)

    def _action_run_job(self, params=None):
        """Auto-generated action wrapper for run_job"""
        if params is None:
            params = {}
        return self.run_job(**params)

    def _action_start(self, params=None):
        """Auto-generated action wrapper for start"""
        if params is None:
            params = {}
        return self.start(**params)

    def _action_stop(self, params=None):
        """Auto-generated action wrapper for stop"""
        if params is None:
            params = {}
        return self.stop(**params)

_engine_instance = None

def get_engine() -> CronEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = CronEngine()
    return _engine_instance

    def shutdown(self) -> dict:
        """优雅关闭"""
        self.trace("cron_engine.shutdown", "start")
        self.status = "stopped"
        self.trace("cron_engine.shutdown", "end")
        return {"success": True, "module": "cron_engine"}

    def health_check(self) -> dict:
        return {
            "status": "healthy",
            "module": "cron_engine",
            "version": getattr(self, "version", "1.0.0"),
        }

    def initialize(self) -> dict:
        self.trace("cron_engine.initialize", "start")
        self.metrics_collector.gauge("cron_engine.initialized", 1)
        self.audit("初始化cron_engine", level="info")
        self.trace("cron_engine.initialize", "end")
        return {"success": True, "module": "cron_engine"}

module_class = CronEngine
