"""
AUTO-EVO-AI V0.1 — AI Code Review + Diff API 路由
提供：代码审查 / diff 对比 / commit 日志 / 审查历史
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from modules.code_review import get_reviewer

router = APIRouter()

class ReviewRequest(BaseModel):
    target: str = "working"  # working / commit / branch
    hash: str = ""
    base: str = "master"
    head: str = ""
    staged: bool = False
    compare: str = ""


@router.post("/api/v1/code-review/run")
async def run_review(req: ReviewRequest):
    """运行代码审查"""
    reviewer = get_reviewer()
    try:
        if req.target == "commit":
            r = reviewer.review_commit(req.hash, req.compare)
        elif req.target == "branch":
            r = reviewer.review_branch(req.base, req.head)
        else:
            r = reviewer.review_working_tree(req.staged)
        return {"success": True, "review": vars(r) if hasattr(r, '__dict__') else r}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/code-review/history")
async def review_history(limit: int = 20):
    """获取审查历史"""
    reviewer = get_reviewer()
    return {"success": True, "reviews": reviewer.get_history(limit)}


@router.get("/api/v1/code-review/commits")
async def commit_log(limit: int = 20):
    """获取 commit 日志"""
    reviewer = get_reviewer()
    return {"success": True, "commits": reviewer.get_commit_log(limit)}


@router.get("/api/v1/code-review/diff")
async def get_diff(
    target: str = Query("", description="commit hash or empty for working tree"),
    compare: str = Query("", description="base commit for range"),
):
    """获取 diff 文本"""
    reviewer = get_reviewer()
    text = reviewer.get_diff(target, compare)
    return {"success": True, "diff": text}


@router.get("/api/v1/code-review/status")
async def review_status():
    """审查系统状态"""
    return {"success": True, "status": "ready", "engine": "AI Code Review v1"}


# ===== Diff View API =====

@router.get("/api/v1/diff/compare")
async def diff_compare(
    base: str = Query("HEAD~1", description="基准版本"),
    head: str = Query("HEAD", description="目标版本"),
    file: str = Query("", description="指定文件"),
):
    """对比两个版本的差异"""
    reviewer = get_reviewer()
    cmd = ["diff", f"{base}..{head}"]
    if file:
        cmd.append("--")
        cmd.append(file)
    import subprocess
    from pathlib import Path
    repo = str(Path(__file__).parent.parent)
    try:
        r = subprocess.run(["git"] + cmd, capture_output=True, text=True, timeout=30, cwd=repo)
        return {"success": True, "diff": r.stdout, "files_changed": len([l for l in r.stdout.split("\n") if l.startswith("diff --git")])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/diff/file")
async def diff_file(
    path: str = Query(..., description="文件路径"),
    base: str = Query("", description="基准 commit"),
    head: str = Query("", description="目标 commit"),
):
    """获取单个文件在不同版本的差异"""
    reviewer = get_reviewer()
    repo = str(Path(__file__).parent.parent)
    import subprocess
    from pathlib import Path

    try:
        # 尝试获取该文件的 diff
        if base and head:
            cmd = ["diff", f"{base}..{head}", "--", path]
        elif base:
            cmd = ["show", f"{base}:{path}"]
        else:
            # 未提交的变更
            cmd = ["diff", "--", path]

        r = subprocess.run(["git"] + cmd, capture_output=True, text=True, timeout=15, cwd=repo)

        # 同时获取目标版本的文件内容
        content = ""
        try:
            if head:
                cr = subprocess.run(["git", "show", f"{head}:{path}"], capture_output=True, text=True, timeout=10, cwd=repo)
                content = cr.stdout
        except Exception:
            content = ""

        return {
            "success": True,
            "diff": r.stdout,
            "file": path,
            "content": content,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "diff": ""}
