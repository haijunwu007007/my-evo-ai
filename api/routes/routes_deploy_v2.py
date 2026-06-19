# -*- coding: utf-8 -*-
"""一键部署任意开源项目 — 克隆→分析→构建→部署"""
from fastapi import APIRouter, HTTPException
import os, json, time, asyncio, threading, hashlib

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
router = APIRouter(prefix="/api/v1", tags=["deploy"])

_DEPLOYS = {}  # {id: {status, url, info, progress, logs}}

def _deploy_worker(deploy_id: str, repo_url: str, branch: str):
    """后台部署线程"""
    d = _DEPLOYS[deploy_id]
    try:
        import sys
        sys.path.insert(0, BASE)
        from modules.repo_analyzer import analyze, clone, build, gen_dockerfile

        d["progress"] = "正在克隆仓库..."
        path, err = clone(repo_url, branch)
        if err: d.update({"status": "failed", "error": err, "progress": "克隆失败"}); return

        d["progress"] = "正在分析项目..."
        info = analyze(path)
        d["info"] = info
        d["type"] = info["type"]

        d["progress"] = "正在构建项目..."
        ok, logs = build(path, info)
        d["logs"] = logs
        if not ok: d.update({"status": "warning", "progress": "构建有警告"})

        # 生成Dockerfile
        df = gen_dockerfile(info)
        os.makedirs(os.path.join(BASE, "data", "deploy", deploy_id), exist_ok=True)
        with open(os.path.join(BASE, "data", "deploy", deploy_id, "Dockerfile"), "w") as f:
            f.write(df)
        with open(os.path.join(BASE, "data", "deploy", deploy_id, "info.json"), "w") as f:
            json.dump(info, f, ensure_ascii=False, default=str)

        d["dockerfile"] = df
        d["status"] = "ready"
        d["progress"] = "部署完成"
        # cleanup
        import shutil
        try: shutil.rmtree(path, ignore_errors=True)
        except: pass
    except Exception as e:
        d.update({"status": "failed", "error": str(e)[:500], "progress": "部署异常"})

@router.post("/deploy/start")
async def deploy_start(data: dict):
    """开始部署一个GitHub项目"""
    url = (data.get("url") or "").strip()
    branch = (data.get("branch") or "").strip()
    if not url or ("github.com" not in url and "gitlab" not in url):
        return {"success": False, "error": "请输入有效的Git仓库URL"}
    deploy_id = hashlib.md5((url + str(time.time())).encode()).hexdigest()[:12]
    _DEPLOYS[deploy_id] = {"id": deploy_id, "url": url, "status": "building", "progress": "排队中...", "info": None, "logs": "", "dockerfile": "", "type": "", "error": ""}
    threading.Thread(target=_deploy_worker, args=(deploy_id, url, branch), daemon=True).start()
    return {"success": True, "id": deploy_id}

@router.get("/deploy/status/{deploy_id}")
async def deploy_status(deploy_id: str):
    """查询部署状态"""
    d = _DEPLOYS.get(deploy_id)
    if not d: return {"success": False, "error": "未找到部署记录"}
    return {"success": True, **d}

@router.get("/deploy/list")
async def deploy_list():
    """列出所有部署"""
    return {"success": True, "deploys": sorted(_DEPLOYS.values(), key=lambda x: -len(x.get("status",""))), "total": len(_DEPLOYS)}
