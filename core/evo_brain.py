#!/usr/bin/env python3
"""
AUTO-EVO-AI V0.1 主编排器 - 系统大脑
使用LLM做真实语义理解，正则降级兜底
"""
import json, re, asyncio, logging, hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
from .evolution_engine import engine as evo_engine  # AdaptiveEngine 单例

logger = logging.getLogger(__name__)

class EvoBrain:
    """主编排器 - LLM驱动意图理解 + 正则降级"""

    # 意图 -> (模块列表, 中文描述)
    INTENT_MAP: Dict[str, tuple] = {
        'search':      (['browser_auto','githubtrending','web_search'],           '搜索/查找'),
        'monitor':     (['system_monitor','incident_manager','health_monitor'],   '监控/追踪'),
        'automation':  (['cron_scheduler','workflow_manager','trigger_engine'],   '自动化/定时'),
        'analysis':    (['data_analysis','chart_engine','excel_engine'],          '分析/统计'),
        'generate':    (['doc_automation','code_generator','export_engine'],      '生成/创建'),
        'notify':      (['enterprise_notifier','feishu_notifier','email_automation','sms_gateway'], '通知/发送'),
        'translate':   (['translation_service','nlp_engine'],                     '翻译'),
        'report':      (['data_analysis','chart_engine'],                         '报告/总结'),
        'query':       (['database_manager','elasticsearch_search','sql_generator'],'查询/检索'),
        'code':        (['code_review','code_quality','code_sandbox','agent_hephaestus'], '代码/开发'),
        'deploy':      (['docker_deploy','k8s_orch','release_manager','rollback_manager'], '部署/发布'),
        'chat':        (['llm_openai','llm_claude','llm_gemini'],                 '对话/咨询'),
    }

    def __init__(self, module_manager):
        self.mm = module_manager
        self.context: Dict[str, Any] = {}
        self.history: List[Dict] = []
        self._llm_available = False

    async def think(self, user_input: str) -> Dict[str, Any]:
        """核心思考：先用LLM语义理解，正则兜底"""
        user_input = user_input.strip()
        if not user_input:
            return self._fallback('general', user_input, 0.0)

        result = None
        # 主路径：LLM语义理解
        try:
            result = await self._llm_understand(user_input)
        except Exception as e:
            logger.warning(f'[EvoBrain] LLM理解失败: {e}')

        # 降级：正则匹配
        if not result or result.get('confidence', 0) < 0.3:
            result = self._regex_understand(user_input)

        plan = self._generate_plan(result, user_input)
        entry = {
            'user_input': user_input, 'intent': result['intent'],
            'modules': result['modules'], 'params': result.get('params', {}),
            'plan': plan, 'confidence': round(result.get('confidence', 0), 3),
            'timestamp': datetime.now().isoformat(),
        }
        self.history.append(entry)
        if len(self.history) > 50:
            self.history = self.history[-50:]
        return entry

    async def _llm_understand(self, text: str) -> Optional[Dict]:
        """调用LLM做意图理解"""
        gateway = self.mm.get_module('ai_gateway')
        if not gateway:
            return None
        system_prompt = f'''你是一个意图分类引擎。从以下意图中选择最匹配的一个：
{chr(10).join(f'- {k}: {v[1]}' for k,v in self.INTENT_MAP.items())}
返回 JSON: {{"intent":"意图名","confidence":0.0~1.0,"params":{{"key":"提取的关键参数"}}}}
只返回JSON，不要多余文字。'''
        try:
            r = await gateway.execute('chat', {
                'messages': [{'role':'system','content':system_prompt},{'role':'user','content':f'分析意图: {text}'}],
                'model': 'auto', 'temperature': 0.1, 'max_tokens': 300,
            })
            content = ''
            if isinstance(r, dict):
                for k in ('response', 'content', 'message', 'reply', 'text', 'result', 'data'):
                    v = r.get(k)
                    if v:
                        if isinstance(v, dict): content = v.get('content', '') or str(v)
                        elif isinstance(v, str): content = v
                        break
            if not content:
                return None
            content = content.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            data = json.loads(content)
            intent = data.get('intent', '').lower().strip()
            if intent not in self.INTENT_MAP:
                intent = 'chat'
            modules = self.INTENT_MAP.get(intent, self.INTENT_MAP['chat'])[0]
            return {
                'intent': intent, 'modules': modules,
                'params': data.get('params', {}), 'confidence': float(data.get('confidence', 0.5)),
            }
        except Exception as e:
            logger.debug(f'[EvoBrain] LLM parse fail: {e}')
            return None

    def _regex_understand(self, text: str) -> Dict:
        """正则兜底"""
        rules = [
            (r'搜索|查找|查一下|帮我找',          'search'),
            (r'监控|追踪|关注|跟踪|看.*状态',       'monitor'),
            (r'自动|定时|定期|每[天周月小时分]',     'automation'),
            (r'分析|统计|汇总|对比|趋势',           'analysis'),
            (r'生成|创建|制作|画|绘图|写.*报告',     'generate'),
            (r'发送|通知|提醒|推送|告警',           'notify'),
            (r'翻译|转译|译成',                    'translate'),
            (r'周报|月报|日报|总结|报告',           'report'),
            (r'查询|检索|搜|获取.*数据|查.*数据',    'query'),
            (r'代码|审查|提交|合并|deploy|部署',    'code'),
            (r'部署|上线|发布|发布到',              'deploy'),
            (r'你好|嗨|hi|hello|在吗',              'chat'),
        ]
        best_score, best_intent = 0, 'chat'
        for pat, intent in rules:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                score = len(m.group()) + len(pat) * 0.05
                if score > best_score:
                    best_score, best_intent = score, intent
        modules = self.INTENT_MAP.get(best_intent, self.INTENT_MAP['chat'])[0]
        return {'intent': best_intent, 'modules': modules,
                'params': {'raw': text}, 'confidence': min(best_score / 5, 1.0)}

    def _generate_plan(self, result: Dict, text: str) -> List[str]:
        """生成可执行步骤"""
        steps = [f'理解意图: {result.get("intent","未知")}']
        modules = result.get('modules', [])
        if modules:
            steps.append(f'加载模块: {", ".join(modules)}')
            steps.append(f'执行参数: {json.dumps(result.get("params",{}), ensure_ascii=False)}')
        return steps

    def get_context(self, key: str = None):
        return self.context if key is None else self.context.get(key)

    def set_context(self, key: str, value: Any):
        self.context[key] = value

    def get_history(self, n: int = 10) -> List[Dict]:
        return self.history[-n:]

    def clear_history(self):
        self.history.clear()

    def suggest_best_module(self, intent: str = "", candidates: List[str] = None) -> Optional[str]:
        """
        根据进化引擎的评分推荐最佳模块。
        - intent: 意图描述（可选）
        - candidates: 候选模块列表
        返回: 最佳模块名，或 None
        """
        if candidates:
            scored = []
            for m in candidates:
                s = evo_engine.score_module(m)
                if s:
                    scored.append((m, s["score"]))
            if not scored:
                return candidates[0] if candidates else None
            scored.sort(key=lambda x: x[1], reverse=True)
            best = scored[0][0]
            if scored[0][1] < 0.5:
                logger.info(f"[EVO] adaptive: {best} score={scored[0][1]:.3f} low, returning anyway")
            return best
        # 无候选时返回评分最高的模块
        ranked = evo_engine.ranking(1)
        return ranked[0]["module"] if ranked else None

    def get_adaptive_route(self, intent: str, candidates: List[str]) -> Dict:
        """
        自适应路由：返回候选模块的评分排序。
        用于 UI 展示和手动选择。
        """
        scored = []
        for m in candidates:
            s = evo_engine.score_module(m)
            if s:
                scored.append({
                    "module": m,
                    "score": s["score"],
                    "success_rate": s["success_rate"],
                    "avg_latency_ms": s["avg_latency_ms"],
                    "state": s["state"],
                })
            else:
                scored.append({
                    "module": m,
                    "score": 0.5,
                    "success_rate": 0,
                    "avg_latency_ms": 0,
                    "state": "unknown",
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return {
            "intent": intent,
            "candidates": scored,
            "recommended": scored[0]["module"] if scored else None,
            "has_evolution_data": len(scored) > 0,
        }
