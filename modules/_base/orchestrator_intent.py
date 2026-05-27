"""AUTO-EVO-AI -- 意图分析器（从 agent_orchestrator.py 提取）"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple
from modules._base.orchestrator_types import IntentCategory, ModuleCapability
logger = logging.getLogger(__name__)
class AIIntentAnalyzer(object):
    """
    AI 增强的意图理解器
    使用 LLM 做深度意图解析、回退到规则引擎
    """

    SYSTEM_PROMPT = """你是一个任务拆解专家。用户会输入自然语言，你需要：
1. 分析主要意图（单选）
2. 识别次要意图（可多选）
3. 提取关键参数
4. 估计复杂度

意图分类：
- data_analysis: 数据分析、统计、报表
- document_gen: 文档生成、报告、合同
- communication: 消息通知、邮件、飞书
- rpa_desktop: 桌面操作、浏览器自动化
- strategy: 战略决策、商业分析
- security: 审批、权限、安全
- monitoring: 监控、告警、运维
- content: 内容创作、营销文案
- ecommerce: 电商、订单、库存
- finance_legal: 财税、法务
- file_operation: 文件操作、整理
- web_operation: 网页操作、API调用
- schedule: 定时任务、调度
- system: 系统管理、配置
- custom: 自定义/复杂任务

输出JSON格式：
{
  "primary_intent": "xxx",
  "confidence": 0.95,
  "secondary_intents": ["xxx", "yyy"],
  "key_params": {"时间": "今天", "对象": "张总"},
  "complexity": "medium",
  "suggestion": "简要建议"
}"""

    def __init__(self, ai_gateway=None):
        self.ai_gateway = ai_gateway
        self._rule_analyzer = IntentAnalyzer

    async def analyze(self, user_input: str) -> Tuple[IntentCategory, float, List[IntentCategory]]:
        """
        AI 增强的意图分析

        Returns:
            (主意图, 置信度, 次要意图列表)
        """
        # 尝试使用 AI
        if self.ai_gateway and self.ai_gateway.models:
            try:
                return await self._ai_analyze(user_input)
            except Exception as e:
                logger.warning(f"AI意图分析失败，降级到规则引擎: {e}")

        # 降级到规则引擎
        return self._rule_analyzer.analyze(user_input)

    async def _ai_analyze(self, user_input: str) -> Tuple[IntentCategory, float, List[IntentCategory]]:
        """使用 LLM 分析意图"""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"用户输入: {user_input}"},
        ]

        try:
            response = self.ai_gateway.chat(
                messages=messages,
                model=None,  # 使用默认模型
                temperature=0.1,
            )

            import json

            # 解析 JSON 响应
            content = response.get("content", "{}")
            # 提取 JSON
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
            else:
                result = json.loads(content)

            # 转换意图
            primary = self._str_to_intent(result.get("primary_intent", "custom"))
            confidence = float(result.get("confidence", 0.5))
            secondary = [self._str_to_intent(s) for s in result.get("secondary_intents", [])]

            logger.info(f"AI意图分析: {primary.value} ({confidence:.0%})")
            return (primary, confidence, secondary)

        except Exception as e:
            logger.warning(f"AI分析异常: {e}")
            return IntentCategory.CUSTOM, 0.3, []

    @staticmethod
    def _str_to_intent(intent_str: str) -> IntentCategory:
        """字符串转意图枚举"""
        mapping = {
            "data_analysis": IntentCategory.DATA_ANALYSIS,
            "document_gen": IntentCategory.DOCUMENT_GEN,
            "communication": IntentCategory.COMMUNICATION,
            "rpa_desktop": IntentCategory.RPA_DESKTOP,
            "strategy": IntentCategory.STRATEGY,
            "security": IntentCategory.SECURITY,
            "monitoring": IntentCategory.MONITORING,
            "content": IntentCategory.CONTENT,
            "ecommerce": IntentCategory.ECOMMERCE,
            "finance_legal": IntentCategory.FINANCE_LEGAL,
            "file_operation": IntentCategory.FILE_OPERATION,
            "web_operation": IntentCategory.WEB_OPERATION,
            "schedule": IntentCategory.SCHEDULE,
            "system": IntentCategory.SYSTEM,
            "custom": IntentCategory.CUSTOM,
        }
        return mapping.get(intent_str.lower(), IntentCategory.CUSTOM)

# ============================================================================
# 意图理解器
# ============================================================================

class IntentAnalyzer(object):
    """
    自然语言意图分析器
    基于关键词匹配 + 模式识别（无需外部LLM，可离线运行）
    """

    # 意图关键词映射
    INTENT_KEYWORDS: Dict[IntentCategory, List[str]] = {
        IntentCategory.DATA_ANALYSIS: [
            "分析",
            "统计",
            "报表",
            "趋势",
            "汇总",
            "图表",
            "数据",
            "计算",
            "dashboard",
            "kpi",
            "指标",
            "环比",
            "同比",
            "可视化",
            "透视",
        ],
        IntentCategory.DOCUMENT_GEN: [
            "生成文档",
            "写报告",
            "word",
            "pdf",
            "excel",
            "ppt",
            "合同",
            "简历",
            "方案",
            "模板",
            "文档",
            "生成",
            "导出",
            "打印",
        ],
        IntentCategory.COMMUNICATION: [
            "发消息",
            "通知",
            "邮件",
            "微信",
            "钉钉",
            "飞书",
            "短信",
            "群发",
            "提醒",
            "催办",
            "回复",
            "转发",
            "通知",
            "contact",
        ],
        IntentCategory.RPA_DESKTOP: [
            "打开",
            "点击",
            "输入",
            "截图",
            "自动化",
            "鼠标",
            "键盘",
            "操作",
            "窗口",
            "应用",
            "软件",
            "桌面",
            "rpa",
            "自动化操作",
            "浏览器",
            "网页操作",
        ],
        IntentCategory.STRATEGY: [
            "决策",
            "战略",
            "规划",
            "评估",
            "预测",
            "建议",
            "方案",
            "优化",
            "改进",
            "竞品",
            "市场",
            "分析报告",
            "商业",
        ],
        IntentCategory.SECURITY: [
            "审批",
            "授权",
            "权限",
            "安全",
            "风控",
            "审计",
            "合规",
            "隔离",
            "加密",
            "验证",
            "策略",
            "policy",
            "acl",
        ],
        IntentCategory.MONITORING: [
            "监控",
            "告警",
            "异常",
            "日志",
            "巡检",
            "健康",
            "性能",
            "cpu",
            "内存",
            "磁盘",
            "网络",
            "运维",
            "报警",
        ],
        IntentCategory.CONTENT: [
            "写文章",
            "文案",
            "营销",
            "seo",
            "标题",
            "配图",
            "发布",
            "内容",
            "创意",
            "脚本",
            "视频",
            "短视频",
            "推广",
            "社交媒体",
        ],
        IntentCategory.ECOMMERCE: [
            "订单",
            "库存",
            "商品",
            "上架",
            "下架",
            "价格",
            "促销",
            "电商",
            "店铺",
            "物流",
            "退款",
            "客服",
            "采购",
        ],
        IntentCategory.FINANCE_LEGAL: [
            "发票",
            "报税",
            "财务",
            "合同审查",
            "法律",
            "合规",
            "账单",
            "成本",
            "收入",
            "税务",
            "法务",
        ],
        IntentCategory.FILE_OPERATION: [
            "文件",
            "文件夹",
            "移动",
            "复制",
            "删除",
            "重命名",
            "整理",
            "归档",
            "备份",
            "压缩",
            "下载",
            "上传",
        ],
        IntentCategory.WEB_OPERATION: [
            "网页",
            "网站",
            "爬取",
            "抓取",
            "搜索",
            "浏览",
            "url",
            "api调用",
            "接口",
            "请求",
            "http",
        ],
        IntentCategory.SCHEDULE: [
            "定时",
            "每天",
            "每周",
            "每月",
            "计划",
            "日程",
            "提醒",
            "定期",
            "cron",
            "自动执行",
            "循环",
        ],
        IntentCategory.SYSTEM: [
            "配置",
            "设置",
            "重启",
            "更新",
            "安装",
            "部署",
            "系统",
            "模块",
            "插件",
            "版本",
            "升级",
            "环境",
        ],
        IntentCategory.CUSTOM: ["复合任务", "多步骤", "流程", "帮我", "请"],
    }

    # 复合意图模式
    COMPOUND_PATTERNS: List[Tuple[str, IntentCategory, IntentCategory]] = [
        # (模式, 主要意图, 次要意图)
        (r"分析.*(?:发|通知|邮件)", IntentCategory.DATA_ANALYSIS, IntentCategory.COMMUNICATION),
        (r"生成.*(?:发|通知|邮件)", IntentCategory.DOCUMENT_GEN, IntentCategory.COMMUNICATION),
        (r"监控.*(?:告警|通知|邮件)", IntentCategory.MONITORING, IntentCategory.COMMUNICATION),
        (r"审批.*(?:通知|邮件|消息)", IntentCategory.SECURITY, IntentCategory.COMMUNICATION),
        (r"(?:写|生成).*(?:分析|报告)", IntentCategory.DOCUMENT_GEN, IntentCategory.DATA_ANALYSIS),
        (r"(?:操作|打开).*(?:截图|监控)", IntentCategory.RPA_DESKTOP, IntentCategory.MONITORING),
        (r"(?:自动|定时).*(?:分析|报告|整理)", IntentCategory.SCHEDULE, IntentCategory.DATA_ANALYSIS),
    ]

    @classmethod
    def analyze(cls, user_input: str) -> Tuple[IntentCategory, float, List[IntentCategory]]:
        """
        分析用户输入意图

        Returns:
            (主意图, 置信度, 次要意图列表)
        """
        text = user_input.lower().strip()
        scores: Dict[IntentCategory, float] = {}

        # 1. 关键词评分
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            score = sum(2.0 for kw in keywords if kw in text)
            # 长关键词权重更高
            score += sum(len(kw) * 0.1 for kw in keywords if kw in text)
            scores[intent] = score

        # 2. 复合模式检测
        secondary_intents: List[IntentCategory] = []
        for pattern, primary, secondary in cls.COMPOUND_PATTERNS:
            if re.search(pattern, text):
                scores[primary] = scores.get(primary, 0) + 3.0
                if secondary not in secondary_intents:
                    secondary_intents.append(secondary)

        # 3. 排序
        if not scores or max(scores.values()) == 0:
            return (IntentCategory.CUSTOM, 0.3, secondary_intents)

        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent, top_score = sorted_intents[0]
        confidence = min(top_score / 5.0, 1.0)

        # 收集次要意图
        for intent, score in sorted_intents[1:4]:
            if score > 0.5 and intent not in secondary_intents:
                secondary_intents.append(intent)

        return (primary_intent, confidence, secondary_intents)
