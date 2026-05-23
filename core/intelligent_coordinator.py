# -*- coding: utf-8 -*-
"""
AUTO-EVO-AI 智能协调层 v1.0
===========================
上市公司级生产标准

核心能力:
1. 意图理解: 自然语言→结构化任务描述(意图分类+实体提取+参数识别)
2. 多步工作流: 复杂任务自动拆解为有序步骤链
3. 对话上下文: 多轮对话记忆, 上下文连续性
4. 数据流映射: 模块间自动串联, 输出→输入字段级映射
5. AI推理增强: LLM辅助决策, 动态编排优化

设计原则:
- 作为薄层注入 SystemCoordinatorV3, 不破坏现有代码
- 所有LLM调用失败自动降级到规则引擎
- 无状态推理层 + 持久化记忆层分离
"""

import asyncio
import json
import time
import logging
import hashlib
import sqlite3
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("intelligent_coordinator")


# ============================================================================
# 数据模型
# ============================================================================

class IntentType(str, Enum):
    """意图类型"""
    SINGLE_MODULE = "single_module"      # 单模块执行
    MULTI_STEP = "multi_step"            # 多步工作流
    QUERY = "query"                      # 信息查询
    CONFIGURATION = "configuration"      # 配置变更
    MONITORING = "monitoring"            # 监控查看
    AUTONOMOUS = "autonomous"            # 自主决策
    CHITCHAT = "chitchat"                # 闲聊/无关


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ParsedIntent:
    """解析后的意图"""
    intent_type: str           # IntentType
    primary_action: str        # 主动作: analyze/scan/generate/monitor/configure/query/...
    entities: Dict[str, Any]   # 提取的实体: {"stock": "贵州茅台", "metric": "CPU"}
    modules_hint: List[str]    # 候选模块列表
    complexity: str            # TaskComplexity
    sub_tasks: List[str]       # 子任务拆解(多步时)
    params: Dict[str, Any]     # 提取的参数
    confidence: float = 0.0    # 置信度 0-1
    reasoning: str = ""        # 推理过程


@dataclass
class ConversationTurn:
    """对话轮次"""
    id: str
    user_input: str
    parsed_intent: Dict        # ParsedIntent.asdict()
    response: Dict             # 系统响应
    modules_used: List[str]    # 使用的模块
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    description: str
    module_id: str = ""
    action: str = "status"
    params: Dict[str, Any] = field(default_factory=dict)
    input_mapping: Dict[str, str] = field(default_factory=dict)   # param: "steps.{id}.output.{field}"
    condition: str = ""         # 条件表达式
    parallel_with: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    timeout: int = 30
    retry: int = 0


@dataclass
class WorkflowPlan:
    """工作流执行计划"""
    id: str
    original_task: str
    intent: Dict               # ParsedIntent
    steps: List[Dict]           # WorkflowStep.asdict()
    dag_order: List[str]        # DAG拓扑排序后的步骤ID
    data_flow: Dict[str, str]  # 步骤间数据流映射
    estimated_duration_ms: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# 意图理解引擎
# ============================================================================

class IntentParser:
    """
    自然语言意图解析器
    
    规则引擎 + TF关键词匹配, 不依赖LLM
    LLM调用仅作为增强(可选), 失败自动降级
    """

    # 动作关键词映射
    ACTION_KEYWORDS = {
        "analyze": ["分析", "评估", "诊断", "检测", "统计", "analyze", "evaluate", "assess",
                     "diagnose", "detect", "audit", "inspect", "review", "check"],
        "scan": ["扫描", "搜索", "发现", "查找", "scan", "search", "discover", "find",
                  "crawl", "explore", "trending", "热门"],
        "generate": ["生成", "创建", "编写", "构建", "generate", "create", "build", "write",
                      "make", "produce", "draft"],
        "monitor": ["监控", "观察", "巡检", "监测", "monitor", "watch", "observe", "track",
                     "health", "状态", "健康"],
        "configure": ["配置", "设置", "修改", "更新", "configure", "set", "update", "modify",
                       "adjust", "change", "toggle", "enable", "disable"],
        "query": ["查询", "获取", "获取", "列出", "显示", "query", "get", "list", "show",
                   "fetch", "retrieve", "read", "查看"],
        "execute": ["执行", "运行", "启动", "停止", "重启", "execute", "run", "start", "stop",
                     "restart", "trigger", "launch"],
        "notify": ["通知", "推送", "发送", "告警", "notify", "alert", "push", "send",
                    "broadcast", "message"],
        "backup": ["备份", "恢复", "容灾", "快照", "backup", "restore", "snapshot", "archive"],
        "schedule": ["定时", "调度", "周期", "计划", "schedule", "cron", "periodic", "routine"],
    }

    # 实体提取正则
    ENTITY_PATTERNS = {
        "stock": [
            r"([\u4e00-\u9fff]{2,4})的?(?:股票|行情|股价|涨跌)",
            r"(?:查|看|分析)([\u4e00-\u9fff]{2,4})(?:的)?(?:股票|行情)",
            r"(sh|sz|hk|us)\d{4,6}",
        ],
        "module": [
            r"模块[\"'\s:]*(\w[\w_-]*)",
            r"(?:使用|调用|运行)[\"'\s:]*(\w[\w_-]*)",
        ],
        "number": [
            r"(\d+(?:\.\d+)?)\s*(?:条|个|次|小时|天|分钟|秒|MB|GB|TB|%)",
            r"(?:最近|过去|前)(\d+)\s*(?:小时|天|周|月|条|次|条记录)",
        ],
        "time_range": [
            r"(今日|今天|昨天|本周|上周|本月|上月|本季度|本年|今年)",
            r"(最近|过去|前)(\d+)\s*(?:小时|天|周|月|分钟|秒)",
        ],
        "metric": [
            r"(CPU|内存|磁盘|网络|带宽|延迟|QPS|TPS|连接数|线程数)",
        ],
    }

    # 多步任务指示词
    MULTI_STEP_INDICATORS = [
        "然后", "接着", "之后", "最后", "并且", "同时", "依次",
        "先.*再", "第一步", "第二步", "最后一步",
        "and then", "after that", "finally", "first.*then", "step 1",
        "同时", "并行", "parallel",
    ]

    def parse(self, text: str, context: Dict = None) -> ParsedIntent:
        """
        解析自然语言意图
        
        Args:
            text: 用户输入
            context: 对话上下文(之前轮次)
        
        Returns:
            ParsedIntent
        """
        context = context or {}
        text_lower = text.lower().strip()
        
        # 1. 提取实体
        entities = self._extract_entities(text, text_lower)
        
        # 2. 识别主动作
        primary_action = self._detect_primary_action(text_lower)
        
        # 3. 判断意图类型
        intent_type, reasoning = self._classify_intent(text_lower, primary_action, entities)
        
        # 4. 评估复杂度
        complexity = self._assess_complexity(text, intent_type)
        
        # 5. 提取参数
        params = self._extract_params(text, entities)
        
        # 6. 多步任务拆解
        sub_tasks = []
        if intent_type == IntentType.MULTI_STEP.value:
            sub_tasks = self._split_sub_tasks(text)
        
        # 7. 候选模块
        modules_hint = self._suggest_modules(text_lower, primary_action, entities)
        
        # 8. 置信度
        confidence = self._calculate_confidence(intent_type, primary_action, modules_hint, entities)
        
        return ParsedIntent(
            intent_type=intent_type,
            primary_action=primary_action,
            entities=entities,
            modules_hint=modules_hint,
            complexity=complexity,
            sub_tasks=sub_tasks,
            params=params,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _extract_entities(self, text: str, text_lower: str) -> Dict[str, Any]:
        """提取实体"""
        entities = {}
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text, re.IGNORECASE)
                matches.extend(found)
            if matches:
                entities[entity_type] = matches if len(matches) > 1 else matches[0]
        
        # 提取中文核心主题(去除功能词后的剩余词)
        stopwords = {"的", "了", "吗", "呢", "吧", "啊", "请", "帮我", "我要", "我想",
                      "我想", "请帮我", "能不能", "可以", "帮我", "麻烦", "看一下",
                      "get", "the", "a", "an", "is", "are", "can", "please", "show", "me"}
        clean = text
        for sw in stopwords:
            clean = clean.replace(sw, " ")
        # 提取关键短语(2-6字)
        phrases = re.findall(r'[\u4e00-\u9fff]{2,6}', clean)
        if phrases:
            entities["keywords"] = phrases
        
        return entities

    def _detect_primary_action(self, text_lower: str) -> str:
        """检测主动作"""
        best_action = "query"  # 默认查询
        best_score = 0
        for action, keywords in self.ACTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_action = action
        return best_action

    def _classify_intent(self, text_lower: str, action: str, entities: Dict) -> Tuple[str, str]:
        """分类意图"""
        # 多步任务
        for indicator in self.MULTI_STEP_INDICATORS:
            if indicator in text_lower:
                return IntentType.MULTI_STEP.value, f"检测到多步指示词: {indicator}"
        
        # 包含多个动作词
        action_count = sum(1 for keywords in self.ACTION_KEYWORDS.values() 
                         for kw in keywords if kw in text_lower)
        if action_count >= 2:
            return IntentType.MULTI_STEP.value, f"检测到{action_count}个动作关键词"
        
        # 配置变更
        if action == "configure":
            return IntentType.CONFIGURATION.value, "检测到配置相关动作"
        
        # 监控
        if action == "monitor" or any(m in text_lower for m in ["监控", "巡检", "health", "status"]):
            return IntentType.MONITORING.value, "检测到监控相关动作"
        
        # 自主任务
        if any(w in text_lower for w in ["自动", "自主", "autonomous", "auto"]):
            return IntentType.AUTONOMOUS.value, "检测到自主运行意图"
        
        # 闲聊
        chitchat_words = ["你好", "hello", "hi", "谢谢", "thanks", "bye", "再见"]
        if any(w in text_lower for w in chitchat_words) and action_count == 0:
            return IntentType.CHITCHAT.value, "闲聊类输入"
        
        return IntentType.SINGLE_MODULE.value, f"单模块执行, 动作={action}"

    def _assess_complexity(self, text: str, intent_type: str) -> str:
        """评估任务复杂度"""
        if intent_type == IntentType.MULTI_STEP.value:
            return TaskComplexity.HIGH.value
        if intent_type == IntentType.CONFIGURATION.value:
            return TaskComplexity.MEDIUM.value
        if len(text) > 50:
            return TaskComplexity.MEDIUM.value
        return TaskComplexity.LOW.value

    def _extract_params(self, text: str, entities: Dict) -> Dict:
        """提取参数"""
        params = {}
        if "number" in entities:
            params["limit"] = entities["number"] if isinstance(entities["number"], int) else int(str(entities["number"]).replace("%", ""))
        if "time_range" in entities:
            params["time_range"] = entities["time_range"]
        if "metric" in entities:
            params["metric"] = entities["metric"]
        if "stock" in entities:
            params["target"] = entities["stock"]
        # 整体任务文本作为input
        params["input"] = text
        return params

    def _split_sub_tasks(self, text: str) -> List[str]:
        """拆分子任务"""
        # 按顺序指示词拆分
        splitters = ["然后", "接着", "之后", "最后", "并且", ";", "，然后", ", then",
                      "first", "second", "third", "finally"]
        parts = [text]
        for sp in splitters:
            new_parts = []
            for p in parts:
                new_parts.extend(p.split(sp))
            parts = new_parts
        # 过滤空串和极短串
        return [p.strip() for p in parts if len(p.strip()) >= 2]

    def _suggest_modules(self, text_lower: str, action: str, entities: Dict) -> List[str]:
        """建议候选模块"""
        hints = []
        # 基于实体推荐
        if "stock" in entities:
            hints.extend(["stock_api", "data_analysis"])
        if "module" in entities:
            hints.append(entities["module"])
        # 基于关键词直接推荐（优先级最高）
        keyword_modules = {
            "github": "github_scanner",
            "开源": "github_scanner",
            "trending": "github_scanner",
            "热门": "github_scanner",
            "repo": "github_scanner",
            "仓库": "github_scanner",
            "股票": "stock_api",
            "基金": "stock_api",
            "加密": "data_encrypt",
            "监控": "perf_monitor",
            "部署": "deploy_engine",
            "备份": "backup_engine",
        }
        for kw, mod in keyword_modules.items():
            if kw in text_lower and mod not in hints:
                hints.append(mod)
        # 基于动作推荐
        action_modules = {
            "scan": ["github_scanner", "security_scanner", "web_scraper"],
            "analyze": ["data_analysis", "ai_gateway", "perf_monitor"],
            "generate": ["open_lovable", "ai_gateway", "doc_generator"],
            "monitor": ["perf_monitor", "security_scanner"],
            "configure": ["config_service", "smart_scheduler"],
            "query": ["database_client", "file_manager", "ai_gateway"],
            "execute": ["task_queue_engine"],
            "notify": ["enterprise_notifier"],
            "backup": ["backup_engine"],
            "schedule": ["smart_scheduler"],
        }
        hints.extend(action_modules.get(action, []))
        return list(dict.fromkeys(hints))[:10]  # 去重+限制

    def _calculate_confidence(self, intent_type: str, action: str, 
                               modules_hint: List[str], entities: Dict) -> float:
        """计算置信度"""
        score = 0.3  # 基础分
        if action != "query":  # 有明确动作
            score += 0.2
        if modules_hint:  # 有候选模块
            score += 0.2
        if entities:  # 提取到实体
            score += 0.2
        if intent_type != IntentType.CHITCHAT.value:  # 非闲聊
            score += 0.1
        return min(score, 1.0)


# ============================================================================
# 对话上下文管理器
# ============================================================================

class ConversationManager:
    """
    对话上下文管理 — 多轮对话记忆
    
    持久化到SQLite, 支持会话级上下文
    """

    def __init__(self, db_path: str = None):
        self._db = db_path or str(Path(__file__).parent.parent / "data" / "conversation.db")
        Path(self._db).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # 内存缓存: session_id -> turns
        self._sessions: Dict[str, List[ConversationTurn]] = {}
        self._max_turns_per_session = 50

    def _init_db(self):
        """初始化对话数据库"""
        with sqlite3.connect(self._db) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    turn_count INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    intent_data TEXT DEFAULT '{}',
                    response_data TEXT DEFAULT '{}',
                    modules_used TEXT DEFAULT '[]',
                    timestamp TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_turns_session ON conversation_turns(session_id);
                CREATE INDEX IF NOT EXISTS idx_turns_time ON conversation_turns(timestamp);
            """)

    def get_or_create_session(self, session_id: str = None) -> str:
        """获取或创建会话"""
        if not session_id:
            session_id = str(uuid.uuid4())[:12]
        
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)",
                (session_id,)
            )
        return session_id

    def add_turn(self, session_id: str, user_input: str, 
                 intent: ParsedIntent, response: Dict, modules_used: List[str] = None) -> ConversationTurn:
        """添加对话轮次"""
        turn = ConversationTurn(
            id=str(uuid.uuid4())[:12],
            user_input=user_input,
            parsed_intent=asdict(intent),
            response=response,
            modules_used=modules_used or [],
        )
        
        # 持久化
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                """INSERT INTO conversation_turns 
                   (id, session_id, user_input, intent_data, response_data, modules_used) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (turn.id, session_id, user_input, 
                 json.dumps(asdict(intent), ensure_ascii=False),
                 json.dumps(response, ensure_ascii=False, default=str),
                 json.dumps(modules_used or [], ensure_ascii=False))
            )
            conn.execute(
                """UPDATE sessions SET updated_at = datetime('now'), turn_count = turn_count + 1 
                   WHERE session_id = ?""",
                (session_id,)
            )
        
        # 内存缓存
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(turn)
        if len(self._sessions[session_id]) > self._max_turns_per_session:
            self._sessions[session_id] = self._sessions[session_id][-self._max_turns_per_session:]
        
        return turn

    def get_context(self, session_id: str, last_n: int = 5) -> Dict:
        """获取对话上下文(最近N轮)"""
        turns = self._sessions.get(session_id, [])
        if not turns:
            # 从DB加载
            with sqlite3.connect(self._db) as conn:
                rows = conn.execute(
                    """SELECT user_input, intent_data, response_data, modules_used, timestamp 
                       FROM conversation_turns 
                       WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?""",
                    (session_id, last_n)
                ).fetchall()
                if rows:
                    for row in reversed(rows):
                        turn = ConversationTurn(
                            id="",
                            user_input=row[0],
                            parsed_intent=json.loads(row[1]) if row[1] else {},
                            response=json.loads(row[2]) if row[2] else {},
                            modules_used=json.loads(row[3]) if row[3] else [],
                            timestamp=row[4],
                        )
                        turns.append(turn)
                    self._sessions[session_id] = turns
        
        recent = turns[-last_n:] if turns else []
        return {
            "session_id": session_id,
            "turn_count": len(turns),
            "recent_turns": [
                {
                    "user_input": t.user_input,
                    "intent_type": t.parsed_intent.get("intent_type", ""),
                    "modules_used": t.modules_used,
                    "timestamp": t.timestamp,
                }
                for t in recent
            ],
            "last_modules": [m for t in recent for m in t.modules_used][-10:],
            "last_action": recent[-1].parsed_intent.get("primary_action", "") if recent else "",
        }

    def get_recent_modules(self, session_id: str, top_n: int = 5) -> List[str]:
        """获取最近使用的模块"""
        ctx = self.get_context(session_id)
        return ctx["last_modules"][-top_n:]

    def clear_session(self, session_id: str):
        """清除会话"""
        self._sessions.pop(session_id, None)
        with sqlite3.connect(self._db) as conn:
            conn.execute("DELETE FROM conversation_turns WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


# ============================================================================
# 数据流自动映射引擎
# ============================================================================

class DataFlowMapper:
    """
    模块间数据流自动映射
    
    根据模块能力图谱和步骤依赖, 自动生成 output→input 的字段级映射
    """

    # 常见输出→输入模式
    OUTPUT_PATTERNS = {
        "status": ["status", "health_status", "state"],
        "result": ["result", "data", "output", "response", "content"],
        "items": ["items", "list", "results", "records", "entries", "data"],
        "error": ["error", "message", "reason"],
        "id": ["id", "item_id", "record_id"],
        "count": ["count", "total", "number"],
        "metrics": ["metrics", "stats", "statistics", "performance"],
        "config": ["config", "configuration", "settings", "params"],
        "url": ["url", "link", "href", "path"],
        "score": ["score", "rating", "confidence"],
    }

    def build_data_flow(self, steps: List[Dict], capability_graph: Any = None) -> Dict[str, str]:
        """
        为工作流步骤构建数据流映射
        
        Args:
            steps: 工作流步骤列表 [{"step_id": "s1", "module_id": "xxx", "action": "yyy"}, ...]
            capability_graph: 能力图谱(可选, 用于更精确映射)
        
        Returns:
            {"steps.s1.output.data": "steps.s2.input.source_data", ...}
        """
        mappings = {}
        if len(steps) <= 1:
            return mappings
        
        for i in range(len(steps) - 1):
            src = steps[i]
            dst = steps[i + 1]
            
            src_id = src.get("step_id", f"s{i}")
            dst_id = dst.get("step_id", f"s{i+1}")
            dst_params = dst.get("params", {})
            
            # 基于目标参数名猜测需要的源输出字段
            for param_name in dst_params:
                if param_name in ("input", "task", "query", "source", "data", "text", "content"):
                    # 目标需要数据输入 → 链接上一步的输出
                    src_output_key = self._guess_output_key(src, param_name)
                    if src_output_key:
                        mappings[f"steps.{dst_id}.params.{param_name}"] = f"steps.{src_id}.output.{src_output_key}"
            
            # 自动传递: 如果上一步有output, 下一步有input, 自动链接
            src_action = src.get("action", "status")
            if src_action not in ("status", "health", "ping"):
                # 非查询动作大概率有有意义的输出
                if "steps.{dst_id}.params.input" not in mappings:
                    mappings[f"steps.{dst_id}.params.input"] = f"steps.{src_id}.output"
        
        return mappings

    def _guess_output_key(self, src_step: Dict, target_param: str) -> str:
        """猜测源步骤的输出键名"""
        src_action = src_step.get("action", "")
        module = src_step.get("module_id", "")
        
        # 基于动作类型
        action_output_map = {
            "scan": "items", "search": "items", "fetch_trending": "items",
            "analyze": "result", "generate": "output", "create": "id",
            "stats": "metrics", "status": "status",
        }
        for action_prefix, output_key in action_output_map.items():
            if action_prefix in src_action:
                return output_key
        
        # 基于模块名
        module_output_map = {
            "github_scanner": "items",
            "stock_api": "data",
            "data_analysis": "result",
            "ai_gateway": "response",
            "web_scraper": "content",
            "perf_monitor": "metrics",
        }
        for mod_prefix, output_key in module_output_map.items():
            if mod_prefix in module:
                return output_key
        
        # 默认
        return "result"


# ============================================================================
# 多步工作流规划器
# ============================================================================

class WorkflowPlanner:
    """
    多步工作流规划器
    
    将复杂任务拆解为有序步骤链, 支持并行和条件分支
    """

    def __init__(self, capability_graph: Any = None):
        self.graph = capability_graph
        self.data_flow_mapper = DataFlowMapper()
        self._plan_cache: Dict[str, WorkflowPlan] = {}

    def plan(self, task: str, intent: ParsedIntent) -> WorkflowPlan:
        """
        为任务生成工作流计划
        
        Args:
            task: 原始任务文本
            intent: 解析后的意图
        
        Returns:
            WorkflowPlan
        """
        plan_id = hashlib.md5(task.encode()).hexdigest()[:12]
        
        # 清除过期缓存（超过5分钟）并强制为特定任务重新规划
        cache_key = plan_id
        if cache_key in self._plan_cache:
            cached = self._plan_cache[cache_key]
            try:
                created = datetime.fromisoformat(cached.created_at)
                if datetime.now(timezone.utc) - created > timedelta(minutes=5):
                    del self._plan_cache[cache_key]
                else:
                    # github相关任务不使用缓存（需要实时数据）
                    task_lower = task.lower()
                    if any(kw in task_lower for kw in ["github", "trending", "开源", "趋势", "热门"]):
                        del self._plan_cache[cache_key]
                    else:
                        return cached
            except (ValueError, TypeError):
                del self._plan_cache[cache_key]
        
        if intent.intent_type == IntentType.MULTI_STEP.value and intent.sub_tasks:
            steps = self._plan_multi_step(intent.sub_tasks, intent)
        elif intent.modules_hint and len(intent.modules_hint) == 1:
            steps = self._plan_single_module(intent)
        else:
            steps = self._plan_smart_chain(task, intent)
        
        # 生成数据流映射
        step_dicts = [s if isinstance(s, dict) else asdict(s) for s in steps]
        data_flow = self.data_flow_mapper.build_data_flow(step_dicts, self.graph)
        
        # 应用数据流映射到步骤的input_mapping
        for step_dict in step_dicts:
            step_id = step_dict.get("step_id", "")
            new_mapping = {}
            for dst_key, src_expr in data_flow.items():
                if f"steps.{step_id}." in dst_key:
                    param_name = dst_key.split(".")[-1]
                    new_mapping[param_name] = src_expr
            if new_mapping:
                step_dict["input_mapping"] = {**step_dict.get("input_mapping", {}), **new_mapping}
        
        # DAG拓扑排序
        dag_order = [s.get("step_id", f"s{i}") for i, s in enumerate(step_dicts)]
        
        plan = WorkflowPlan(
            id=plan_id,
            original_task=task,
            intent=asdict(intent),
            steps=step_dicts,
            dag_order=dag_order,
            data_flow=data_flow,
        )
        
        self._plan_cache[cache_key] = plan
        return plan

    def _plan_multi_step(self, sub_tasks: List[str], intent: ParsedIntent) -> List[WorkflowStep]:
        """规划多步任务"""
        steps = []
        for i, sub_task in enumerate(sub_tasks):
            # 针对特定模块的action精确映射
            action = intent.primary_action
            module_id = intent.modules_hint[i] if i < len(intent.modules_hint) else ""
            
            # GitHub趋势查询需要使用fetch_trending而非通用的scan
            if module_id == "github_scanner" and action == "scan":
                action = "fetch_trending"
            if module_id == "githubtrending" and action == "scan":
                action = "trending"
            
            step = WorkflowStep(
                step_id=f"step_{i+1}",
                description=sub_task.strip(),
                module_id=module_id,
                action=action,
                params={"input": sub_task.strip()},
            )
            if i > 0:
                step.depends_on = [f"step_{i}"]
                step.input_mapping = {"input": f"steps.step_{i}.output"}
            steps.append(step)
        return steps

    def _plan_single_module(self, intent: ParsedIntent) -> List[WorkflowStep]:
        """规划单模块任务"""
        module_id = intent.modules_hint[0]
        action = intent.primary_action
        # 针对特定模块的action精确映射
        if module_id == "github_scanner" and action in ("scan", "query"):
            action = "fetch_trending"
        if module_id == "githubtrending" and action in ("scan", "query"):
            action = "trending"
        return [
            WorkflowStep(
                step_id="step_1",
                description=intent.params.get("input", ""),
                module_id=module_id,
                action=action,
                params=intent.params,
            )
        ]

    def _plan_smart_chain(self, task: str, intent: ParsedIntent) -> List[WorkflowStep]:
        """智能链规划 — 基于动作和模块建议生成最优链"""
        steps = []
        modules = intent.modules_hint[:5]  # 最多5步
        
        # 如果没有建议模块, 用通用链
        if not modules:
            modules = ["ai_gateway"]
        
        for i, mod in enumerate(modules):
            action = intent.primary_action if i == 0 else "analyze"
            # 针对特定模块的action精确映射
            if mod in ("github_scanner", "githubtrending") and action in ("scan", "query"):
                action = "fetch_trending" if mod == "github_scanner" else "trending"
            step = WorkflowStep(
                step_id=f"step_{i+1}",
                description=f"执行{intent.primary_action} ({mod})",
                module_id=mod,
                action=action,
                params={"input": task if i == 0 else f"基于上一步结果分析"},
            )
            if i > 0:
                step.depends_on = [f"step_{i}"]
                step.input_mapping = {"input": f"steps.step_{i}.output"}
            steps.append(step)
        
        return steps


# ============================================================================
# 智能协调器 — 主入口
# ============================================================================

class IntelligentCoordinator:
    """
    智能协调器 v1.0
    
    作为薄层注入 SystemCoordinatorV3, 增强以下能力:
    1. 自然语言意图理解
    2. 多步工作流自动规划
    3. 对话上下文连续性
    4. 模块间数据流自动映射
    5. 执行经验学习
    """

    def __init__(self):
        self.intent_parser = IntentParser()
        self.conversation_mgr = ConversationManager()
        self.workflow_planner = WorkflowPlanner()
        self.data_flow_mapper = DataFlowMapper()
        
        # 执行统计
        self._stats = {
            "total_intents": 0,
            "by_type": defaultdict(int),
            "by_complexity": defaultdict(int),
            "workflow_plans": 0,
            "avg_steps": 0.0,
        }
        
        # 经验库: 意图→模块 映射的成功率
        self._intent_module_experience: Dict[str, Dict[str, Dict]] = defaultdict(
            lambda: defaultdict(lambda: {"success": 0, "fail": 0, "total_ms": 0})
        )
        
        logger.info("[IntelligentCoordinator] 初始化完成")

    # ── 核心入口 ──

    async def process(self, task: str, session_id: str = None, 
                      module_executor: Any = None) -> Dict:
        """
        智能处理任务 — 完整闭环
        
        Args:
            task: 自然语言任务
            session_id: 会话ID(多轮对话)
            module_executor: async def(module_id, action, params) -> dict
        
        Returns:
            {"success": bool, "intent": dict, "result": dict, "workflow": dict}
        """
        start = time.monotonic()
        
        # 1. 获取/创建会话
        session_id = self.conversation_mgr.get_or_create_session(session_id)
        
        # 2. 获取对话上下文
        context = self.conversation_mgr.get_context(session_id)
        
        # 3. 解析意图
        intent = self.intent_parser.parse(task, context)
        self._stats["total_intents"] += 1
        self._stats["by_type"][intent.intent_type] += 1
        self._stats["by_complexity"][intent.complexity] += 1
        
        # 4. 结合历史经验优化模块推荐
        if context.get("last_modules"):
            intent = self._enhance_with_experience(intent, context)
        
        # 5. 生成工作流计划
        plan = self.workflow_planner.plan(task, intent)
        self._stats["workflow_plans"] += 1
        self._stats["avg_steps"] = (self._stats["avg_steps"] * (self._stats["workflow_plans"] - 1) + len(plan.steps)) / self._stats["workflow_plans"]
        
        # 6. 执行工作流
        execution_result = await self._execute_workflow(plan, module_executor)
        
        # 7. 记录对话轮次
        modules_used = [s.get("module_id", "") for s in plan.steps if s.get("module_id")]
        self.conversation_mgr.add_turn(
            session_id, task, intent, execution_result, modules_used
        )
        
        # 8. 更新经验库
        self._update_experience(intent, execution_result, start)
        
        duration = int((time.monotonic() - start) * 1000)
        
        return {
            "success": execution_result.get("success", False),
            "session_id": session_id,
            "intent": asdict(intent),
            "workflow": {
                "plan_id": plan.id,
                "steps": len(plan.steps),
                "data_flow_mappings": len(plan.data_flow),
                "dag_order": plan.dag_order,
            },
            "result": execution_result.get("final_output", execution_result),
            "modules_used": modules_used,
            "duration_ms": duration,
            "matched_by": "intelligent_coordinator",
        }

    async def _execute_workflow(self, plan: WorkflowPlan, module_executor: Any) -> Dict:
        """
        执行工作流计划
        
        串联执行步骤, 每步输出传递给下一步
        """
        if not module_executor:
            return {
                "success": False,
                "error": "no_module_executor",
                "final_output": {},
                "step_results": [],
            }
        
        shared_output = {}
        step_results = []
        success_count = 0
        fail_count = 0
        
        for step_dict in plan.steps:
            step_id = step_dict.get("step_id", "")
            module_id = step_dict.get("module_id", "")
            action = step_dict.get("action", "status")
            params = dict(step_dict.get("params", {}))
            input_mapping = step_dict.get("input_mapping", {})
            
            # 数据流映射: 将上一步输出注入当前步骤参数
            resolved_params = self._resolve_mapping(input_mapping, shared_output, step_results)
            params.update(resolved_params)
            
            # 执行 — 传递 action 和 params，由 module_executor 负责正确路由
            try:
                # 构造标准调用格式: task=action(用于展示), params 包含 action + 业务参数
                executor_params = dict(params)
                executor_params["action"] = action
                result = await asyncio.wait_for(
                    module_executor(module_id, action, executor_params),
                    timeout=step_dict.get("timeout", 30)
                )
                
                output = result.get("result", result.get("data", result.get("output", {})))
                if isinstance(output, dict):
                    shared_output.update(output)
                else:
                    shared_output["last_result"] = str(output)[:5000] if output else ""
                
                step_results.append({
                    "step_id": step_id,
                    "module_id": module_id,
                    "action": action,
                    "success": result.get("success", False),
                    "output": output,
                    "error": result.get("error", ""),
                })
                
                if result.get("success"):
                    success_count += 1
                else:
                    fail_count += 1
                    # 非关键步骤失败, 继续执行
                    if step_dict.get("retry", 0) > 0:
                        logger.warning(f"[Workflow] 步骤 {step_id} 失败: {result.get('error', '')}")
                    
            except asyncio.TimeoutError:
                step_results.append({
                    "step_id": step_id, "module_id": module_id, "action": action,
                    "success": False, "error": "timeout", "output": None,
                })
                fail_count += 1
            except Exception as e:
                step_results.append({
                    "step_id": step_id, "module_id": module_id, "action": action,
                    "success": False, "error": str(e)[:500], "output": None,
                })
                fail_count += 1
        
        return {
            "success": fail_count == 0 and success_count > 0,
            "final_output": shared_output,
            "step_results": step_results,
            "summary": f"{success_count}成功/{fail_count}失败 共{len(step_results)}步",
        }

    def _resolve_mapping(self, mapping: Dict[str, str], 
                          shared_output: Dict, step_results: List[Dict]) -> Dict:
        """解析数据流映射"""
        resolved = {}
        for param_name, expr in mapping.items():
            if not isinstance(expr, str):
                continue
            # steps.step_N.output.xxx
            if expr.startswith("steps."):
                parts = expr.split(".")
                try:
                    idx = int(parts[1].replace("step_", "")) - 1  # step_1 -> index 0
                    if 0 <= idx < len(step_results):
                        data = step_results[idx].get("output", {})
                        if len(parts) > 3:
                            for key in parts[3:]:
                                if isinstance(data, dict):
                                    data = data.get(key, "")
                                else:
                                    data = ""
                                    break
                        if data:
                            resolved[param_name] = data
                except (ValueError, IndexError):
                    pass
            elif expr.startswith("shared."):
                key = expr.split(".", 1)[1]
                if key in shared_output:
                    resolved[param_name] = shared_output[key]
        return resolved

    def _enhance_with_experience(self, intent: ParsedIntent, context: Dict) -> ParsedIntent:
        """结合历史经验优化模块推荐"""
        intent_key = f"{intent.primary_action}:{intent.intent_type}"
        exp = self._intent_module_experience.get(intent_key, {})
        
        if exp:
            # 按成功率排序已有经验模块
            scored = []
            for mod, stats in exp.items():
                total = stats["success"] + stats["fail"]
                if total > 0:
                    score = stats["success"] / total
                    scored.append((mod, score))
            scored.sort(key=lambda x: -x[1])
            
            # 将高成功率经验模块插入推荐列表前面
            for mod, _ in scored[:3]:
                if mod not in intent.modules_hint:
                    intent.modules_hint.insert(0, mod)
        
        return intent

    def _update_experience(self, intent: ParsedIntent, result: Dict, start_time: float):
        """更新执行经验"""
        duration = int((time.monotonic() - start_time) * 1000)
        intent_key = f"{intent.primary_action}:{intent.intent_type}"
        
        modules = []
        if result.get("step_results"):
            modules = [s.get("module_id", "") for s in result["step_results"] if s.get("module_id")]
        
        success = result.get("success", False)
        for mod in modules:
            exp = self._intent_module_experience[intent_key][mod]
            if success:
                exp["success"] += 1
            else:
                exp["fail"] += 1
            exp["total_ms"] += duration

    # ── 查询接口 ──

    def get_stats(self) -> Dict:
        """获取智能协调器统计"""
        return {
            "total_intents": self._stats["total_intents"],
            "by_type": dict(self._stats["by_type"]),
            "by_complexity": dict(self._stats["by_complexity"]),
            "workflow_plans": self._stats["workflow_plans"],
            "avg_steps": round(self._stats["avg_steps"], 1),
            "experience_entries": sum(len(v) for v in self._intent_module_experience.values()),
        }

    def get_experience(self, intent_key: str = None) -> Dict:
        """获取执行经验"""
        if intent_key:
            return {intent_key: dict(self._intent_module_experience.get(intent_key, {}))}
        return {
            k: {mod: dict(stats) for mod, stats in v.items()}
            for k, v in self._intent_module_experience.items()
        }

    def parse_only(self, text: str, session_id: str = None) -> Dict:
        """仅解析意图(不执行)"""
        session_id = self.conversation_mgr.get_or_create_session(session_id)
        context = self.conversation_mgr.get_context(session_id)
        intent = self.intent_parser.parse(text, context)
        plan = self.workflow_planner.plan(text, intent)
        return {
            "intent": asdict(intent),
            "workflow_preview": {
                "steps": plan.steps,
                "data_flow": plan.data_flow,
                "dag_order": plan.dag_order,
            },
            "session_id": session_id,
        }

    def get_session_context(self, session_id: str) -> Dict:
        """获取会话上下文"""
        return self.conversation_mgr.get_context(session_id)

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        """获取对话历史"""
        ctx = self.conversation_mgr.get_context(session_id, last_n=limit)
        return ctx.get("recent_turns", [])
