#!/bin/bash
# AUTO-EVO-AI 每日SQLite备份脚本
# 用法: crontab -e 添加 0 3 * * * /home/ubuntu/my-evo-ai/scripts/backup.sh

set -e
BACKUP_DIR="/home/ubuntu/backups"
DB_DIR="/home/ubuntu/my-evo-ai/data"
DATE=$(date +%Y%m%d_%H%M)
mkdir -p "$BACKUP_DIR"

# 备份所有SQLite数据库
for db in "$DB_DIR"/*.db; do
  [ -f "$db" ] || continue
  name=$(basename "$db")
  sqlite3 "$db" ".backup '$BACKUP_DIR/${name%.*}_$DATE.db'"
  gzip -f "$BACKUP_DIR/${name%.*}_$DATE.db"
done

# 保留最近30天
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

# 告警: 如果备份失败则发送通知
echo "[BACKUP] $DATE: $(ls $BACKUP_DIR/*$DATE* 2>/dev/null | wc -l) 个数据库已备份"
