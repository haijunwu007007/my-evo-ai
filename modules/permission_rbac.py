# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI V0.1 - RBAC 权限管理（A级生产实现）
================================================
模块ID: permission-rbac
功能：角色 CRUD、权限绑定、用户角色分配、check_permission。
"""
__module_meta__ = {"id":"permission-rbac","name":"RBAC","version":"V0.1","group":"security","grade":"A",
    "tags":["security","rbac","permission"],"description":"RBAC 权限管理 - 角色/权限/用户"}
import time, uuid, logging
from typing import Any, Dict, List, Optional
from modules._base.enterprise_module import (EnterpriseModule, ModuleStatus, HealthReport, CircuitBreakerMixin, RateLimiterMixin, Result)
from modules._base.metrics import metrics_collector
logger = logging.getLogger("evo.permission-rbac")

class PermissionRbac(CircuitBreakerMixin, RateLimiterMixin, EnterpriseModule):
    MODULE_ID="permission-rbac"; MODULE_NAME="RBAC权限"; VERSION = "V0.1"; MODULE_LEVEL="A"
    def __init__(self, config=None):
        super().__init__(config)
        self._roles: Dict[str, Dict] = {}  # role_id -> {name, permissions, description}
        self._users: Dict[str, List[str]] = {}  # user_id -> [role_ids]
        self._permissions: Dict[str, str] = {}  # perm_key -> description
        self._setup_rate_limit(rate=500, burst=1000)
    def initialize(self) -> None:
        self._add_default_permissions()
        self._add_default_roles()
        self.status = ModuleStatus.RUNNING
    def _add_default_permissions(self):
        for p in ["read","write","delete","admin","config","user_manage","report","audit","api_access"]:
            self._permissions.setdefault(p, f"permission:{p}")
    def _add_default_roles(self):
        if "admin" not in self._roles:
            self._roles["admin"] = {"name":"管理员","permissions":list(self._permissions.keys()),"description":"超级管理员","builtin":True}
        if "user" not in self._roles:
            self._roles["user"] = {"name":"普通用户","permissions":["read","write","report"],"description":"普通用户","builtin":True}
    def health_check(self) -> HealthReport:
        return HealthReport(status=self.status.value, healthy=self.status==ModuleStatus.RUNNING, module_id=self.MODULE_ID,
            checks={"roles":len(self._roles),"users":len(self._users),"perms":len(self._permissions)})
    async def execute(self, action, params=None):
        return await self._safe_execute(action, params, handler=self._dispatch)
    def _dispatch(self, params: Dict) -> Dict:
        action=params.get("action","status")
        if action=="create_role": return self._create_role(params)
        elif action=="list_roles": return {"roles":self._roles}
        elif action=="assign_role": return self._assign_role(params)
        elif action=="remove_role": return self._remove_role(params)
        elif action=="check": return self._check(params)
        elif action=="user_permissions": return self._user_permissions(params)
        elif action=="add_permission": return self._add_permission(params)
        elif action=="list_permissions": return {"success":True,"permissions":self._permissions}
        elif action=="delete_role": return self._delete_role(params)
        return {"success":False,"error":f"unknown:{action}"}

    def _create_role(self, params: Dict) -> Dict:
        role_id = params.get("role_id",f"role_{uuid.uuid4().hex[:6]}")
        if role_id in self._roles: return {"success":False,"error":"role exists"}
        self._roles[role_id] = {"name":params.get("name",role_id),"permissions":params.get("permissions",["read"]),
                                "description":params.get("description",""),"builtin":False}
        return {"success":True,"role_id":role_id}

    def _delete_role(self, params: Dict) -> Dict:
        role_id = params.get("role_id","")
        role = self._roles.get(role_id)
        if not role: return {"success":False,"error":"role not found"}
        if role.get("builtin"): return {"success":False,"error":"cannot delete builtin role"}
        self._roles.pop(role_id,None)
        for uid in self._users:
            self._users[uid] = [r for r in self._users[uid] if r != role_id]
        return {"success":True}

    def _assign_role(self, params: Dict) -> Dict:
        user_id = params.get("user_id","")
        role_id = params.get("role_id","")
        if not user_id or not role_id: return {"success":False,"error":"user_id and role_id required"}
        if role_id not in self._roles: return {"success":False,"error":"role not found"}
        if user_id not in self._users: self._users[user_id] = []
        if role_id not in self._users[user_id]:
            self._users[user_id].append(role_id)
        return {"success":True,"user_id":user_id,"roles":self._users[user_id]}

    def _remove_role(self, params: Dict) -> Dict:
        user_id=params.get("user_id",""); role_id=params.get("role_id","")
        if user_id in self._users and role_id:
            self._users[user_id] = [r for r in self._users[user_id] if r != role_id]
        return {"success":True}

    def _check(self, params: Dict) -> Dict:
        user_id=params.get("user_id",""); permission=params.get("permission","")
        perms = self._user_permissions({"user_id":user_id}).get("permissions",[])
        has_perm = permission in perms
        return {"success":True,"has_permission":has_perm,"permission":permission,"user_id":user_id}

    def _user_permissions(self, params: Dict) -> Dict:
        user_id=params.get("user_id","")
        role_ids = self._users.get(user_id,[])
        perms = set()
        for rid in role_ids:
            role = self._roles.get(rid,{})
            perms.update(role.get("permissions",[]))
        return {"success":True,"user_id":user_id,"roles":role_ids,"permissions":sorted(perms)}

    def _add_permission(self, params: Dict) -> Dict:
        key=params.get("key",""); desc=params.get("description","")
        self._permissions[key]=desc
        return {"success":True}

    async def shutdown(self) -> None:
        self._roles.clear(); self._users.clear(); self.status=ModuleStatus.STOPPED
module_class = PermissionRbac
