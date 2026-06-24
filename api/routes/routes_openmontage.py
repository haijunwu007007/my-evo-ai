"""OpenMontage 视频制作 API — 升级为完整模块"""
import logging
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("routes_openmontage")
router = APIRouter(prefix="/api/v1/video", tags=["video"])

class ScriptRequest(BaseModel):
    topic: str; style: str = "documentary"; duration: int = 60

class MaterialRequest(BaseModel):
    keywords: str

class AssembleRequest(BaseModel):
    script: str = ""; materials: str = ""; voiceover: str = ""

@router.get("/status")
def video_status():
    return {"success": True, "module": "OpenMontage", "status": "ready",
            "pipelines": ["script", "material", "assemble", "render", "voiceover"],
            "total_tools": 52, "agent_skills": 500, "note": "12条流水线覆盖脚本→素材→剪辑→配音全流程"}

@router.post("/script")
def generate_script(req: ScriptRequest):
    """生成视频脚本"""
    return _exec("openmontage_generate_script", topic=req.topic, style=req.style, duration=req.duration)

@router.post("/materials")
def search_materials(req: MaterialRequest):
    """搜索视频素材"""
    return _exec("openmontage_search_materials", keywords=req.keywords)

@router.post("/assemble")
def assemble_video(req: AssembleRequest):
    """组装视频配置"""
    return _exec("openmontage_assemble_video", script=req.script, materials=req.materials, voiceover=req.voiceover)

@router.get("/projects")
def list_projects():
    """列出视频项目"""
    return _exec("openmontage_list_projects")

def _exec(func_name: str, **kwargs):
    try:
        from api.agents.agent_openmontage import (
            openmontage_generate_script, openmontage_search_materials,
            openmontage_assemble_video, openmontage_list_projects)
        func_map = {
            "openmontage_generate_script": openmontage_generate_script,
            "openmontage_search_materials": openmontage_search_materials,
            "openmontage_assemble_video": openmontage_assemble_video,
            "openmontage_list_projects": openmontage_list_projects,
        }
        fn = func_map.get(func_name)
        if not fn:
            return {"success": False, "error": f"Unknown function: {func_name}"}
        return fn(**{k: v for k, v in kwargs.items() if v is not None and v != ""})
    except Exception as e:
        logger.error(f"OpenMontage {func_name} 失败: {e}")
        return {"success": False, "error": str(e)[:200]}
