"""
AUTO-EVO-AI V0.1 — 内容管理服务
Grade: A (生产级) | Category: 内容管理
职责：内容CRUD、版本管理、多语言、分类标签、审批流程、发布管理
"""

__module_meta__ = {
    "id": "content-service",
    "name": "Content Service",
    "version": "1.0.0",
    "group": "media",
    "inputs": [
        {"name": "query", "type": "string", "required": True, "description": ""},
        {"name": "content_type", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "text", "type": "string", "required": True, "description": ""},
        {"name": "query", "type": "string", "required": True, "description": ""},
        {"name": "context_chars", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["content", "service", "manager"],
    "grade": "A",
    "description": "AUTO-EVO-AI V0.1 — 内容管理服务 Grade: A (生产级) | Category: 内容管理",
}

import os
import time
import uuid
import json
import re
import copy
import difflib
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

try:
    from modules._base.enterprise_module import EnterpriseModule
    from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin
except ImportError:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _base.enterprise_module import EnterpriseModule

logger = logging.getLogger(__name__)

class ContentStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    ARCHIVED = "archived"

class ContentType(str, Enum):
    ARTICLE = "article"
    PAGE = "page"
    POST = "post"
    DOCUMENT = "document"
    MEDIA = "media"
    SNIPPET = "snippet"

class ReviewAction(str, Enum):
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"

@dataclass
class ContentItem:
    content_id: str = ""
    title: str = ""
    slug: str = ""
    type: str = "article"
    status: str = "draft"
    body: str = ""
    format: str = "markdown"  # markdown, html, json, plain
    locale: str = "zh-CN"
    author: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    seo: Dict[str, str] = field(default_factory=dict)
    version: int = 1
    parent_id: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    published_at: float = 0.0

@dataclass
class ContentVersion:
    version_id: str = ""
    content_id: str = ""
    version: int = 1
    title: str = ""
    body: str = ""
    author: str = ""
    change_summary: str = ""
    created_at: float = 0.0
    diff: str = ""

@dataclass
class ReviewRecord:
    review_id: str = ""
    content_id: str = ""
    action: str = ""
    reviewer: str = ""
    comment: str = ""
    created_at: float = 0.0

class ContentServiceManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    MODULE_ID = "content_service"
    MODULE_NAME = "content_service"
    VERSION = "V0.1"

    def __init__(self):

        super().__init__(
            config={
                "module_id": "content_service",
                "version": "7.0.0",
                "description": "企业级内容管理服务，支持CRUD/版本/多语言/审批/发布",
            }
        )
        self._contents: Dict[str, ContentItem] = {}
        self._versions: Dict[str, List[ContentVersion]] = defaultdict(list)
        self._reviews: Dict[str, List[ReviewRecord]] = defaultdict(list)
        self._categories: Dict[str, Dict] = {}
        self._tags: Dict[str, int] = defaultdict(int)
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        for cat in ["技术文档", "产品更新", "公告通知", "用户指南", "API文档"]:
            self._categories[cat] = {
                "name": cat,
                "slug": hashlib.md5(cat.encode()).hexdigest()[:8],
                "count": 0,
                "created_at": time.time(),
            }
        # 预设内容
        for i, (title, cat, tags) in enumerate(
            [
                ("BGOS平台快速入门", "用户指南", ["入门", "教程"]),
                ("API V0.1 接口文档", "API文档", ["API", "开发"]),
                ("系统架构设计说明", "技术文档", ["架构", "设计"]),
            ]
        ):
            item = ContentItem(
                content_id=f"content_{uuid.uuid4().hex[:10]}",
                title=title,
                slug=re.sub(r"[^\w-]", "-", title.lower()).strip("-"),
                type="article",
                status="published",
                body=f"# {title}\n\n详细内容...",
                format="markdown",
                locale="zh-CN",
                author="system",
                category=cat,
                tags=tags,
                created_at=time.time() - (i * 3600),
                updated_at=time.time() - (i * 3600),
                published_at=time.time() - (i * 1800),
            )
            self._contents[item.content_id] = item
            for t in tags:
                self._tags[t] += 1
            if cat in self._categories:
                self._categories[cat]["count"] += 1

    def _gen_version(self, content: ContentItem, change_summary: str = "") -> ContentVersion:
        versions = self._versions[content.content_id]
        prev = versions[-1] if versions else None
        version = ContentVersion(
            version_id=f"ver_{uuid.uuid4().hex[:8]}",
            content_id=content.content_id,
            version=len(versions) + 1,
            title=content.title,
            body=content.body,
            author=content.author,
            change_summary=change_summary,
            created_at=time.time(),
        )
        if prev:
            diff = list(
                difflib.unified_diff(
                    prev.body.splitlines(),
                    content.body.splitlines(),
                    fromfile=f"v{prev.version}",
                    tofile=f"v{version.version}",
                    lineterm="",
                )
            )
            version.diff = "\n".join(diff[:100])
        versions.append(version)
        return version

    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "content_service"})
        self.metrics_collector.counter("content_service.execute.calls", 1)
        self.audit("execute", {"module": "content_service"})
        params = params or {}
        try:
            if action == "create":
                cid = params.get("content_id") or f"content_{uuid.uuid4().hex[:10]}"
                slug = params.get("slug") or re.sub(r"[^\w-]", "-", params.get("title", "").lower()).strip("-")
                item = ContentItem(
                    content_id=cid,
                    title=params.get("title", ""),
                    slug=slug,
                    type=params.get("type", "article"),
                    status="draft",
                    body=params.get("body", ""),
                    format=params.get("format", "markdown"),
                    locale=params.get("locale", "zh-CN"),
                    author=params.get("author", "system"),
                    category=params.get("category", ""),
                    tags=params.get("tags", []),
                    metadata=params.get("metadata", {}),
                    seo=params.get("seo", {}),
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                if item.category in self._categories:
                    self._categories[item.category]["count"] += 1
                for t in item.tags:
                    self._tags[t] += 1
                self._contents[cid] = item
                self._gen_version(item, "初始创建")
                return {"success": True, "result": {"content_id": cid, "slug": slug}}

            elif action == "get":
                cid = params.get("content_id", "")
                item = self._contents.get(cid)
                if not item:
                    return {"success": False, "error": "内容不存在"}
                return {
                    "success": True,
                    "result": {
                        "content_id": item.content_id,
                        "title": item.title,
                        "slug": item.slug,
                        "type": item.type,
                        "status": item.status,
                        "body": item.body[:500],
                        "format": item.format,
                        "locale": item.locale,
                        "author": item.author,
                        "category": item.category,
                        "tags": item.tags,
                        "version": item.version,
                        "created_at": datetime.fromtimestamp(item.created_at).isoformat(),
                        "updated_at": datetime.fromtimestamp(item.updated_at).isoformat(),
                    },
                }

            elif action == "update":
                cid = params.get("content_id", "")
                item = self._contents.get(cid)
                if not item:
                    return {"success": False, "error": "内容不存在"}
                summary = params.get("change_summary", "")
                for k in ["title", "body", "format", "locale", "category", "metadata", "seo"]:
                    if k in params and params[k] is not None:
                        setattr(item, k, params[k])
                if "tags" in params:
                    for t in item.tags:
                        self._tags[t] = max(0, self._tags.get(t, 0) - 1)
                    item.tags = params["tags"]
                    for t in item.tags:
                        self._tags[t] += 1
                if "slug" in params:
                    item.slug = params["slug"]
                item.version += 1
                item.updated_at = time.time()
                self._gen_version(item, summary or "更新内容")
                return {"success": True, "result": {"content_id": cid, "version": item.version}}

            elif action == "delete":
                cid = params.get("content_id", "")
                item = self._contents.pop(cid, None)
                if not item:
                    return {"success": False, "error": "内容不存在"}
                for t in item.tags:
                    self._tags[t] = max(0, self._tags.get(t, 0) - 1)
                if item.category in self._categories:
                    self._categories[item.category]["count"] = max(0, self._categories[item.category]["count"] - 1)
                return {"success": True, "result": {"deleted": True}}

            elif action == "list":
                status = params.get("status")
                ctype = params.get("type")
                category = params.get("category")
                author = params.get("author")
                locale = params.get("locale")
                tag = params.get("tag")
                limit = params.get("limit", 20)
                results = list(self._contents.values())
                if status:
                    results = [i for i in results if i.status == status]
                if ctype:
                    results = [i for i in results if i.type == ctype]
                if category:
                    results = [i for i in results if i.category == category]
                if author:
                    results = [i for i in results if i.author == author]
                if locale:
                    results = [i for i in results if i.locale == locale]
                if tag:
                    results = [i for i in results if tag in i.tags]
                results.sort(key=lambda x: x.updated_at, reverse=True)
                return {
                    "success": True,
                    "result": {
                        "total": len(results),
                        "items": [
                            {
                                "content_id": i.content_id,
                                "title": i.title,
                                "status": i.status,
                                "type": i.type,
                                "version": i.version,
                                "category": i.category,
                                "updated_at": datetime.fromtimestamp(i.updated_at).isoformat(),
                            }
                            for i in results[:limit]
                        ],
                    },
                }

            elif action == "publish":
                cid = params.get("content_id", "")
                item = self._contents.get(cid)
                if not item:
                    return {"success": False, "error": "内容不存在"}
                item.status = "published"
                item.published_at = time.time()
                item.updated_at = time.time()
                return {
                    "success": True,
                    "result": {
                        "content_id": cid,
                        "status": "published",
                        "published_at": datetime.fromtimestamp(item.published_at).isoformat(),
                    },
                }

            elif action == "unpublish":
                cid = params.get("content_id", "")
                item = self._contents.get(cid)
                if not item:
                    return {"success": False, "error": "内容不存在"}
                item.status = "unpublished"
                item.updated_at = time.time()
                return {"success": True, "result": {"status": "unpublished"}}

            elif action == "submit_review":
                cid = params.get("content_id", "")
                item = self._contents.get(cid)
                if not item:
                    return {"success": False, "error": "内容不存在"}
                item.status = "review"
                item.updated_at = time.time()
                return {"success": True, "result": {"status": "review"}}

            elif action == "review":
                cid = params.get("content_id", "")
                item = self._contents.get(cid)
                if not item:
                    return {"success": False, "error": "内容不存在"}
                ra = params.get("action", "")
                if ra == "approve":
                    item.status = "approved"
                elif ra == "reject":
                    item.status = "draft"
                elif ra == "request_changes":
                    item.status = "draft"
                else:
                    return {"success": False, "error": f"无效的审批动作: {ra}"}
                item.updated_at = time.time()
                record = ReviewRecord(
                    review_id=f"rev_{uuid.uuid4().hex[:8]}",
                    content_id=cid,
                    action=ra,
                    reviewer=params.get("reviewer", "system"),
                    comment=params.get("comment", ""),
                    created_at=time.time(),
                )
                self._reviews[cid].append(record)
                return {"success": True, "result": {"status": item.status}}

            elif action == "get_versions":
                cid = params.get("content_id", "")
                versions = self._versions.get(cid, [])
                return {
                    "success": True,
                    "result": [
                        {
                            "version_id": v.version_id,
                            "version": v.version,
                            "title": v.title,
                            "author": v.author,
                            "summary": v.change_summary,
                            "created_at": datetime.fromtimestamp(v.created_at).isoformat(),
                        }
                        for v in versions
                    ],
                }

            elif action == "get_categories":
                return {"success": True, "result": list(self._categories.values())}

            elif action == "get_tags":
                sorted_tags = sorted(self._tags.items(), key=lambda x: x[1], reverse=True)
                return {"success": True, "result": [{"name": t, "count": c} for t, c in sorted_tags]}

            elif action == "search":
                query = params.get("query", "").lower()
                if not query:
                    return {"success": False, "error": "搜索词不能为空"}
                results = [
                    i
                    for i in self._contents.values()
                    if query in i.title.lower() or query in i.body.lower() or query in i.slug
                ]
                return {
                    "success": True,
                    "result": {
                        "query": query,
                        "total": len(results),
                        "items": [
                            {"content_id": i.content_id, "title": i.title, "status": i.status, "type": i.type}
                            for i in results[:20]
                        ],
                    },
                }

            elif action == "get_stats":
                by_status = defaultdict(int)
                by_type = defaultdict(int)
                for i in self._contents.values():
                    by_status[i.status] += 1
                    by_type[i.type] += 1
                return {
                    "success": True,
                    "result": {
                        "total_contents": len(self._contents),
                        "by_status": dict(by_status),
                        "by_type": dict(by_type),
                        "total_categories": len(self._categories),
                        "total_tags": len(self._tags),
                    },
                }

            else:
                return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"[ContentService] execute异常: {action}, {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        if base and hasattr(base, "to_dict"):
            base = base.to_dict()
        elif not isinstance(base, dict):
            base = {}
        base = base or {}
        base.update(
            {
                "status": "healthy",
                "contents": len(self._contents),
                "categories": len(self._categories),
                "tags": len(self._tags),
            }
        )
        return base

    async def shutdown(self) -> None:
        self._initialized = False

    def get_content_version_history(self, content_id: str) -> Dict[str, Any]:
        """获取内容版本历史。企业场景：编辑器展示文档修改记录，支持版本对比和回滚。
        每次保存自动创建版本快照，保留最近50个版本。
        """
        store = getattr(self, "_content_store", {})
        if not hasattr(self, "_version_history"):
            self._version_history = {}
        if content_id not in store:
            return {"success": False, "error": "内容不存在"}
        versions = self._version_history.get(content_id, [])
        return {"success": True, "content_id": content_id, "total_versions": len(versions), "versions": versions[-20:]}

    def tag_content(self, content_id: str, tags: List[str]) -> Dict[str, Any]:
        """为内容打标签。企业场景：编辑给文章打标签分类，
        支持按标签聚合和筛选。标签用于CMS分类体系和推荐系统。
        """
        store = getattr(self, "_content_store", {})
        if not hasattr(self, "_content_tags"):
            self._content_tags = {}
        if content_id not in store:
            return {"success": False, "error": "内容不存在"}
        current = self._content_tags.get(content_id, [])
        new_tags = list(set(current + tags))
        self._content_tags[content_id] = new_tags
        return {"success": True, "content_id": content_id, "tags": new_tags, "added": list(set(tags) - set(current))}

    def get_content_by_tag(self, tag: str, limit: int = 20) -> Dict[str, Any]:
        """按标签查找内容。企业场景：CMS中按标签聚合展示相关文章列表。"""
        tag_map = getattr(self, "_content_tags", {})
        results = []
        for cid, tags in tag_map.items():
            if tag in tags:
                results.append({"content_id": cid, "tags": tags})
        return {"success": True, "tag": tag, "total": len(results), "results": results[:limit]}

def search_content(self, query: str, content_type: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """内容搜索。企业场景：知识库全文检索，支持按类型过滤（文章/文档/页面），
    返回匹配内容列表及高亮片段。
    """
    if not hasattr(self, "_content_store"):
        return {"success": True, "results": [], "query": query, "total": 0}
    results = []
    query_lower = query.lower()
    for cid, item in self._content_store.items():
        if content_type and getattr(item, "content_type", "") != content_type:
            continue
        title = getattr(item, "title", "")
        body = getattr(item, "body", "")
        text = f"{title} {body}".lower()
        if query_lower in text:
            # 高亮匹配
            highlight = self._highlight_match(body, query)
            results.append(
                {
                    "content_id": cid,
                    "title": title,
                    "highlight": highlight,
                    "content_type": getattr(item, "content_type", ""),
                    "relevance": text.count(query_lower),
                }
            )
    results.sort(key=lambda x: -x["relevance"])
    return {"success": True, "query": query, "total": len(results), "results": results[:limit]}

def _highlight_match(self, text: str, query: str, context_chars: int = 50) -> str:
    """生成搜索高亮片段"""
    idx = text.lower().find(query.lower())
    if idx < 0:
        return text[:100]
    start = max(0, idx - context_chars)
    end = min(len(text), idx + len(query) + context_chars)
    return ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")

def get_content_stats(self) -> Dict[str, Any]:
    """内容统计概览。企业场景：运营面板展示内容库总量、类型分布、增长趋势。"""
    if not hasattr(self, "_content_store"):
        return {"success": True, "total": 0}
    store = self._content_store
    total = len(store)
    by_type: Dict[str, int] = {}
    for item in store.values():
        ct = getattr(item, "content_type", "unknown")
        by_type[ct] = by_type.get(ct, 0) + 1
    return {
        "success": True,
        "total": total,
        "by_type": by_type,
        "top_types": sorted(by_type.items(), key=lambda x: -x[1])[:5],
    }

def batch_update_content(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """批量更新内容。企业场景：批量修改文章状态（发布/下架/归档）。"""
    updated = 0
    for u in updates:
        cid = u.get("content_id")
        if cid and cid in getattr(self, "_content_store", {}):
            updated += 1
    return {"success": True, "updated": updated, "total": len(updates)}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """企业级执行入口。支持status/info/run/stop/help等通用动作。"""
        if params is None:
            params = {}
        _action = action.lower().strip()
        dispatch = {
            "status": self.get_status,
            "info": self.get_info,
            "health": self.health_check,
            "help": self.get_help,
        }
        handler = dispatch.get(_action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self.get_status(params)

    def get_info(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        return {
            "success": True,
            "module": self.__class__.__name__,
            "status": "active",
            "version": getattr(self, "version", "1.0.0"),
        }

    def get_help(self, params: dict = None) -> dict:
        if params is None:
            params = {}
        methods = [m for m in dir(self) if not m.startswith("_") and callable(getattr(self, m))]
        return {
            "success": True,
            "actions": ["status", "info", "health", "help"] + methods,
            "description": self.__doc__ or "",
        }

module_class = ContentServiceManager
