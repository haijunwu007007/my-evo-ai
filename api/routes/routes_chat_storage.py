"""对话持久化 + 文件上传路由"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json, os, time, shutil

from core.logging_config import get_logger
logger = get_logger("evo.api.chat_storage")

router = APIRouter(tags=["chat"])

BASE = Path(__file__).resolve().parent.parent.parent
CHAT_DIR = BASE / "_data" / "chat_history"
UPLOAD_DIR = BASE / "uploads"

CHAT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ChatSaveReq(BaseModel):
    username: str
    role: str       # "user" | "bot"
    content: str


class ChatLoadReq(BaseModel):
    username: str
    limit: Optional[int] = 100


@router.post("/api/v1/chat/save")
async def chat_save(req: ChatSaveReq):
    """保存单条聊天记录"""
    user_file = CHAT_DIR / f"{req.username}.jsonl"
    entry = {
        "role": req.role,
        "content": req.content,
        "time": time.time()
    }
    try:
        with open(user_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return {"success": True}
    except Exception as e:
        logger.error("保存聊天记录失败: %s", e)
        return {"success": False, "detail": str(e)}


@router.get("/api/v1/chat/load")
async def chat_load(username: str, limit: int = 100):
    """加载用户聊天记录（最近的 limit 条）"""
    user_file = CHAT_DIR / f"{username}.jsonl"
    if not user_file.exists():
        return {"success": True, "messages": []}

    try:
        messages = []
        with open(user_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
        return {"success": True, "messages": messages[-limit:]}
    except Exception as e:
        logger.error("加载聊天记录失败: %s", e)
        return {"success": True, "messages": []}


@router.delete("/api/v1/chat/clear")
async def chat_clear(username: str):
    """清空用户聊天记录"""
    user_file = CHAT_DIR / f"{username}.jsonl"
    if user_file.exists():
        user_file.unlink()
    return {"success": True}


@router.get("/api/v1/chat/users")
async def chat_users():
    """列出所有有过聊天记录的用户"""
    users = []
    if CHAT_DIR.exists():
        for f in CHAT_DIR.iterdir():
            if f.suffix == ".jsonl":
                users.append(f.stem)
    return {"success": True, "users": users}


@router.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传单个文件"""
    safe_name = f"{int(time.time())}_{file.filename}"
    dest = UPLOAD_DIR / safe_name

    try:
        content = await file.read()
        dest.write_bytes(content)
        size = len(content)
        logger.info("文件上传: %s (%d bytes)", safe_name, size)
        return {
            "success": True,
            "filename": safe_name,
            "original_name": file.filename,
            "size": size,
            "url": f"/uploads/{safe_name}"
        }
    except Exception as e:
        logger.error("文件上传失败: %s", e)
        return {"success": False, "detail": str(e)}


@router.post("/api/v1/upload/multi")
async def upload_files(files: list[UploadFile] = File(...)):
    """上传多个文件"""
    results = []
    for f in files:
        safe_name = f"{int(time.time())}_{f.filename}"
        dest = UPLOAD_DIR / safe_name
        try:
            content = await f.read()
            dest.write_bytes(content)
            results.append({
                "success": True,
                "filename": safe_name,
                "original_name": f.filename,
                "size": len(content),
                "url": f"/uploads/{safe_name}"
            })
        except Exception as e:
            results.append({
                "success": False,
                "filename": f.filename,
                "detail": str(e)
            })
    return {"success": True, "files": results}


@router.get("/api/v1/uploads")
async def list_uploads():
    """列出所有上传文件"""
    files = []
    if UPLOAD_DIR.exists():
        for f in UPLOAD_DIR.iterdir():
            if f.is_file():
                files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime
                })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"success": True, "files": files}
