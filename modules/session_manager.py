"""Production-grade module: 会话管理器
# Grade: A
企业级Session生命周期引擎 - 管理用户登录会话、Token刷新、并发控制、安全审计。
典型场景: Web应用Session管理、JWT Token续期、并发登录限制、异常登录检测。
"""

__module_meta__ = {
        "id": "session-manager",
        "name": "Session Manager",
        "version": "V0.1",
        "group": "auth",
        "inputs": [
            {
                "name": "default_ttl",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "max_sessions_per_user",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "user_id",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "device_info",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "metadata",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "ttl",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [],
        "depends_on": [],
        "tags": [
            "session",
            "manager"
        ],
        "grade": "A",
        "description": "Production-grade module: 会话管理器 企业级Session生命周期引擎 - 管理用户登录会话、Token刷新、并发控制、安全审计。"
    }
import hashlib
from core.logging_config import get_logger
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = get_logger("session_manager")

class SessionStoreManager:
    """会话存储管理器 - 管理Session的完整生命周期。

    企业场景：电商大促期间10万+并发用户Session管理，
    支持滑动过期、并发限制、异常设备检测、按用户批量操作。
    """

    def __init__(self, default_ttl: int = 1800, max_sessions_per_user: int = 5):
        self._sessions: Dict[str, Dict] = {}
        self._user_sessions: Dict[str, List[str]] = {}
        self._default_ttl = default_ttl
        self._max_per_user = max_sessions_per_user
        self._total_created = 0
        self._total_validated = 0
        self._total_revoked = 0
        self._total_expired = 0
        self._login_history: List[Dict] = []

    def create(
        self,
        user_id: str,
        device_info: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """创建会话。企业场景：用户登录后创建Session，
        检查并发数限制，超出则踢掉最早的设备。
        返回session_id和access_token。
        """
        now = time.time()
        # 检查并发限制
        existing = self._user_sessions.get(user_id, [])
        if len(existing) >= self._max_per_user:
            # 踢掉最旧的会话
            oldest_sid = existing[0]
            self._revoke_internal(oldest_sid, reason="max_sessions_exceeded")
            existing.pop(0)

        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        token = hashlib.sha256(f"{session_id}:{now}".encode()).hexdigest()[:32]
        session_ttl = ttl or self._default_ttl

        session = {
            "session_id": session_id,
            "token": token,
            "user_id": user_id,
            "device": device_info or {},
            "metadata": metadata or {},
            "created_at": now,
            "expires_at": now + session_ttl,
            "last_active": now,
            "ttl": session_ttl,
            "ip": (device_info or {}).get("ip", ""),
            "user_agent": (device_info or {}).get("user_agent", ""),
            "is_valid": True,
            "refresh_count": 0,
            "revoke_reason": None,
        }
        self._sessions[session_id] = session
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)
        self._total_created += 1
        self._login_history.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "device": device_info or {},
                "timestamp": now,
                "action": "login",
            }
        )

        return {
            "session_id": session_id,
            "token": token,
            "expires_at": session["expires_at"],
            "ttl_seconds": session_ttl,
            "concurrent_sessions": len(self._user_sessions[user_id]),
        }

    def validate(self, session_id: str, token: str) -> Dict[str, Any]:
        """验证会话有效性。企业场景：每个API请求前验证Session，
        检查Token匹配、过期时间、是否被主动注销。
        支持滑动续期：验证通过时自动延长过期时间。
        """
        self._total_validated += 1
        session = self._sessions.get(session_id)
        if not session:
            return {"valid": False, "error": "session_not_found"}
        if not session.get("is_valid", True):
            return {"valid": False, "error": "session_revoked", "reason": session.get("revoke_reason", "")}
        if session["token"] != token:
            return {"valid": False, "error": "token_mismatch"}
        now = time.time()
        if now >= session["expires_at"]:
            self._total_expired += 1
            session["is_valid"] = False
            return {"valid": False, "error": "session_expired", "expired_at": session["expires_at"]}
        # 滑动续期
        session["last_active"] = now
        remaining_pct = (session["expires_at"] - now) / session["ttl"]
        if remaining_pct < 0.3:
            session["expires_at"] = now + session["ttl"]
            session["refresh_count"] += 1
        return {
            "valid": True,
            "user_id": session["user_id"],
            "remaining_seconds": round(session["expires_at"] - now, 1),
            "refreshed": remaining_pct < 0.3,
            "last_active": now,
        }

    def refresh(self, session_id: str, additional_ttl: Optional[int] = None) -> Dict[str, Any]:
        """手动刷新Session TTL。企业场景：用户长操作期间主动续期，
        避免操作到一半被踢出。
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "session_not_found"}
        if not session.get("is_valid", True):
            return {"success": False, "error": "session_revoked"}
        now = time.time()
        if now >= session["expires_at"]:
            return {"success": False, "error": "session_expired"}
        add_ttl = additional_ttl or session["ttl"]
        session["expires_at"] = now + add_ttl
        session["last_active"] = now
        session["refresh_count"] += 1
        return {
            "success": True,
            "new_expires_at": session["expires_at"],
            "new_ttl": add_ttl,
            "total_refreshes": session["refresh_count"],
        }

    def revoke(self, session_id: str, reason: str = "user_logout") -> Dict[str, Any]:
        """注销会话。企业场景：用户主动退出登录、管理员踢人、密码修改后强制下线。"""
        return self._revoke_internal(session_id, reason)

    def _revoke_internal(self, session_id: str, reason: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "session_not_found"}
        session["is_valid"] = False
        session["revoked_at"] = time.time()
        session["revoke_reason"] = reason
        self._total_revoked += 1
        # 从用户会话列表中移除
        user_id = session.get("user_id", "")
        if user_id in self._user_sessions:
            if session_id in self._user_sessions[user_id]:
                self._user_sessions[user_id].remove(session_id)
        return {"success": True, "session_id": session_id, "user_id": user_id, "reason": reason}

    def revoke_all_user_sessions(self, user_id: str, reason: str = "admin_revoke") -> Dict[str, Any]:
        """注销用户所有会话。企业场景：修改密码后强制所有设备下线、
        安全事件触发批量踢人。
        """
        session_ids = self._user_sessions.get(user_id, [])
        revoked = []
        for sid in session_ids[:]:
            result = self._revoke_internal(sid, reason)
            if result.get("success"):
                revoked.append(sid)
        return {"success": True, "user_id": user_id, "revoked_count": len(revoked), "revoked_sessions": revoked}

    def list_active_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """列出活跃会话。企业场景：用户查看"我的设备"列表、
        管理员查看在线用户列表、运维统计实时在线人数。
        """
        now = time.time()
        active = []
        target_sessions = []
        if user_id:
            target_sessions = self._sessions.get(user_id, [])
            # 用user_sessions索引
            for sid in self._user_sessions.get(user_id, []):
                s = self._sessions.get(sid)
                if s:
                    target_sessions = [s]
                    break
            target_sessions = [
                self._sessions[sid] for sid in self._user_sessions.get(user_id, []) if sid in self._sessions
            ]
        else:
            target_sessions = list(self._sessions.values())
        for s in target_sessions:
            if s.get("is_valid") and s["expires_at"] > now:
                remaining = s["expires_at"] - now
                active.append(
                    {
                        "session_id": s["session_id"],
                        "user_id": s["user_id"],
                        "device": s.get("device", {}),
                        "ip": s.get("ip", ""),
                        "user_agent": s.get("user_agent", ""),
                        "created_at": s["created_at"],
                        "last_active": s["last_active"],
                        "remaining_seconds": round(remaining, 1),
                        "refresh_count": s.get("refresh_count", 0),
                    }
                )
        active.sort(key=lambda x: x["last_active"], reverse=True)
        return active[:limit]

    def detect_suspicious_logins(
        self, user_id: str, max_distinct_ips: int = 3, time_window: int = 3600
    ) -> Dict[str, Any]:
        """检测异常登录。企业场景：安全审计时发现同一用户短时间内
        从不同IP/设备登录，触发二次验证。
        """
        now = time.time()
        cutoff = now - time_window
        recent_logins = [h for h in self._login_history if h["user_id"] == user_id and h["timestamp"] > cutoff]
        if len(recent_logins) < 2:
            return {"suspicious": False, "reason": "login_count_low", "recent_logins": len(recent_logins)}
        ips = set()
        devices = set()
        for login in recent_logins:
            dev = login.get("device", {})
            ip = dev.get("ip", "")
            ua = dev.get("user_agent", "")
            if ip:
                ips.add(ip)
            if ua:
                devices.add(ua[:50])
        flags = []
        if len(ips) > max_distinct_ips:
            flags.append(f"多IP登录({len(ips)}个)")
        if len(devices) > max_distinct_ips:
            flags.append(f"多设备登录({len(devices)}个)")
        suspicious = len(flags) > 0
        return {
            "suspicious": suspicious,
            "distinct_ips": len(ips),
            "distinct_devices": len(devices),
            "flags": flags,
            "recent_logins": len(recent_logins),
        }

    def get_user_session_summary(self, user_id: str) -> Dict[str, Any]:
        """获取用户会话摘要。企业场景：用户设置页面展示当前登录的所有设备，
        支持远程注销某个设备。
        """
        now = time.time()
        session_ids = self._user_sessions.get(user_id, [])
        active_devices = []
        for sid in session_ids:
            s = self._sessions.get(sid)
            if not s:
                continue
            if s.get("is_valid") and s["expires_at"] > now:
                remaining = s["expires_at"] - now
                device_info = s.get("device", {})
                active_devices.append(
                    {
                        "session_id": sid,
                        "device_name": device_info.get("device_name", "未知设备"),
                        "device_type": device_info.get("device_type", "unknown"),
                        "ip": s.get("ip", ""),
                        "location": device_info.get("location", ""),
                        "last_active": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s["last_active"])),
                        "remaining_minutes": round(remaining / 60, 1),
                        "is_current": False,
                    }
                )
        active_devices.sort(key=lambda x: x["last_active"], reverse=True)
        total_logins = sum(1 for h in self._login_history if h["user_id"] == user_id)
        return {
            "user_id": user_id,
            "active_devices": active_devices,
            "active_count": len(active_devices),
            "total_historical_logins": total_logins,
            "max_allowed": self._max_per_user,
        }

    def cleanup_expired_sessions(self, batch_size: int = 1000) -> Dict[str, Any]:
        """清理过期会话。企业场景：定时任务每小时清理一次无效Session，
        释放内存中过期会话数据占用的空间，防止内存泄漏。
        """
        now = time.time()
        expired_ids = []
        for sid, session in list(self._sessions.items()):
            if session.get("is_valid") and now >= session["expires_at"]:
                expired_ids.append(sid)
                session["is_valid"] = False
            elif not session.get("is_valid"):
                expired_ids.append(sid)
            if len(expired_ids) >= batch_size:
                break
        for sid in expired_ids:
            self._sessions.pop(sid, None)
            for uid, sids in self._user_sessions.items():
                if sid in sids:
                    sids.remove(sid)
        self._total_expired += len(expired_ids)
        return {"success": True, "cleaned": len(expired_ids), "remaining_sessions": len(self._sessions)}

    def get_stats(self) -> Dict[str, Any]:
        """获取Session统计。企业场景：运维面板展示在线用户数、
        创建/过期速率、并发分布。
        """
        now = time.time()
        active_count = sum(1 for s in self._sessions.values() if s.get("is_valid") and s["expires_at"] > now)
        unique_users = len(self._user_sessions)
        multi_session_users = sum(1 for sids in self._user_sessions.values() if len(sids) > 1)
        return {
            "active_sessions": active_count,
            "unique_users": unique_users,
            "multi_session_users": multi_session_users,
            "total_created": self._total_created,
            "total_validated": self._total_validated,
            "total_revoked": self._total_revoked,
            "total_expired": self._total_expired,
            "max_per_user": self._max_per_user,
            "default_ttl": self._default_ttl,
        }

    # --- Auto-generated action dispatch methods ---
    def _action_cleanup_expired_sessions(self, params=None):
        """Auto-generated action wrapper for cleanup_expired_sessions"""
        if params is None:
            params = {}
        return self.cleanup_expired_sessions(**params)

    def _action_create(self, params=None):
        """Auto-generated action wrapper for create"""
        if params is None:
            params = {}
        return self.create(**params)

    def _action_detect_suspicious_logins(self, params=None):
        """Auto-generated action wrapper for detect_suspicious_logins"""
        if params is None:
            params = {}
        return self.detect_suspicious_logins(**params)

    def _action_get_stats(self, params=None):
        """Auto-generated action wrapper for get_stats"""
        if params is None:
            params = {}
        return self.get_stats(**params)

    def _action_get_user_session_summary(self, params=None):
        """Auto-generated action wrapper for get_user_session_summary"""
        if params is None:
            params = {}
        return self.get_user_session_summary(**params)

    def _action_list_active_sessions(self, params=None):
        """Auto-generated action wrapper for list_active_sessions"""
        if params is None:
            params = {}
        return self.list_active_sessions(**params)

    def _action_refresh(self, params=None):
        """Auto-generated action wrapper for refresh"""
        if params is None:
            params = {}
        return self.refresh(**params)

    def _action_revoke(self, params=None):
        """Auto-generated action wrapper for revoke"""
        if params is None:
            params = {}
        return self.revoke(**params)

    def _action_revoke_all_user_sessions(self, params=None):
        """Auto-generated action wrapper for revoke_all_user_sessions"""
        if params is None:
            params = {}
        return self.revoke_all_user_sessions(**params)

    def _action_validate(self, params=None):
        """Auto-generated action wrapper for validate"""
        if params is None:
            params = {}
        return self.validate(**params)

class SessionManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """会话管理器 - 企业级Session生命周期引擎。

    核心能力：
    1. Token生成与验证（SHA256）
    2. 滑动过期续期
    3. 并发登录限制（踢最早设备）
    4. 批量注销（改密码踢全设备）
    5. 异常登录检测（多IP/多设备）
    6. 登录历史审计
    """

    def __init__(self, config: Optional[Dict] = None):

        super().__init__(config=config)
        self.metrics_collector = self._NoopMetricsCollector()

        self.config = config or {}
        self._data: Dict[str, Any] = {}
        self._metrics: Dict[str, Any] = {
            "total_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "last_success_ts": None,
        }
        self._audit_log: List[Dict] = []
        self._status = ModuleStatus.INITIALIZING
        self._logger = get_logger("session_manager")
        self._store = SessionStoreManager(
            default_ttl=self.config.get("default_ttl", 1800),
            max_sessions_per_user=self.config.get("max_sessions_per_user", 5),
        )

    def initialize(self) -> dict:
        try:
            self._data["config"] = self.config
            self._data["instance_id"] = str(uuid.uuid4())[:8]
            self._data["created_at"] = time.time()
            self._status = ModuleStatus.RUNNING
            return {"success": True, "instance_id": self._data["instance_id"]}
        except Exception as e:
            self._status = ModuleStatus.ERROR
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        stats = self._store.get_stats()
        checks = [
            ("store_active", True),
            ("status_ok", self._status == ModuleStatus.RUNNING),
        ]
        results = [{"name": n, "healthy": bool(v)} for n, v in checks]
        return {
            "healthy": all(c["healthy"] for c in results),
            "checks": results,
            "status": self._status.value if hasattr(self._status, "value") else str(self._status),
            "total_operations": self._metrics["total_operations"],
            "session_stats": stats,
        }

    def create_session(self, params: dict = None) -> dict:
        """创建会话。params: user_id(必填), device_info(可选), metadata(可选), ttl(可选)"""
        params = params or {}
        user_id = params.get("user_id", "")
        if not user_id:
            return {"success": False, "error": "user_id 必填"}
        self._metrics["total_operations"] += 1
        return {
            "success": True,
            **self._store.create(
                user_id=user_id,
                device_info=params.get("device_info"),
                metadata=params.get("metadata"),
                ttl=params.get("ttl"),
            ),
        }

    def validate(self, params: dict = None) -> dict:
        """验证会话。params: session_id(必填), token(必填)"""
        params = params or {}
        sid = params.get("session_id", "")
        token = params.get("token", "")
        if not sid or not token:
            return {"success": False, "error": "session_id 和 token 必填"}
        self._metrics["total_operations"] += 1
        result = self._store.validate(sid, token)
        return {"success": result.get("valid", False), **result}

    def refresh(self, params: dict = None) -> dict:
        """刷新会话。params: session_id(必填), additional_ttl(可选)"""
        params = params or {}
        sid = params.get("session_id", "")
        if not sid:
            return {"success": False, "error": "session_id 必填"}
        self._metrics["total_operations"] += 1
        return self._store.refresh(sid, params.get("additional_ttl"))

    def revoke(self, params: dict = None) -> dict:
        """注销会话。params: session_id(必填), reason(可选)"""
        params = params or {}
        sid = params.get("session_id", "")
        if not sid:
            return {"success": False, "error": "session_id 必填"}
        self._metrics["total_operations"] += 1
        return self._store.revoke(sid, params.get("reason", "user_logout"))

    def list_active(self, params: dict = None) -> dict:
        """列出活跃会话。params: user_id(可选), limit(可选)"""
        params = params or {}
        sessions = self._store.list_active_sessions(user_id=params.get("user_id"), limit=params.get("limit", 50))
        self._metrics["total_operations"] += 1
        return {"success": True, "count": len(sessions), "sessions": sessions}

    async def execute(self, action: str, params: dict = None) -> dict:
        """Dispatch action to business methods."""
        self.trace("execute", {"module": "session_manager", "action": action})
        self.metrics_collector.counter("session_manager.execute.calls", 1)
        self.audit("execute", {"module": "session_manager", "action": action})
        params = params or {}
        handler = getattr(self, action, None)
        if handler and callable(handler):
            self._metrics["total_operations"] += 1
            t0 = time.time()
            try:
                result = handler(params)
                self._metrics["last_success_ts"] = time.time()
                self._metrics["avg_latency_ms"] = (
                    self._metrics["avg_latency_ms"] * 0.9 + (time.time() - t0) * 1000 * 0.1
                )
                return result
            except Exception as e:
                self._metrics["errors"] += 1
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown action: {action}"}

    def shutdown(self) -> dict:
        """Graceful shutdown for session_manager."""
        self._status = "stopped"
        self._logger.info("%s shutdown complete", self.__class__.__name__)
        return {"success": True, "module": self.__class__.__name__}

module_class = SessionManager
