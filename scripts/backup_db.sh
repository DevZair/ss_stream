#!/bin/bash
set -euo pipefail

MYSQL_DATABASE=${MYSQL_DATABASE:-warehouse_system}
MYSQL_USER=${MYSQL_USER:-root}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-}
MYSQL_HOST=${MYSQL_HOST:-localhost}
MYSQL_PORT=${MYSQL_PORT:-3306}
BACKUP_DIR=${BACKUP_DIR:-backups}

mkdir -p "$BACKUP_DIR"
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="$BACKUP_DIR/${MYSQL_DATABASE}_${timestamp}.sql.gz"

echo "[+] Создаю резервную копию в $backup_file"
MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" "$MYSQL_DATABASE" | gzip > "$backup_file"

echo "[✓] Резервная копия готова"
