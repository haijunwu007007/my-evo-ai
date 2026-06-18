"""
AUTO-EVO-AI V0.1 — Pydantic 请求模型
从 infra.py 拆分出，减少核心基础设施体积
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class ModuleCallRequest(BaseModel):
    module: str
    method: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}


class ExecuteRequest(BaseModel):
    task: str
    context: dict[str, Any] = {}


class PlannerChatRequest(BaseModel):
    message: str
    context: dict[str, Any] | None = None


class PlannerTaskRequest(BaseModel):
    task: str
    params: dict[str, Any] | None = None


class EmailConfigRequest(BaseModel):
    host: str = ""
    port: int = 465
    user: str = ""
    password: str = ""
    ssl: bool = True
    from_name: str = ""


class NotificationRequest(BaseModel):
    channel: str = ""
    to: str = ""
    subject: str = ""
    content: str = ""
    msg_type: str = "text"
    secret: str = ""
    html: str = ""


class LLMChatRequest(BaseModel):
    prompt: str = ""
    messages: list[dict] = []
    model: str = ""
    session_id: str = ""
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 0
    stream: bool = False
    use_cache: bool = True


class LLMProviderRequest(BaseModel):
    name: str = ""
    provider_type: str = "openai_compatible"
    base_url: str = ""
    api_key: str = ""
    models: list[str] = []
    priority: int = 10


class DocReportRequest(BaseModel):
    title: str = "报告"
    sections: list[dict] = []
    format: str = "markdown"
    metadata: dict = None


class DocPresentationRequest(BaseModel):
    title: str = "演示文稿"
    slides: list[dict] = []
