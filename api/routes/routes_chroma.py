"""AUTO-EVO-AI V0.1 — ChromaDB 向量数据库管理路由"""
from fastapi import APIRouter
router = APIRouter()
B = "/api/v1/tools/chroma"

import os, json as _json
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules", ".chroma_data")

def _get_chroma():
    try:
        import chromadb
        return chromadb.PersistentClient(path=CHROMA_DIR)
    except Exception:
        return None

@router.get(B)
async def chroma_status():
    c = _get_chroma()
    if not c:
        return {"success": True, "available": False, "error": "chromadb not installed"}
    try:
        cols = c.list_collections()
        return {"success": True, "available": True, "collections": [col.name for col in cols], "count": len(cols)}
    except Exception as e:
        return {"success": True, "available": True, "collections": [], "count": 0, "note": str(e)}

@router.get(B + "/collections")
async def chroma_collections():
    c = _get_chroma()
    if not c:
        return {"success": False, "collections": []}
    try:
        cols = c.list_collections()
        result = []
        for col in cols:
            result.append({"name": col.name, "count": col.count(), "metadata": col.metadata})
        return {"success": True, "collections": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get(B + "/query")
async def chroma_query(collection: str = "module_semantic_index", q: str = "", top_k: int = 5):
    c = _get_chroma()
    if not c:
        return {"success": False, "error": "chromadb not installed"}
    try:
        col = c.get_collection(collection)
        if not q:
            all_data = col.get(limit=top_k)
            return {"success": True, "results": [{"id": i, "doc": d[:200] if d else ""} for i, d in zip(all_data["ids"], all_data["documents"])]}
        results = col.query(query_texts=[q], n_results=top_k)
        if results and results["ids"] and results["ids"][0]:
            return {"success": True, "results": [{"id": i, "score": round(s, 4), "doc": d[:200] if d else ""} for i, s, d in zip(results["ids"][0], results["distances"][0], results["documents"][0])]}
        return {"success": True, "results": []}
    except Exception as e:
        return {"success": False, "error": str(e)}
