"""一次性批量修复: print()→logger + body硬编码→CSS变量"""
import pathlib, re

ROOT = pathlib.Path("D:/AUTO-EVO-AI-V0.1")

# ========== 1. print() → logger (核心文件) ==========
PRINT_FIXES = {
    # file_relative: [(old_print_line_prefix, new_logger_line)]
}

def fix_print(fpath: pathlib.Path) -> int:
    """替换文件中顶级的 print( → logger.info(，跳过 import/startup横幅/流式输出"""
    try:
        c = fpath.read_text("utf-8", errors="ignore")
    except:
        return 0
    lines = c.split("\n")
    changed = 0
    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 跳过注释行、docstring、空行、import
        if not stripped or stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("from ") or stripped.startswith("import "):
            new_lines.append(line)
            continue
        # 跳过LLM流式输出（生成式 print）
        if "print(" in stripped and ("def " in stripped or "stream" in stripped.lower() or "yield" in stripped):
            new_lines.append(line)
            continue
        # 跳过 startup banner / ASCII art
        logger.info(ipped.startswith('print("') and ("====" in stripped or "AUTO" in stripped or "EVO" in stripped or "---" in stripped or "★" in stripped or "█" in stripped or "▄" in stripped or "▀" in stripped):)
            new_lines.append(line)
            continue
        logger.info(int(" in stripped:)
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}logger.info({stripped[6:]})")
            changed += 1
        else:
            new_lines.append(line)
    if changed:
        fpath.write_text("\n".join(new_lines), "utf-8")
        # 确保文件末尾有换行
        c2 = fpath.read_text("utf-8")
        if not c2.endswith("\n"):
            fpath.write_text(c2 + "\n", "utf-8")
    return changed

# ========== 2. body硬编码→CSS变量 ==========
def fix_body_bg(html: str) -> str:
    """替换 body{background:#xxx 为 body{background:var(--bg)"""
    html = re.sub(
        r'body\s*\{([^}]*?)background(?:-color)?\s*:\s*#[0-9a-fA-F]{6}\b',
        r'body{\1background:var(--bg)',
        html
    )
    html = re.sub(
        r'body\s*\{([^}]*?)background(?:-color)?\s*:\s*#[0-9a-fA-F]{3}\b',
        r'body{\1background:var(--bg)',
        html
    )
    # 也替换 body.dark 或 body.light 的硬编码
    html = re.sub(
        r'(body\.(?:dark|light))\s*\{([^}]*?)background(?:-color)?\s*:\s*#[0-9a-fA-F]{6}\b',
        r'\1{\2background:var(--bg)',
        html
    )
    return html

def fix_other_colors(html: str) -> str:
    """替换常见硬编码色值为CSS变量"""
    replacements = [
        (r'#1a1a2e(?![0-9a-fA-F])', 'var(--bg)'),
        (r'#16213e(?![0-9a-fA-F])', 'var(--bg)'),
        (r'#0f3460(?![0-9a-fA-F])', 'var(--accent)'),
        (r'#0f0f1a(?![0-9a-fA-F])', 'var(--bg)'),
        (r'#1e2a4a(?![0-9a-fA-F])', 'var(--card)'),
        (r'#2a2a4a(?![0-9a-fA-F])', 'var(--border)'),
        (r'#2d3561(?![0-9a-fA-F])', 'var(--border)'),
        (r'#f5f5f8(?![0-9a-fA-F])', 'var(--bg)'),
        (r'#ffffff(?![0-9a-fA-F])', 'var(--card)'),
        (r'#e8eaed(?![0-9a-fA-F])', 'var(--border)'),
        (r'background:#111122', 'background:var(--bg)'),
        (r'background:#0b0b16', 'background:var(--bg)'),
        (r'background:#12122a', 'background:var(--card)'),
    ]
    for old, new in replacements:
        html = re.sub(old, new, html)
    return html

# ========== 执行 ==========
total_print_fixed = 0
total_body_fixed = 0
total_other_fixed = 0

# 修复print()
for f in sorted(ROOT.rglob("*.py")):
    if "__pycache__" in str(f) or ".evo" in str(f) or ".git" in str(f):
        continue
    logger.info(d = fix_print(f))
    if changed:
        logger.info(f"  print→logger: {f.relative_to(ROOT)} ({changed}处)"))
        total_print_fixed += changed

# 修复body硬编码
for f in sorted(ROOT.glob("frontend/*.html")):
    try:
        c = f.read_text("utf-8", errors="ignore")
    except:
        continue
    c2 = fix_body_bg(c)
    c3 = fix_other_colors(c2)
    if c3 != c:
        f.write_text(c3, "utf-8")
        logger.info(f"  CSS变量化: {f.name}"))
        if c2 != c:
            total_body_fixed += 1
        if c3 != c2:
            total_other_fixed += 1

logger.info(f"\n=== 统计 ==="))
logger.info(f"print()→logger: {total_print_fixed}处"))
logger.info(f"body硬编码→var(--bg): {total_body_fixed}页"))
logger.info(f"其他硬编码→CSS变量: {total_other_fixed}处"))
