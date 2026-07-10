"""模块RAG索引 — 457模块建可搜索目录"""
import logging
logger = logging.getLogger("evo.module_catalog")
import os, json, ast, re
from pathlib import Path
from typing import Dict, List

BASE = Path(__file__).resolve().parent.parent
MODULES_DIR = BASE / "modules"
INDEX_FILE = BASE / "data" / "module_index.json"

def _extract_info(filepath: Path) -> dict:
    """从模块文件提取关键信息"""
    try:
        src = filepath.read_text(encoding='utf-8', errors='replace')
    except:
        return None
    name = filepath.stem
    info = {"name": name, "file": str(filepath.relative_to(BASE)),
            "size": len(src), "doc": "", "classes": [], "functions": [],
            "keywords": [], "actions": []}
    # 提取docstring
    doc_match = re.match(r'"""(.*?)"""', src, re.DOTALL)
    if doc_match:
        info["doc"] = doc_match.group(1).strip()[:200]
    # 提取类和方法
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                info["classes"].append(node.name)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        info["actions"].append(item.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):
                    info["functions"].append(node.name)
    except:
        pass
    # 提取关键词（中文+英文）
    words = set(re.findall(r'[\u4e00-\u9fff]{2,}', src))
    words.update(re.findall(r'\b[a-z]{4,}\b', src.lower()))
    info["keywords"] = list(words)[:50]
    return info

def build_index() -> Dict:
    """扫描所有模块建立索引"""
    index = {}
    for fp in sorted(MODULES_DIR.glob("*.py")):
        if fp.name.startswith("_"):
            continue
        info = _extract_info(fp)
        if info:
            index[info["name"]] = info
    # 保存
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding='utf-8')
    return index

def load_index() -> Dict:
    """加载索引"""
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding='utf-8'))
    return build_index()

def search(query: str, top_k: int = 10) -> List[dict]:
    """搜索模块 — 关键词匹配"""
    index = load_index()
    q_words = set(re.findall(r'[\u4e00-\u9fff]{2,}|\w{3,}', query.lower()))
    scored = []
    for name, info in index.items():
        score = 0
        text = f"{name} {' '.join(info['keywords'])} {info['doc']} {' '.join(info['classes'])} {' '.join(info['actions'])}".lower()
        for w in q_words:
            if w in text:
                score += text.count(w)
        if score > 0:
            scored.append((score, info))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:top_k]]

if __name__ == "__main__":
    idx = build_index()
    print(f"索引完成: {len(idx)} 模块")
    r = search("数据库")
    print(f"搜索'数据库'结果: {[m['name'] for m in r]}")
