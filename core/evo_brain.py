#!/usr/bin/env python3
"""
AUTO-EVO-AI V0.1 主编排器 - 系统大脑
一句话完成复杂任务的智能调度中心
"""

import json
import re
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

class EvoBrain:
    """主编排器 - 理解用户意图并调度合适模块"""

    def __init__(self, module_manager):
        self.mm = module_manager
        self.context = {}  # 对话上下文
        self.history = []  # 执行历史

    async def think(self, user_input: str) -> Dict[str, Any]:
        """
        核心思考：理解用户意图并规划执行方案
        返回: {
            "intent": str,           # 识别的意图
            "modules": List[str],    # 需要调用的模块
            "params": Dict,          # 传递给模块的参数
            "plan": List[str],      # 执行步骤
            "confidence": float     # 置信度
        }
        """
        user_input = user_input.strip()

        # 意图识别规则
        intent_rules = [
            # (关键词模式, 意图类型, 触发的模块, 参数提取)
            (r'搜索?|查找|帮我找', 'search', ['github-trending', 'browser-auto'], self._extract_search),
            (r'监控|追踪|关注', 'monitor', ['system-monitor', 'stock-api'], self._extract_target),
            (r'自动|自动化|定时', 'automation', ['cron-scheduler', 'workflow-manager'], self._extract_task),
            (r'分析?|统计|汇总', 'analysis', ['data-analysis', 'ai-summary'], self._extract_data),
            (r'生成|创建|制作', 'generate', ['doc-automation', 'pdf-report'], self._extract_content),
            (r'发送|通知|提醒', 'notify', ['feishu-notify', 'push-notify', 'email-automation'], self._extract_recipient),
            (r'翻译|转译', 'translate', ['translation-api'], self._extract_text),
            (r'录音|录制|转写', 'transcribe', ['voice-recorder', 'speech-to-text'], self._extract_audio),
            (r'思维导?|图谱|结构化', 'mindmap', ['mindmap-generator'], self._extract_topic),
            (r'周报|月报|总结', 'report', ['weekly-report', 'monthly-report'], self._extract_period),
            (r'部署|上线|发布', 'deploy', ['docker-deploy', 'gitlab-repo'], self._extract_service),
            (r'查询|获取.*数据', 'query', ['database-client', 'api-gateway'], self._extract_query),
            (r'安装|更新|升级', 'install', ['pip-manager', 'auto-update'], self._extract_package),
            (r'重置|恢复|初始化', 'reset', ['system-reset'], self._extract_target),
        ]

        best_match = None
        best_score = 0

        for pattern, intent, modules, param_extractor in intent_rules:
            if re.search(pattern, user_input, re.IGNORECASE):
                # 计算匹配分数
                score = len(re.findall(pattern, user_input, re.IGNORECASE))
                # 优先匹配更长的匹配
                score += len(pattern) * 0.1

                if score > best_score:
                    best_score = score
                    params = param_extractor(user_input)
                    best_match = {
                        "intent": intent,
                        "modules": modules,
                        "params": params,
                        "confidence": min(score / 2, 1.0)
                    }

        # 如果没有匹配到，使用通用理解
        if not best_match:
            best_match = {
                "intent": "general",
                "modules": ["ai-assistant"],
                "params": {"query": user_input},
                "confidence": 0.5
            }

        # 生成执行计划
        plan = self._generate_plan(best_match)

        return {
            "user_input": user_input,
            **best_match,
            "plan": plan,
            "timestamp": datetime.now().isoformat()
        }

    def _extract_search(self, text: str) -> Dict:
        """提取搜索关键词"""
        # 移除搜索相关的词，保留核心搜索内容
        clean = re.sub(r'搜索?|查找|帮我找', '', text, flags=re.IGNORECASE).strip()
        return {"keyword": clean, "type": "general"}

    def _extract_target(self, text: str) -> Dict:
        """提取监控/操作目标"""
        return {"target": text}

    def _extract_task(self, text: str) -> Dict:
        """提取任务内容"""
        return {"task": text}

    def _extract_data(self, text: str) -> Dict:
        """提取数据分析需求"""
        return {"data_request": text}

    def _extract_content(self, text: str) -> Dict:
        """提取内容生成需求"""
        return {"content": text}

    def _extract_recipient(self, text: str) -> Dict:
        """提取通知对象"""
        channels = []
        if '微信' in text: channels.append('wechat')
        if '钉钉' in text: channels.append('dingtalk')
        if '飞书' in text: channels.append('feishu')
        if '邮件' in text: channels.append('email')
        if not channels: channels.append('feishu')  # 默认飞书
        return {"channels": channels, "message": text}

    def _extract_text(self, text: str) -> Dict:
        """提取翻译文本"""
        lang_match = re.search(r'翻成?(\w+)语', text)
        target_lang = lang_match.group(1) if lang_match else '英文'
        return {"text": text, "target_lang": target_lang}

    def _extract_audio(self, text: str) -> Dict:
        """提取音频处理需求"""
        return {"audio_task": text}

    def _extract_topic(self, text: str) -> Dict:
        """提取思维导图主题"""
        return {"topic": text}

    def _extract_period(self, text: str) -> Dict:
        """提取报告周期"""
        period = 'week' if '周' in text else 'month'
        return {"period": period}

    def _extract_service(self, text: str) -> Dict:
        """提取部署服务"""
        return {"service": text}

    def _extract_query(self, text: str) -> Dict:
        """提取查询请求"""
        return {"query": text}

    def _extract_package(self, text: str) -> Dict:
        """提取包名"""
        pkgs = re.findall(r'[\w\-]+', text)
        return {"packages": [p for p in pkgs if len(p) > 2]}

    def _generate_plan(self, intent_data: Dict) -> List[str]:
        """生成执行计划"""
        intent = intent_data["intent"]
        modules = intent_data["modules"]

        plans = {
            "search": [
                "1. 调用 GitHub Trending 模块获取最新项目",
                "2. 使用 AI 分析筛选优质项目",
                "3. 返回项目详情和 Star 数"
            ],
            "monitor": [
                "1. 注册监控任务到调度器",
                "2. 设置监控频率和告警规则",
                "3. 启动守护进程持续监控"
            ],
            "automation": [
                "1. 解析任务步骤",
                "2. 创建自动化工作流",
                "3. 设置定时触发器",
                "4. 启动执行"
            ],
            "analysis": [
                "1. 收集相关数据源",
                "2. 执行数据分析",
                "3. 生成可视化图表",
                "4. 输出分析结论"
            ],
            "generate": [
                "1. 收集生成所需信息",
                "2. 调用 AI 生成内容",
                "3. 格式化输出"
            ],
            "notify": [
                "1. 构建通知消息",
                "2. 调用多渠道推送",
                "3. 确认送达状态"
            ],
            "transcribe": [
                "1. 启动录音设备",
                "2. 实时语音转文字",
                "3. 生成转录文本"
            ],
            "mindmap": [
                "1. 分析主题结构",
                "2. 生成思维导图 JSON",
                "3. 渲染可视化图形"
            ],
            "report": [
                "1. 收集周期内数据",
                "2. 生成 AI 摘要",
                "3. 生成图表",
                "4. 格式化报告"
            ],
            "deploy": [
                "1. 构建 Docker 镜像",
                "2. 配置部署环境",
                "3. 执行部署",
                "4. 验证服务状态"
            ],
            "general": [
                "1. 理解用户意图",
                "2. 准备相关信息",
                "3. 执行请求"
            ]
        }

        return plans.get(intent, plans["general"])

    async def execute(self, plan: Dict) -> Dict[str, Any]:
        """
        执行计划：调用各个模块
        """
        results = []
        modules = plan.get("modules", [])

        for module_id in modules:
            module = self.mm.get_module(module_id)
            if module:
                try:
                    result = await module.execute(plan.get("params", {}))
                    results.append({
                        "module": module_id,
                        "status": "success",
                        "result": result
                    })
                except Exception as e:
                    results.append({
                        "module": module_id,
                        "status": "error",
                        "error": str(e)
                    })
            else:
                results.append({
                    "module": module_id,
                    "status": "not_found",
                    "error": f"模块 {module_id} 不存在"
                })

        # 记录执行历史
        self.history.append({
            "plan": plan,
            "results": results,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "plan": plan,
            "results": results,
            "summary": self._summarize_results(results)
        }

    def _summarize_results(self, results: List[Dict]) -> str:
        """汇总执行结果"""
        success = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "error")

        if success == len(results):
            return f"✅ 全部执行成功 ({success} 个模块)"
        elif success > 0:
            return f"⚠️ 部分成功 ({success} 成功, {failed} 失败)"
        else:
            return f"❌ 全部执行失败"

    async def chat(self, user_input: str) -> str:
        """
        对话式执行：思考 → 执行 → 返回结果
        """
        # 思考
        plan = await self.think(user_input)

        # 显示计划
        plan_text = "\n".join(plan["plan"])
        print(f"\n🧠 系统大脑思考中...")
        print(f"   意图: {plan['intent']}")
        print(f"   模块: {', '.join(plan['modules'])}")
        print(f"   置信度: {plan['confidence']:.0%}")
        print(f"\n📋 执行计划:")
        print(f"   {plan_text}")

        # 执行
        print(f"\n⚙️ 开始执行...")
        result = await self.execute(plan)

        return result

# 导出
__all__ = ["EvoBrain"]
