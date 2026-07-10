"""
AUTO-EVO-AI V0.1 — 代码差异对比 API (增强版)
基于 diff_viewer 模块的文本对比 + AI解释
"""
import logging
logger = logging.getLogger("evo.routes_diff")

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from modules.diff_viewer import compare_text, explain_diff, batch_compare

router = APIRouter()


class CompareRequest(BaseModel):
    old_text: str = ""
    new_text: str = ""
    file_path: str = "unknown"


class BatchCompareRequest(BaseModel):
    old_files: dict[str, str] = {}
    new_files: dict[str, str] = {}


@router.post("/api/v1/diff/viewer/compare")
async def diff_compare(req: CompareRequest):
    try:
        result = compare_text(req.old_text, req.new_text, req.file_path)
        return {"success": True, "diff": {
            "file": result.file_path,
            "language": result.language,
            "additions": result.additions,
            "deletions": result.deletions,
            "chunks": result.chunks,
        }}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/api/v1/diff/viewer/batch")
async def diff_batch(req: BatchCompareRequest):
    try:
        result = batch_compare(req.old_files, req.new_files)
        return {"success": True, "result": {
            "files": [{"file": f.file_path, "additions": f.additions, "deletions": f.deletions, "chunks": f.chunks} for f in result.files],
            "total_additions": result.total_additions,
            "total_deletions": result.total_deletions,
            "total_files": result.total_files,
            "summary": result.summary,
        }}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/api/v1/diff/viewer/explain")
async def diff_explain(req: CompareRequest):
    try:
        diff_file = compare_text(req.old_text, req.new_text, req.file_path)
        explanation = explain_diff(diff_file)
        return {"success": True, "explanation": explanation}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
