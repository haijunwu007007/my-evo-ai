"""统一项目中所有版本字符串为 V0.1"""
import re, os
from pathlib import Path

BASE = Path(r"D:\AUTO-EVO-AI-V0.1")
EXCLUDE_DIRS = {".git", "__pycache__", ".evo_data", "_archive"}
EXCLUDE_EXT = {".pyc", ".db", ".png", ".jpg", ".ico", ".svg", ".woff2", ".map"}

# 替换规则: (模式, 替换)
REPLACE_RULES = [
    # docstring/注释中的旧版本号
    (r'AUTO-EVO-AI v7\.\d+', 'AUTO-EVO-AI V0.1'),
    (r'AUTO-EVO-AI v6\.\d+', 'AUTO-EVO-AI V0.1'),
    (r'AUTO-EVO-AI v5\.\d+', 'AUTO-EVO-AI V0.1'),
    # 类级 VERSION 属性 (v7.x / v6.xx)
    (r'VERSION\s*=\s*"v7\.\d+"', 'VERSION = "V0.1"'),
    (r'VERSION\s*=\s*"v6\.\d+"', 'VERSION = "V0.1"'),
    # __module_meta__ 中版本为 v7.x/v6.xx 的描述
    (r'"version"\s*:\s*"v7\.\d+"', '"version": "1.0.0"'),
    (r'"version"\s*:\s*"v6\.\d+"', '"version": "1.0.0"'),
    # 版本号在模块全称描述中的
    (r'版本:\s*v6\.\d+', '版本: V0.1'),
    (r'版本:\s*v7\.0', '版本: V0.1'),
    # 注释中的版本声明
    (r'/\*\s*v\d+\.\d+\s', '/* V0.1 '),
    # 模块标题中的 V0.1 / V0.1 / V0.1 等（作为独立版本标识）
    (r'v6\.\d{2,}', 'V0.1'),
    (r'v7\.\d+', 'V0.1'),
    # 模块 meta 描述中的版本标签
    (r'VERSION\s+=\s+"v7\.\d+"', 'VERSION = "V0.1"'),
    (r'VERSION\s+=\s+"v6\.\d+"', 'VERSION = "V0.1"'),
]

DRY_RUN = False  # 改为 True 只打印不修改

def process_file(path: Path) -> bool:
    try:
        content = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return False
    
    new_content = content
    changed = False
    for pattern, replacement in REPLACE_RULES:
        replaced, count = re.subn(pattern, replacement, new_content)
        if count > 0:
            logger.info(f"  {path.relative_to(BASE)}: {pattern} -> {replacement} ({count}x)"))
            new_content = replaced
            changed = True
    
    if changed and not DRY_RUN:
        path.write_text(new_content, encoding='utf-8')
    return changed

def main():
    files_checked = 0
    files_changed = 0
    
    for ext in ('*.py', '*.js', '*.html', '*.md', '*.json', '*.yaml', '*.yml', '*.css'):
        for path in sorted(BASE.rglob(ext)):
            # 跳过排除目录
            rel = path.relative_to(BASE)
            if any(p.name in EXCLUDE_DIRS or p.name.startswith('.') for p in rel.parents):
                continue
            if path.suffix in EXCLUDE_EXT:
                continue
            files_checked += 1
            changed = process_file(path)
            if changed:
                files_changed += 1
    
    logger.info(f"\n检查了 {files_checked} 个文件, 修改了 {files_changed} 个文件"))

if __name__ == '__main__':
    main()
