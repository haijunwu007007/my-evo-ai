"""Seed RAG knowledge base with default document"""
import sqlite3, time
from pathlib import Path

DB = Path("D:/AUTO-EVO-AI-V0.1/core/adaptive_engine.db")
RAG_DIR = Path("D:/AUTO-EVO-AI-V0.1/data/rag")

conn = sqlite3.connect(str(DB))

for table_sql in [
    "CREATE TABLE IF NOT EXISTS rag_knowledge (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, description TEXT, doc_count INTEGER DEFAULT 0, chunk_count INTEGER DEFAULT 0, created_at REAL)",
    "CREATE TABLE IF NOT EXISTS rag_documents (id INTEGER PRIMARY KEY AUTOINCREMENT, kb_name TEXT, filename TEXT, title TEXT, file_path TEXT, chunk_count INTEGER DEFAULT 0, created_at REAL)",
    "CREATE TABLE IF NOT EXISTS rag_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER, kb_name TEXT, text TEXT, embedding BLOB, created_at REAL)",
]:
    conn.execute(table_sql)

conn.execute("INSERT OR IGNORE INTO rag_knowledge (name, description, created_at) VALUES (?,?,?)",
    ("default", "AUTO-EVO-AI 系统知识库", time.time()))

text = open("D:/AUTO-EVO-AI-V0.1/rag_seed.md", encoding="utf-8").read()
chunks = [line.strip() for line in text.split("\n") if line.strip()]

doc_dir = RAG_DIR / "documents" / "default"
doc_dir.mkdir(parents=True, exist_ok=True)
(doc_dir / "rag_seed.md").write_text(text, encoding="utf-8")

cursor = conn.execute("INSERT INTO rag_documents (kb_name, filename, title, file_path, created_at) VALUES (?,?,?,?,?)",
    ("default", "rag_seed.md", "AUTO-EVO-AI V0.1 System Manual", str(doc_dir / "rag_seed.md"), time.time()))
doc_id = cursor.lastrowid

for i, ck in enumerate(chunks):
    conn.execute("INSERT INTO rag_chunks (doc_id, kb_name, chunk_index, content, created_at) VALUES (?,?,?,?,?)",
        (doc_id, "default", i, ck, time.time()))

conn.execute("UPDATE rag_knowledge SET doc_count=doc_count+1, chunk_count=chunk_count+? WHERE name=?",
    (len(chunks), "default"))
conn.commit()
conn.close()

print(f"OK: 1 doc, {len(chunks)} chunks seeded into 'default' KB")
