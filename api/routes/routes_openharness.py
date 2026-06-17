"""OpenHarness Integration Routes"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["openharness"])

class MCPRegister(BaseModel):
    name: str
    url: str

class ChannelSend(BaseModel):
    platform: str
    channel: str = "general"
    message: str

class BridgeConfig(BaseModel):
    provider: str
    endpoint: str
    key: str = ""

class SkillData(BaseModel):
    name: str
    content: str

class MemoryData(BaseModel):
    key: str
    content: str
    ttl: int = 2592000

@router.get("/api/openharness/mcp/list")
async def mcp_list():
    from api.openharness_integration import mcp_list as _list
    return _list()

@router.post("/api/openharness/mcp/register")
async def mcp_register(data: MCPRegister):
    from api.openharness_integration import mcp_register as _reg
    return _reg(data.name, data.url)

@router.post("/api/openharness/channel/send")
async def channel_send(data: ChannelSend):
    from api.openharness_integration import channel_send as _send
    return _send(data.platform, data.channel, data.message)

@router.post("/api/openharness/bridge/configure")
async def bridge_configure(data: BridgeConfig):
    from api.openharness_integration import bridge_configure as _cfg
    return _cfg(data.provider, data.endpoint, data.key)

@router.get("/api/openharness/bridge/list")
async def bridge_list():
    from api.openharness_integration import bridge_list as _list
    return _list()

@router.get("/api/openharness/skills/list")
async def skills_list():
    from api.openharness_integration import skills_list as _list
    return _list()

@router.post("/api/openharness/skills/save")
async def skills_save(data: SkillData):
    from api.openharness_integration import skills_save as _save
    return _save(data.name, data.content)

@router.post("/api/openharness/memory/save")
async def memory_save(data: MemoryData):
    from api.openharness_integration import memory_save as _save
    return _save(data.key, data.content, data.ttl)

@router.get("/api/openharness/memory/search/{query}")
async def memory_search(query: str):
    from api.openharness_integration import memory_search as _search
    return _search(query)

@router.post("/api/openharness/memory/compress")
async def memory_compress():
    from api.openharness_integration import memory_compress as _cmp
    return _cmp()

@router.get("/api/openharness/stats")
async def openharness_stats():
    from api.openharness_integration import mcp_list, bridge_list, skills_list
    return {
        "mcp_servers": len(mcp_list().get("servers", [])),
        "bridges": len(bridge_list().get("bridges", [])),
        "skills": len(skills_list().get("skills", [])),
    }
