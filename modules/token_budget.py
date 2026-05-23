"""
AUTO-EVO-AI V0.1 - Token Budget Control Module
基于 Mercury Agent 的Token预算控制系统

Token预算控制帮助管理AI API的使用成本：
- 每日预算设置和追踪
- 70%时自动启用精简模式
- 支持覆盖和重置
- 使用量可视化

作者: AUTO-EVO-AI Team
版本: V0.1.0
"""

__module_meta__ = {
    "id": "token-budget",
    "name": "Token Budget",
    "version": "1.0.0",
    "group": "auth",
    "inputs": [
        {"name": "tokens", "type": "string", "required": True, "description": ""},
        {"name": "model", "type": "string", "required": True, "description": ""},
        {"name": "config_path", "type": "string", "required": True, "description": ""},
        {"name": "daily_limit", "type": "string", "required": True, "description": ""},
        {"name": "tokens_to_use", "type": "string", "required": True, "description": ""},
        {"name": "tokens", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "success", "type": "bool", "description": "是否成功"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["manager", "token"],
    "grade": "C",
    "description": "AUTO-EVO-AI V0.1 - Token Budget Control Module 基于 Mercury Agent 的Token预算控制系统",
}

import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta, date
from enum import Enum
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

DEFAULT_BUDGET = 100000  # 默认每日10万tokens
CONCISE_THRESHOLD = 0.70  # 70%时启用精简模式
WARNING_THRESHOLD = 0.90  # 90%时发出警告
DEFAULT_CONFIG_PATH = "~/.workbuddy/token-budget.json"

# 模型Token单价（每1000 tokens的价格，美元）
MODEL_PRICING = {
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.00015,
    "gpt-4-turbo": 0.01,
    "claude-3-opus": 0.015,
    "claude-3-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    "deepseek-chat": 0.00014,
    "gemini-pro": 0.00125,
}

class BudgetMode(Enum):
    """预算模式"""

    NORMAL = "normal"  # 正常模式
    CONCISE = "concise"  # 精简模式
    PAUSED = "paused"  # 暂停使用
    UNLIMITED = "unlimited"  # 无限制

@dataclass
class BudgetStatus:
    """预算状态"""

    daily_limit: int
    used_today: int
    remaining: int
    percentage: float
    mode: BudgetMode
    is_concise: bool
    is_warning: bool
    days_until_reset: int
    estimated_cost_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "daily_limit": self.daily_limit,
            "used_today": self.used_today,
            "remaining": self.remaining,
            "percentage": f"{self.percentage:.1%}",
            "mode": self.mode.value,
            "is_concise": self.is_concise,
            "is_warning": self.is_warning,
            "days_until_reset": self.days_until_reset,
            "estimated_cost_usd": f"${self.estimated_cost_usd:.4f}",
        }

@dataclass
class UsageRecord:
    """使用记录"""

    timestamp: datetime
    tokens: int
    model: str
    cost_usd: float
    conversation_id: str
    request_type: str = "chat"

# ============================================================================
# 核心类
# ============================================================================

class TokenBudgetManager(object):
    """
    Token预算管理器

    功能:
    - 每日预算设置和追踪
    - 70%时自动启用精简模式
    - 支持单次请求覆盖
    - 使用量可视化
    - 多供应商支持

    使用示例:
    ```python
    manager = TokenBudgetManager()

    # 检查预算
    if manager.check_budget(5000):
        # 执行请求
        result = make_api_call(...)
        manager.record_usage(5000, 'gpt-4o-mini')
    else:
        print("预算不足")

    # 获取状态
    status = manager.get_status()
    print(f"已使用 {status.percentage:.1%}")

    # 重置
    manager.reset_daily()
    ```
    """

    def __init__(self, config_path: Optional[str] = None, daily_limit: Optional[int] = None):
        """
        初始化Token预算管理器

        Args:
            config_path: 配置文件路径
            daily_limit: 默认每日限额
        """
        self.config_path = Path(config_path or DEFAULT_CONFIG_PATH).expanduser()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self._load_config()

        # 设置每日限额
        if daily_limit:
            self.daily_limit = daily_limit
        elif self.daily_limit == 0:
            self.daily_limit = DEFAULT_BUDGET

        # 当前模式
        self.current_mode = BudgetMode.NORMAL
        self._concise_override = False

    def _load_config(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                self.daily_limit = data.get("daily_limit", DEFAULT_BUDGET)
                self.model_pricing = data.get("model_pricing", MODEL_PRICING)
                self.last_reset = data.get("last_reset", None)
            except Exception:
                self._init_default_config()
        else:
            self._init_default_config()

    def _init_default_config(self):
        """初始化默认配置"""
        self.daily_limit = DEFAULT_BUDGET
        self.model_pricing = MODEL_PRICING.copy()
        self.last_reset = None

    def _save_config(self):
        """保存配置"""
        data = {"daily_limit": self.daily_limit, "model_pricing": self.model_pricing, "last_reset": self.last_reset}
        self.config_path.write_text(json.dumps(data, indent=2))

    def _get_today(self) -> str:
        """获取今天的日期字符串"""
        return date.today().isoformat()

    def _check_and_reset(self):
        """检查是否需要重置"""
        today = self._get_today()

        if self.last_reset != today:
            # 新的一天，重置使用量
            self.daily_usage = 0
            self.daily_records = []
            self.last_reset = today
            self.current_mode = BudgetMode.NORMAL
            self._save_config()

    def check_budget(self, tokens_to_use: int) -> bool:
        """
        检查预算是否足够

        Args:
            tokens_to_use: 计划使用的token数量

        Returns:
            bool: 是否可以使用
        """
        self._check_and_reset()

        # 无限制模式
        if self.current_mode == BudgetMode.UNLIMITED:
            return True

        # 暂停模式
        if self.current_mode == BudgetMode.PAUSED:
            return False

        # 检查剩余
        return (self.daily_usage + tokens_to_use) <= self.daily_limit

    def record_usage(
        self, tokens: int, model: str = "gpt-4o-mini", conversation_id: str = "default", request_type: str = "chat"
    ) -> bool:
        """
        记录Token使用

        Args:
            tokens: 使用的token数量
            model: 使用的模型
            conversation_id: 对话ID
            request_type: 请求类型

        Returns:
            bool: 是否成功记录
        """
        self._check_and_reset()

        # 检查是否超过预算
        if not self.check_budget(tokens):
            return False

        # 初始化
        if not hasattr(self, "daily_usage"):
            self.daily_usage = 0
        if not hasattr(self, "daily_records"):
            self.daily_records = []

        # 更新使用量
        self.daily_usage += tokens

        # 计算成本
        cost = self._calculate_cost(tokens, model)

        # 记录
        record = UsageRecord(
            timestamp=datetime.now(),
            tokens=tokens,
            model=model,
            cost_usd=cost,
            conversation_id=conversation_id,
            request_type=request_type,
        )
        self.daily_records.append(record)

        # 检查是否需要切换模式
        self._update_mode()

        return True

    def _calculate_cost(self, tokens: int, model: str) -> float:
        """计算成本"""
        price = self.model_pricing.get(model, 0.001)  # 默认0.001美元/1K tokens
        return (tokens / 1000) * price

    def _update_mode(self):
        """更新预算模式"""
        if not hasattr(self, "daily_usage"):
            return

        percentage = self.daily_usage / self.daily_limit

        # 检查阈值
        if percentage >= 1.0:
            self.current_mode = BudgetMode.PAUSED
        elif percentage >= CONCISE_THRESHOLD and not self._concise_override:
            self.current_mode = BudgetMode.CONCISE
        else:
            self.current_mode = BudgetMode.NORMAL

    def should_use_concise_mode(self) -> bool:
        """
        检查是否应该使用精简模式

        超过70%时自动启用

        Returns:
            bool: 是否启用精简模式
        """
        self._check_and_reset()

        if self._concise_override:
            return True

        if not hasattr(self, "daily_usage"):
            return False

        percentage = self.daily_usage / self.daily_limit
        return percentage >= CONCISE_THRESHOLD

    def set_mode(self, mode: BudgetMode):
        """设置预算模式"""
        self.current_mode = mode
        self._concise_override = mode == BudgetMode.CONCISE

    def override_concise(self, enable: bool = True):
        """覆盖精简模式设置"""
        self._concise_override = enable
        if enable:
            self.current_mode = BudgetMode.CONCISE

    def get_status(self) -> BudgetStatus:
        """
        获取当前预算状态

        Returns:
            BudgetStatus: 预算状态
        """
        self._check_and_reset()

        # 初始化
        if not hasattr(self, "daily_usage"):
            self.daily_usage = 0
        if not hasattr(self, "daily_records"):
            self.daily_records = []

        remaining = max(0, self.daily_limit - self.daily_usage)
        percentage = self.daily_usage / self.daily_limit if self.daily_limit > 0 else 0

        # 计算估计成本
        total_cost = sum(r.cost_usd for r in self.daily_records)

        # 计算距离重置的时间
        now = datetime.now()
        tomorrow = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
        days_until_reset = max(1, (tomorrow - now).days)

        return BudgetStatus(
            daily_limit=self.daily_limit,
            used_today=self.daily_usage,
            remaining=remaining,
            percentage=percentage,
            mode=self.current_mode,
            is_concise=self.should_use_concise_mode(),
            is_warning=percentage >= WARNING_THRESHOLD,
            days_until_reset=days_until_reset,
            estimated_cost_usd=total_cost,
        )

    def reset_daily(self):
        """重置每日使用量"""
        self.daily_usage = 0
        self.daily_records = []
        self.last_reset = self._get_today()
        self.current_mode = BudgetMode.NORMAL
        self._concise_override = False
        self._save_config()

    def set_daily_limit(self, limit: int):
        """设置每日限额"""
        if limit < 0:
            raise ValueError("限额不能为负数")
        self.daily_limit = limit
        self._save_config()
        self._update_mode()

    def add_usage(self, tokens: int, model: str = "gpt-4o-mini", conversation_id: str = "default") -> bool:
        """
        添加使用量（别名方法）

        Args:
            tokens: token数量
            model: 模型
            conversation_id: 对话ID

        Returns:
            bool: 是否成功
        """
        return self.record_usage(tokens, model, conversation_id)

    def get_usage_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取使用历史

        Args:
            days: 查询天数

        Returns:
            List[Dict]: 使用历史
        """
        # 实际应从持久化存储中读取
        # 这里返回内存中的记录
        if not hasattr(self, "daily_records"):
            return []

        cutoff = datetime.now() - timedelta(days=days)
        records = [r for r in self.daily_records if r.timestamp >= cutoff]

        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "tokens": r.tokens,
                "model": r.model,
                "cost_usd": r.cost_usd,
                "conversation_id": r.conversation_id,
            }
            for r in records
        ]

    def get_weekly_report(self) -> Dict[str, Any]:
        """
        获取周报

        Returns:
            Dict: 周报数据
        """
        self._check_and_reset()

        # 模拟周数据
        days = 7
        avg_daily = self.daily_usage / 1 if hasattr(self, "daily_usage") else 0

        return {
            "period": f"过去{days}天",
            "total_tokens": self.daily_usage * days,
            "avg_daily_tokens": avg_daily,
            "current_usage_percentage": f"{self.daily_usage / self.daily_limit:.1%}" if self.daily_limit else "0%",
            "estimated_cost": f"${self.daily_usage * 0.00015 * days:.2f}",
            "current_mode": self.current_mode.value,
            "days_until_limit": self._days_until_limit(),
        }

    def _days_until_limit(self) -> int:
        """估算距离用完限额的天数"""
        if not hasattr(self, "daily_usage") or self.daily_usage == 0:
            return 999

        daily_rate = self.daily_usage
        if daily_rate == 0:
            return 999

        return self.remaining // daily_rate if hasattr(self, "remaining") else 999

    def estimate_cost(self, tokens: int, model: Optional[str] = None) -> float:
        """
        估算成本

        Args:
            tokens: token数量
            model: 模型名称

        Returns:
            float: 成本（美元）
        """
        model = model or "gpt-4o-mini"
        return self._calculate_cost(tokens, model)

    def format_concise_prompt(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        格式化精简提示

        当Token使用超过70%时，自动精简提示以减少Token消耗。

        Args:
            prompt: 原始提示
            max_tokens: 最大token数

        Returns:
            str: 精简后的提示
        """
        # 简单的精简策略
        # 实际应用中可以使用LLM来精简

        lines = prompt.split("\n")
        concise_lines = []
        current_tokens = 0

        for line in lines:
            line_tokens = len(line) // 4

            if current_tokens + line_tokens <= max_tokens:
                concise_lines.append(line)
                current_tokens += line_tokens
            else:
                # 添加截断说明
                concise_lines.append(f"\n[内容已精简，原长度 {len(prompt)} 字符]")
                break

        return "\n".join(concise_lines)

    def create_concise_context(self, context: str, max_tokens: int = 1000) -> str:
        """
        创建精简的上下文

        在精简模式下，减少非必要的信息。

        Args:
            context: 原始上下文
            max_tokens: 最大token数

        Returns:
            str: 精简后的上下文
        """
        # 移除详细说明
        lines = context.split("\n")
        精简_lines = []

        skip_patterns = ["详细说明", "完整示例", "下面是", "例如：", "比如："]

        for line in lines:
            skip = False
            for pattern in skip_patterns:
                if pattern in line:
                    skip = True
                    break

            if not skip:
                精简_lines.append(line)

        result = "\n".join(精简_lines)

        # 如果还是太长，继续精简
        if len(result) > max_tokens * 4:
            result = result[: max_tokens * 4] + "\n[内容已截断]"

        return result

    def set_model_price(self, model: str, price_per_1k: float):
        """设置模型价格"""
        self.model_pricing[model] = price_per_1k
        self._save_config()

    def get_cost_breakdown(self) -> Dict[str, float]:
        """获取按模型分类的成本"""
        breakdown = {}

        if not hasattr(self, "daily_records"):
            return breakdown

        for record in self.daily_records:
            model = record.model
            if model not in breakdown:
                breakdown[model] = 0
            breakdown[model] += record.cost_usd

        return breakdown

    def to_markdown(self) -> str:
        """生成Markdown格式的状态报告"""
        status = self.get_status()

        lines = [
            "## Token预算状态\n",
            f"| 项目 | 数值 |",
            f"|------|------|",
            f"| 每日限额 | {status.daily_limit:,} tokens |",
            f"| 今日使用 | {status.used_today:,} tokens |",
            f"| 剩余 | {status.remaining:,} tokens |",
            f"| 使用比例 | {status.percentage:.1%} |",
            f"| 当前模式 | {status.mode.value} |",
            f"| 精简模式 | {'是' if status.is_concise else '否'} |",
            f"| 警告 | {'是' if status.is_warning else '否'} |",
            f"| 估计成本 | ${status.estimated_cost_usd:.4f} |",
            f"| 重置倒计时 | {status.days_until_reset}天 |",
        ]

        return "\n".join(lines)

# ============================================================================
# 快捷函数
# ============================================================================

_manager_instance: Optional[TokenBudgetManager] = None

def get_manager() -> TokenBudgetManager:
    """获取单例预算管理器"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = TokenBudgetManager()
    return _manager_instance

def check_and_use(tokens: int, model: str = "gpt-4o-mini") -> bool:
    """快捷函数：检查并记录使用"""
    manager = get_manager()
    if manager.check_budget(tokens):
        return manager.record_usage(tokens, model)
    return False

def get_budget_status() -> BudgetStatus:
    """快捷函数：获取预算状态"""
    return get_manager().get_status()

def reset_budget():
    """快捷函数：重置预算"""
    get_manager().reset_daily()

# ============================================================================
# 示例和使用
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("AUTO-EVO-AI V0.1 - Token Budget Module")
    print("=" * 60)

    # 创建管理器
    manager = TokenBudgetManager()

    # 设置每日限额
    manager.set_daily_limit(50000)  # 5万tokens
    print("\n📊 已设置每日限额: 50,000 tokens")

    # 模拟使用
    print("\n💬 模拟使用场景:")

    scenarios = [
        (1000, "gpt-4o-mini", "首次问候"),
        (2000, "gpt-4o-mini", "查询数据"),
        (5000, "gpt-4o", "复杂分析"),
        (3000, "gpt-4o-mini", "再次查询"),
    ]

    for tokens, model, desc in scenarios:
        success = manager.record_usage(tokens, model, "test-conv")
        cost = manager._calculate_cost(tokens, model)

        status = "✅" if success else "❌"
        concise = " [精简]" if manager.should_use_concise_mode() else ""

        print(f"   {status} {desc}: {tokens} tokens ({model}) - ${cost:.6f}{concise}")

    # 获取状态
    status = manager.get_status()
    print("\n📈 当前预算状态:")
    print(f"   - 已使用: {status.used_today:,} / {status.daily_limit:,}")
    print(f"   - 剩余: {status.remaining:,} tokens")
    print(f"   - 使用比例: {status.percentage:.1%}")
    print(f"   - 当前模式: {status.mode.value}")
    print(f"   - 精简模式: {'是' if status.is_concise else '否'}")
    print(f"   - 估计成本: ${status.estimated_cost_usd:.6f}")

    # 成本分析
    print("\n💰 成本分析:")
    breakdown = manager.get_cost_breakdown()
    for model, cost in breakdown.items():
        print(f"   - {model}: ${cost:.6f}")

    # 精简模式测试
    print("\n📝 精简模式提示:")
    if manager.should_use_concise_mode():
        print("   ⚠️ 已启用精简模式，减少非必要信息")
        test_context = "这是一个详细的上下文。详细说明：第一步做什么，第二步做什么，第三步做什么。"
        concise = manager.create_concise_context(test_context, max_tokens=500)
        print(f"   精简后: {concise[:100]}...")

    # 周报
    print("\n📅 周报:")
    report = manager.get_weekly_report()
    for key, value in report.items():
        print(f"   - {key}: {value}")

    # Markdown报告
    print("\n📄 Markdown报告:")
    print(manager.to_markdown())

    print("\n" + "=" * 60)
    print("Token Budget Module 测试完成!")
    print("=" * 60)

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """执行入口 - 路由到token_budget业务方法"""
        params = params or {}
        self.trace("token_budget.execute", "start", action=action)
        self.metrics_collector.counter("token_budget.execute.total", 1)
        try:
            a = (action or "status").lower().strip()
            if a == "_load_config":
                result = self._load_config(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_load_config"
                self.metrics_collector.counter("token_budget.execute._load_config", 1)
                return result
            if a == "_init_default_config":
                result = self._init_default_config(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_init_default_config"
                self.metrics_collector.counter("token_budget.execute._init_default_config", 1)
                return result
            if a == "_save_config":
                result = self._save_config(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_save_config"
                self.metrics_collector.counter("token_budget.execute._save_config", 1)
                return result
            if a == "_get_today":
                result = self._get_today(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_get_today"
                self.metrics_collector.counter("token_budget.execute._get_today", 1)
                return result
            if a == "_check_and_reset":
                result = self._check_and_reset(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_check_and_reset"
                self.metrics_collector.counter("token_budget.execute._check_and_reset", 1)
                return result
            if a == "check_budget":
                result = self.check_budget(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "check_budget"
                self.metrics_collector.counter("token_budget.execute.check_budget", 1)
                return result
            if a == "_calculate_cost":
                result = self._calculate_cost(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_calculate_cost"
                self.metrics_collector.counter("token_budget.execute._calculate_cost", 1)
                return result
            if a == "_update_mode":
                result = self._update_mode(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_update_mode"
                self.metrics_collector.counter("token_budget.execute._update_mode", 1)
                return result
            if a == "should_use_concise_mode":
                result = self.should_use_concise_mode(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "should_use_concise_mode"
                self.metrics_collector.counter("token_budget.execute.should_use_concise_mode", 1)
                return result
            if a == "set_mode":
                result = self.set_mode(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "set_mode"
                self.metrics_collector.counter("token_budget.execute.set_mode", 1)
                return result
            if a == "override_concise":
                result = self.override_concise(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "override_concise"
                self.metrics_collector.counter("token_budget.execute.override_concise", 1)
                return result
            if a == "reset_daily":
                result = self.reset_daily(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "reset_daily"
                self.metrics_collector.counter("token_budget.execute.reset_daily", 1)
                return result
            if a == "set_daily_limit":
                result = self.set_daily_limit(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "set_daily_limit"
                self.metrics_collector.counter("token_budget.execute.set_daily_limit", 1)
                return result
            if a == "get_weekly_report":
                result = self.get_weekly_report(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "get_weekly_report"
                self.metrics_collector.counter("token_budget.execute.get_weekly_report", 1)
                return result
            if a == "_days_until_limit":
                result = self._days_until_limit(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_days_until_limit"
                self.metrics_collector.counter("token_budget.execute._days_until_limit", 1)
                return result
            if a == "set_model_price":
                result = self.set_model_price(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "set_model_price"
                self.metrics_collector.counter("token_budget.execute.set_model_price", 1)
                return result
            if a == "get_cost_breakdown":
                result = self.get_cost_breakdown(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "get_cost_breakdown"
                self.metrics_collector.counter("token_budget.execute.get_cost_breakdown", 1)
                return result
            if a == "to_markdown":
                result = self.to_markdown(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "to_markdown"
                self.metrics_collector.counter("token_budget.execute.to_markdown", 1)
                return result
            if a in ("status", "info", "stats", "health"):
                return {"success": True, "status": "running", "module": "token_budget", "health": self.health_check()}
            if a == "help":
                return {
                    "actions": [
                        "_load_config",
                        "_init_default_config",
                        "_save_config",
                        "_get_today",
                        "_check_and_reset",
                        "check_budget",
                        "_calculate_cost",
                        "_update_mode",
                        "should_use_concise_mode",
                        "set_mode",
                        "override_concise",
                        "reset_daily",
                        "set_daily_limit",
                        "get_weekly_report",
                        "_days_until_limit",
                    ],
                    "module": "token_budget",
                }
            return {
                "success": True,
                "action": a,
                "module": "token_budget",
                "available": [
                    "_load_config",
                    "_init_default_config",
                    "_save_config",
                    "_get_today",
                    "_check_and_reset",
                    "check_budget",
                    "_calculate_cost",
                    "_update_mode",
                    "should_use_concise_mode",
                    "set_mode",
                ],
            }
        except Exception as e:
            self.metrics_collector.counter("token_budget.execute.error", 1)
            return {"success": False, "error": str(e), "action": action}

def shutdown(self) -> dict:
    self.trace("token_budget.shutdown", "start")
    self.status = "stopped"
    self.trace("token_budget.shutdown", "end")
    return {"success": True, "module": "token_budget"}

def health_check(self) -> dict:
    return {"status": "healthy", "module": "token_budget", "version": getattr(self, "version", "1.0.0")}

def initialize(self) -> dict:
    self.trace("token_budget.initialize", "start")
    self.metrics_collector.gauge("token_budget.initialized", 1)
    self.audit("初始化token_budget", level="info")
    self.trace("token_budget.initialize", "end")
    return {"success": True, "module": "token_budget"}

module_class = TokenBudgetManager
