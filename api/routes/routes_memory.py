# -*- coding: utf-8 -*-
from fastapi import APIRouter
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))
from modules.memory_tree import MemoryTree

router = APIRouter(tags=["memory"])
_tree = None
def _get():
    global _tree
    if _tree is None: _tree = MemoryTree()
    return _tree

@router.get("/api/v1/memory/status")
async def get_status():
    return {"status": "ok", "nodes": 0, "feature": "memory-tree"}

@router.post("/api/v1/memory/add")
async def add_node(node_id: str, title: str, content: str = "", parent: str = "", tags: str = ""):
    _get().add_node(node_id, title, content, "note", parent, tags)
    return {"ok": True}

@router.get("/api/v1/memory/search")
async def search(query: str):
    return {"results": _get().search(query)}

@router.get("/api/v1/memory/tree")
async def get_tree():
    return {"nodes": _get().get_tree()}
