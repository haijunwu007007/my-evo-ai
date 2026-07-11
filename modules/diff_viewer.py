from __future__ import annotations

"""

Grade: A

AUTO-EVO-AI V0.1 — 代码差异对比引擎

语法高亮行内对比 + AI变更解释 + 文件对比

"""



__module_meta__ = {

    "id": "diff-viewer",

    "name": "代码差异对比引擎",

    "version": "V0.1",

    "group": "developer",

    "grade": "A",

    "description": "语法高亮行内对比 + AI变更解释 + 文件对比",

    "tags": ["diff", "code", "compare"],

}



import difflib, re, html

from pathlib import Path

from dataclasses import dataclass, field, asdict

from typing import Optional

from modules._base import Result

from modules._base.enterprise_module import EnterpriseModule





# 常见文件扩展名到语言的映射

EXT_LANG = {

    ".py": "python", ".js": "javascript", ".ts": "typescript",

    ".tsx": "typescript", ".jsx": "javascript", ".html": "html",

    ".css": "css", ".scss": "scss", ".json": "json", ".yaml": "yaml",

    ".yml": "yaml", ".md": "markdown", ".sql": "sql", ".sh": "bash",

    ".bash": "bash", ".go": "go", ".rs": "rust", ".java": "java",

    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",

    ".vue": "vue", ".svelte": "svelte", ".xml": "xml",

}





@dataclass

class DiffFile:

    file_path: str = ""

    language: str = ""

    additions: int = 0

    deletions: int = 0

    chunks: list[dict] = field(default_factory=list)

    raw_diff: str = ""





@dataclass

class DiffResult:

    files: list[DiffFile] = field(default_factory=list)

    total_additions: int = 0

    total_deletions: int = 0

    total_files: int = 0

    summary: str = ""





def _get_language(file_path: str) -> str:

    ext = Path(file_path).suffix.lower()

    return EXT_LANG.get(ext, "text")





def highlight_line(line: str, lang: str = "text") -> str:

    """简单的语法高亮，生成HTML"""

    escaped = html.escape(line)

    # 关键词高亮

    keywords = {

        "python": r'\b(def|class|import|from|return|if|else|elif|for|while|try|except|with|as|pass|None|True|False|async|await|raise|yield|lambda|and|or|not|in|is|self)\b',

        "javascript": r'\b(function|const|let|var|return|if|else|for|while|class|import|export|default|from|async|await|try|catch|throw|new|this|typeof|instanceof|null|undefined|true|false)\b',

        "typescript": r'\b(function|const|let|var|return|if|else|for|while|class|interface|type|import|export|default|from|async|await|try|catch|throw|new|this|null|undefined|true|false|enum|implements|extends)\b',

    }

    kw_pattern = keywords.get(lang, '')

    if kw_pattern:

        escaped = re.sub(kw_pattern, r'<span class="kw">\1</span>', escaped)

    # 字符串高亮

    escaped = re.sub(r'("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')', r'<span class="str">\1</span>', escaped)

    # 注释高亮

    escaped = re.sub(r'(#.*$|//.*$)', r'<span class="cm">\1</span>', escaped)

    return escaped





def compare_text(old_text: str, new_text: str, file_path: str = "unknown") -> DiffFile:

    """对比两个文本，生成差异结果"""

    lang = _get_language(file_path)

    old_lines = old_text.splitlines(keepends=True)

    new_lines = new_text.splitlines(keepends=True)



    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    diff = difflib.unified_diff(old_lines, new_lines, n=3)



    diff_file = DiffFile(file_path=file_path, language=lang)

    diff_text = ""

    for line in diff:

        diff_text += line



    diff_file.raw_diff = diff_text



    # 解析chunks

    current_chunk = None

    for line in diff_text.split("
"):

        if line.startswith("@@"):

            m = re.search(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)

            if current_chunk:

                diff_file.chunks.append(current_chunk)

            current_chunk = {

                "old_start": int(m.group(1)) if m else 0,

                "new_start": int(m.group(2)) if m else 0,

                "lines": [],

            }

        elif current_chunk:

            if line.startswith("+"):

                diff_file.additions += 1

                current_chunk["lines"].append({"type": "add", "content": line[1:], "html": highlight_line(line[1:], lang)})

            elif line.startswith("-"):

                diff_file.deletions += 1

                current_chunk["lines"].append({"type": "del", "content": line[1:], "html": highlight_line(line[1:], lang)})

            elif line.startswith(" "):

                current_chunk["lines"].append({"type": "ctx", "content": line, "html": html.escape(line)})



    if current_chunk:

        diff_file.chunks.append(current_chunk)



    return diff_file





def explain_diff(diff_file: DiffFile) -> str:

    """AI解释变更内容"""

    if not diff_file.chunks:

        return "无变更"



    changes = []

    for c in diff_file.chunks:

        adds = sum(1 for l in c["lines"] if l["type"] == "add")

        dels = sum(1 for l in c["lines"] if l["type"] == "del")

        if adds or dels:

            changes.append(f"第{c['old_start']}行附近: +{adds}/-{dels}")



    summary = f"文件 {diff_file.file_path}"

    if changes:

        summary += " — " + "; ".join(changes[:5])

    else:

        summary += " — 无可见变更"



    if diff_file.additions + diff_file.deletions > 50:

        summary += f" (共+{diff_file.additions}/-{diff_file.deletions}行，大范围变更)"

    else:

        summary += f" (+{diff_file.additions}/-{diff_file.deletions}行)"



    return summary





def batch_compare(old_files: dict[str, str], new_files: dict[str, str]) -> DiffResult:

    """批量对比文件"""

    result = DiffResult()

    all_files = set(list(old_files.keys()) + list(new_files.keys()))



    for f in sorted(all_files):

        old = old_files.get(f, "")

        new = new_files.get(f, "")

        if old == new:

            continue

        diff_file = compare_text(old, new, f)

        result.files.append(diff_file)

        result.total_additions += diff_file.additions

        result.total_deletions += diff_file.deletions



    result.total_files = len(result.files)

    result.summary = f"{result.total_files} 文件变更, +{result.total_additions}/-{result.total_deletions} 行"

    return result





class DiffViewerModule(EnterpriseModule):

    def __init__(self):

        super().__init__(module_id="diff-viewer", name="代码差异对比引擎")



    async def initialize(self):

        self._status = "ready"

        return Result(success=True, message="Diff Viewer 就绪")



    async def execute(self, action: str, **params) -> Result:

        try:

            if action == "compare":

                old = params.get("old_text", "")

                new = params.get("new_text", "")

                file_path = params.get("file", "unknown")

                result = compare_text(old, new, file_path)

                return Result(success=True, data=asdict(result))

            elif action == "explain":

                file_path = params.get("file", "unknown")

                old = params.get("old_text", "")

                new = params.get("new_text", "")

                diff_file = compare_text(old, new, file_path)

                explanation = explain_diff(diff_file)

                return Result(success=True, data={"explanation": explanation})

            return Result(success=False, error=f"未知动作: {action}")

        except Exception as e:

            return Result(success=False, error=str(e))



    async def health_check(self):

        return Result(success=True, data={"status": self._status})

