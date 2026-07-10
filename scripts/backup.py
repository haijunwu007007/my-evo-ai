#!/usr/bin/env python3
"""AUTO-EVO-AI 数据备份脚本 — 备份SQLite和配置到 backup/ 目录"""
import shutil, os, datetime, json, sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE / "backup"
DATA_FILES = [
    BASE / "core" / "adaptive_engine.db",
    BASE / "core" / "adaptive_engine.db-wal",
    BASE / "core" / "adaptive_engine.db-shm",
    BASE / ".env",
    BASE / "config.yaml",
]

def backup():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / ts
    dest.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for f in DATA_FILES:
        if f.exists():
            shutil.copy2(f, dest / f.name)
            count += 1
    
    # 导出 SQLite 数据为 SQL dump
    db_path = BASE / "core" / "adaptive_engine.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            with open(dest / "dump.sql", "w", encoding="utf-8") as f:
                for line in conn.iterdump():
                    f.write(line + "\n")
            conn.close()
            count += 1
        except: pass
    
    # 记录备份清单
    manifest = {"time": ts, "files": count, "size": sum(f.stat().st_size for f in dest.iterdir() if f.is_file())}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    
    # 清理超过30天的旧备份
    for d in sorted(BACKUP_DIR.iterdir()):
        if d.is_dir() and d.name < (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m"):
            shutil.rmtree(d, ignore_errors=True)
    
    logger.info(f"备份完成: {dest} ({count} 文件, {manifest['size']/1024:.1f} KB)"))

if __name__ == "__main__":
    backup()
