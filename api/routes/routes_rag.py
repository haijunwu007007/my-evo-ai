"""
AUTO-EVO-AI V0.1 — 端到端 RAG 知识库
借鉴 Dify "Knowledge" 功能：上传→分块→向量化→检索→Rerank→LLM 回复
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import os, json, time, hashlib, re, sqlite3, asyncio, httpx
from pathlib import Path

logger = get_logger("evo.api.rag")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAG_DIR = BASE_DIR / "rag_kb"
RAG_DIR.mkdir(exist_ok=True)
(RAG_DIR / "documents").mkdir(exist_ok=True)
(RAG_DIR / "chunks").mkdir(exist_ok=True)
(RAG_DIR / "vectors").mkdir(exist_ok=True)

# ─── SQLite metadata ──────────────────────────
_DB = BASE_DIR / "core" / "adaptive_engine.db"

def _init_db():
    conn = sqlite3.connect(str(_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS rag_knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        description TEXT,
        doc_count INTEGER DEFAULT 0,
        chunk_count INTEGER DEFAULT 0,
        created_at REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS rag_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kb_name TEXT,
        filename TEXT,
        title TEXT,
        chunk_count INTEGER DEFAULT 0,
        file_path TEXT,
        created_at REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS rag_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER,
        kb_name TEXT,
        chunk_index INTEGER,
        content TEXT,
        embedding BLOB,
        created_at REAL
    )""")
    conn.commit(); conn.close()

_init_db()

# ─── 种子文档（系统知识库自动填充）─────────────────────
_SEED_DOCS = {
    "系统帮助": [
        "AUTO-EVO-AI V0.1 是一个 457 模块的多智能体自动化编排系统，支持聊天、仪表盘和企业管理三种入口。",
        "主要功能包括：AI 对话（支持流式输出）、模块管理（457个预置模块）、技能系统（Skills）、MCP 工具桥接、RAG 知识库、多智能体团队协作（6个默认 Agent：Planner/Coder/Reviewer/Operator/Analyst/Researcher）、工作流编排、Gateway 外部集成网关、A2A Agent 协议、MCPize 万能集成桥、REST→MCP 转换。",
        "系统默认访问地址：http://localhost:8765。聊天首页 /，仪表盘 /dashboard，企业管理后台 /app/login。默认管理员账号 admin，密码由环境变量 EVO_ADMIN_PASSWORD 设置。",
        "Skills（技能）是系统的扩展能力单元，通过 POST /api/v1/skills/register 注册，通过 GET /api/v1/skills 查询列表，通过 POST /api/v1/skills/{name}/execute 执行。内置 18 个技能包括文本/文档/代码/搜索/翻译/PPT/Excel 等。",
        "MCP（Model Context Protocol）是标准化的 AI 工具接口。系统内置 8 个 MCP 工具（chat_send/document_generate/code_generate/web_search/github_trending/math_calculate/system_status/translate_text），并支持自动发现外部 MCP 服务器。",
    ],
}
def _seed_rag():
    """如果知识库为空，自动填充种子文档"""
    conn = sqlite3.connect(str(_DB))
    try:
        cnt = conn.execute("SELECT COUNT(*) FROM rag_knowledge").fetchone()[0]
        if cnt > 0:
            return
        for kb_name, docs in _SEED_DOCS.items():
            now = time.time()
            conn.execute(
                "INSERT OR IGNORE INTO rag_knowledge (name, description, doc_count, chunk_count, created_at) VALUES (?,?,?,?,?)",
                (kb_name, f"{kb_name} 自动种子知识库", len(docs), 0, now),
            )
            for i, doc_text in enumerate(docs):
                doc_hash = hashlib.md5(doc_text.encode()).hexdigest()
                doc_path = str(RAG_DIR / "documents" / f"{kb_name}_{i}.txt")
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(doc_text)
                conn.execute(
                    "INSERT INTO rag_documents (kb_name, filename, title, chunk_count, file_path, created_at) VALUES (?,?,?,?,?,?)",
                    (kb_name, f"{kb_name}_{i}.txt", doc_text[:40], 1, doc_path, now),
                )
                # 直接作为 chunk 存储
                chunk_path = RAG_DIR / "chunks" / f"{kb_name}_{i}.json"
                chunk_data = {"content": doc_text, "kb": kb_name, "index": i}
                with open(chunk_path, "w", encoding="utf-8") as f:
                    json.dump(chunk_data, f, ensure_ascii=False)
            conn.commit()
    except Exception:
        pass
    finally:
        conn.close()
_seed_rag()

# ─── 分块策略 ─────────────────────────────
_CHUNK_STRATEGIES = {
    "fixed": {"chunk_size": 500, "overlap": 50},
    "paragraph": {"separator": "\n\n", "max_chars": 1000},
    "sentence": {"separator": "。！？\n", "max_chars": 300},
    "ai": {"model": "glm-4-flash"}  # AI 智能分块
}

def _chunk_text(text: str, strategy: str = "paragraph") -> list[str]:
    """按策略分块文本"""
    if not text.strip():
        return []
    if strategy == "fixed":
        size = _CHUNK_STRATEGIES["fixed"]["chunk_size"]
        overlap = _CHUNK_STRATEGIES["fixed"]["overlap"]
        return [text[i:i+size] for i in range(0, len(text), size - overlap)]
    elif strategy == "paragraph":
        sep = _CHUNK_STRATEGIES["paragraph"]["separator"]
        max_c = _CHUNK_STRATEGIES["paragraph"]["max_chars"]
        chunks = []
        for para in text.split(sep):
            para = para.strip()
            if not para:
                continue
            if len(para) > max_c:
                # 再按句切
                for sent in para.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n"):
                    s = sent.strip()
                    if s:
                        chunks.append(s)
            else:
                chunks.append(para)
        return chunks
    elif strategy == "sentence":
        sep = _CHUNK_STRATEGIES["sentence"]["separator"]
        max_c = _CHUNK_STRATEGIES["sentence"]["max_chars"]
        chunks = []
        buffer = ""
        for char in text:
            buffer += char
            if char in sep and len(buffer) >= max_c * 0.5:
                chunks.append(buffer.strip())
                buffer = ""
        if buffer.strip():
            chunks.append(buffer.strip())
        return chunks
    return [text]


def _compute_embedding(text: str) -> list[float]:
    """计算文本向量（简单 TF-IDF 降级 + GLM API）"""
    # 尝试智谱 embedding API
    api_key = os.environ.get("ZHIPU_API_KEY", "")
    if api_key:
        try:
            import httpx
            resp = httpx.post(
                "https://open.bigmodel.cn/api/paas/v4/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "embedding-2", "input": text[:512]},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [{}])[0].get("embedding", [])
        except Exception:
            pass
    # 降级：词袋向量
    import math
    words = re.findall(r'\w+', text.lower())
    word_set = set(words)
    # 用 hash 模拟 128 维向量
    vec = [0.0] * 128
    for w in words:
        h = hash(w) % 128
        vec[h] += 1.0 / max(len(words), 1)
    return vec


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(x*x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ============================================================
# API: 创建知识库
# ============================================================
class KBCreate(BaseModel):
    name: str
    description: str = ""

@router.post("/api/v1/rag/kb")
async def create_kb(req: KBCreate):
    conn = sqlite3.connect(str(_DB))
    try:
        conn.execute("INSERT INTO rag_knowledge (name, description, created_at) VALUES (?,?,?)",
                     (req.name, req.description, time.time()))
        conn.commit()
        (RAG_DIR / "documents" / req.name).mkdir(parents=True, exist_ok=True)
        return {"success": True, "kb": req.name, "message": f"知识库 '{req.name}' 已创建"}
    except sqlite3.IntegrityError:
        return {"success": False, "detail": f"知识库 '{req.name}' 已存在"}
    finally: conn.close()


@router.get("/api/v1/rag/kb")
async def list_kb():
    conn = sqlite3.connect(str(_DB))
    rows = conn.execute("SELECT name, description, doc_count, chunk_count, created_at FROM rag_knowledge ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"success": True, "knowledge_bases": [
        {"name": r[0], "description": r[1], "doc_count": r[2], "chunk_count": r[3], "created_at": r[4]} for r in rows
    ]}


# ============================================================
# API: 上传文档
# ============================================================
@router.post("/api/v1/rag/upload")
async def upload_document(kb: str = Form(...), file: UploadFile = File(...), chunk_strategy: str = Form("paragraph")):
    """上传文档到知识库"""
    content_bytes = await file.read()
    try:
        text = content_bytes.decode("utf-8", errors="replace")
    except:
        text = f"[二进制文件] {file.filename} 内容无法编码为文本，跳过分块。"
    
    conn = sqlite3.connect(str(_DB))
    
    # 确认知识库存在
    kb_row = conn.execute("SELECT id FROM rag_knowledge WHERE name=?", (kb,)).fetchone()
    if not kb_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"知识库 '{kb}' 不存在")
    
    # 写入文件
    doc_dir = RAG_DIR / "documents" / kb
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / file.filename
    file_path.write_bytes(content_bytes)
    
    # 记录文档
    cursor = conn.execute(
        "INSERT INTO rag_documents (kb_name, filename, title, file_path, created_at) VALUES (?,?,?,?,?)",
        (kb, file.filename, file.filename, str(file_path), time.time())
    )
    doc_id = cursor.lastrowid
    
    # 分块
    chunks = _chunk_text(text, chunk_strategy)
    chunk_ids = []
    for i, chunk_text in enumerate(chunks):
        emb = _compute_embedding(chunk_text)
        emb_blob = json.dumps(emb).encode() if emb else b""
        c = conn.execute(
            "INSERT INTO rag_chunks (doc_id, kb_name, chunk_index, content, embedding, created_at) VALUES (?,?,?,?,?,?)",
            (doc_id, kb, i, chunk_text[:1000], emb_blob, time.time())
        )
        chunk_ids.append(c.lastrowid)
    
    # 更新计数
    conn.execute("UPDATE rag_knowledge SET doc_count = doc_count + 1, chunk_count = chunk_count + ? WHERE name=?",
                 (len(chunks), kb))
    conn.execute("UPDATE rag_documents SET chunk_count = ? WHERE id=?", (len(chunks), doc_id))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "document": file.filename,
        "kb": kb,
        "chunks": len(chunks),
        "chunk_strategy": chunk_strategy,
        "message": f"文档 {file.filename} 已上传并分块为 {len(chunks)} 个片段"
    }


@router.get("/api/v1/rag/documents")
async def list_documents(kb: str = ""):
    conn = sqlite3.connect(str(_DB))
    if kb:
        rows = conn.execute("SELECT id, filename, title, chunk_count, created_at FROM rag_documents WHERE kb_name=? ORDER BY created_at DESC", (kb,)).fetchall()
    else:
        rows = conn.execute("SELECT id, filename, title, chunk_count, created_at FROM rag_documents ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"success": True, "documents": [
        {"id": r[0], "filename": r[1], "title": r[2], "chunk_count": r[3], "created_at": r[4]} for r in rows
    ]}


# ============================================================
# API: 查询知识库（RAG 核心）
# ============================================================
class RAGQuery(BaseModel):
    query: str
    kb: str = ""
    top_k: int = 5
    use_rerank: bool = True
    use_llm: bool = True

@router.post("/api/v1/rag/query")
async def rag_query(req: RAGQuery):
    """RAG 查询：向量检索 → Rerank → LLM 回复"""
    start = time.time()
    
    # 1. 计算查询向量
    query_emb = _compute_embedding(req.query)
    
    # 2. 向量检索
    conn = sqlite3.connect(str(_DB))
    if req.kb:
        rows = conn.execute("SELECT id, doc_id, chunk_index, content, embedding FROM rag_chunks WHERE kb_name=?", (req.kb,)).fetchall()
    else:
        rows = conn.execute("SELECT id, doc_id, chunk_index, content, embedding FROM rag_chunks").fetchall()
    conn.close()
    
    if not rows:
        return {"success": True, "query": req.query, "results": [], "total": 0, "mode": "no_chunks",
                "message": "知识库暂无内容，请先上传文档。"}
    
    # 计算相似度
    scored = []
    for r in rows:
        chunk_id, doc_id, idx, content, emb_blob = r
        if emb_blob:
            try:
                emb = json.loads(emb_blob.decode())
                score = _cosine_similarity(query_emb, emb)
                scored.append((score, chunk_id, doc_id, idx, content))
            except:
                scored.append((0.1, chunk_id, doc_id, idx, content))
        else:
            scored.append((0.1, chunk_id, doc_id, idx, content))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:req.top_k * 3]  # 取更多让 Rerank 排序
    
    # 3. Rerank（可选）
    if req.use_rerank and top:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                rerank_payload = {
                    "query": req.query,
                    "candidates": [{"title": f"chunk_{r[3]}", "content": r[4][:500]} for r in top[:20]]
                }
                resp = await c.post("http://127.0.0.1:8765/api/v1/rerank", json=rerank_payload)
                if resp.status_code == 200:
                    reranked = resp.json().get("results", [])
                    # 按 Rerank 分数排序
                    top = [(r.get("score", 0), top[i][1], top[i][2], top[i][3], top[i][4])
                           for i, r in enumerate(reranked) if i < len(top)]
                    top.sort(key=lambda x: x[0], reverse=True)
        except Exception:
            pass
    
    results = [{
        "score": round(r[0], 4),
        "content": r[4][:500],
        "doc_id": r[2],
        "chunk_index": r[3]
    } for r in top[:req.top_k]]
    
    elapsed = round(time.time() - start, 3)
    
    # 4. LLM 回复（可选）
    llm_answer = ""
    if req.use_llm and results:
        context = "\n\n".join([f"[片段 {r['chunk_index']}]: {r['content'][:300]}" for r in results[:3]])
        try:
            from api.routes.routes_smart_chat import _call_llm
            llm_answer = await _call_llm(f"基于以下知识回答问题。\n\n知识:\n{context}\n\n问题: {req.query}\n\n请用中文回答:", provider="glm")
        except:
            llm_answer = "(LLM 不可用，仅返回检索结果)"
    
    return {
        "success": True,
        "query": req.query,
        "kb": req.kb or "all",
        "total_chunks": len(rows),
        "results": results,
        "llm_answer": llm_answer,
        "elapsed_sec": elapsed
    }


# ============================================================
# API: 简单的 RAG 聊天（端到端）
# ============================================================
@router.post("/api/v1/rag/analyze")
async def rag_analyze(payload: dict):
    """简版 RAG 分析——同 chat 但返回更简"""
    query = payload.get("query", "")
    if not query:
        return {"success": False, "detail": "请提供问题"}
    import httpx
    async with httpx.AsyncClient(timeout=60) as c:
        resp = await c.post("http://127.0.0.1:8765/api/v1/rag/query",
                           json={"query": query, "top_k": payload.get("top_k", 3), "use_llm": True})
        data = resp.json()
    if data.get("success") and data.get("llm_answer"):
        return {"success": True, "answer": data["llm_answer"], "mode": "rag"}
    return {"success": False, "detail": "RAG 分析失败"}

@router.post("/api/v1/rag/chat")
async def rag_chat(payload: dict):
    """
    端到端 RAG 聊天：输入问题 → 自动检索知识库 → LLM 回复
    等价于 Dify 的"知识库对话"应用
    """
    query = payload.get("query", "")
    kb = payload.get("kb", "")
    if not query:
        return {"success": False, "detail": "请提供问题"}
    
    # 调用 RAG 查询
    import httpx
    async with httpx.AsyncClient(timeout=60) as c:
        resp = await c.post("http://127.0.0.1:8765/api/v1/rag/query",
                           json={"query": query, "kb": kb, "top_k": 5, "use_rerank": True, "use_llm": True})
        data = resp.json()
    
    if data.get("success") and data.get("llm_answer"):
        return {"success": True, "answer": data["llm_answer"], "sources": data.get("results", []), "mode": "rag"}
    
    # 降级：直接 LLM
    try:
        from api.routes.routes_smart_chat import _call_llm
        answer = await _call_llm(query, provider="glm")
        return {"success": True, "answer": answer, "mode": "direct_llm"}
    except:
        return {"success": False, "detail": "RAG 查询失败，LLM 也不可用。"}


# ============================================================
# 注册到 smart_chat 的关键词
# ============================================================
_RAG_KEYWORDS = ["知识库", "上传文档", "查询知识库", "找资料", "RAG", "rag查询"]
