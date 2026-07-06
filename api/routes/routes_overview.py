# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 — 系统能力总览（新用户引导）

提供 /api/v1/overview 端点，返回系统全部能力清单，
帮助新用户快速了解 AUTO-EVO-AI 平台的功能全貌。
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["overview"])

_CAPABILITIES = [
    {"icon":"💬","name":"智能对话","desc":"聊天、搜索、翻译、画图、写代码","keywords":"你好,搜索,画,翻译,写代码","tag":"/"},
    {"icon":"🧠","name":"专家系统","desc":"266位专家提供专业服务","keywords":"找专家,我想找","tag":"experts"},
    {"icon":"📚","name":"学习中心","desc":"录屏演示、自动生成技能","keywords":"学,教,培训","tag":"learn"},
    {"icon":"🔄","name":"工作流编排","desc":"拖拽式自动化工作流","keywords":"工作流,编排","tag":"canvas"},
    {"icon":"⭕","name":"循环任务","desc":"定时自动化任务","keywords":"循环,定时,每天","tag":"loop"},
    {"icon":"🛠️","name":"技能 & 扩展","desc":"160+内置工具技能","keywords":"技能,工具","tag":"skills"},
    {"icon":"🤖","name":"Agent集群","desc":"多Agent协作执行","keywords":"agent,智能体","tag":"agents"},
    {"icon":"🏛️","name":"集团OS","desc":"企业级管理系统","keywords":"企业,集团","tag":"enterprise"},
    {"icon":"📊","name":"监控面板","desc":"系统健康、性能监控","keywords":"监控,状态","tag":"dashboard"},
    {"icon":"📦","name":"应用市场","desc":"已生成的应用","keywords":"应用,apps","tag":"apps"},
]

@router.get("/overview")
async def get_overview():
    """返回系统能力总览，用于新用户引导界面"""
    return {
        "success": True,
        "system": "AUTO-EVO-AI V0.1",
        "capabilities": _CAPABILITIES,
    }
