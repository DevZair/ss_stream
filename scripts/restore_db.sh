#!/bin/bash
set -euo pipefail

# Восстанавливает базу из gzip-дампа, созданного backup_db.sh
# Использует переменные окружения: MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT

if [ $# -lt 1 ]; then
  echo "Использование: $0 <путь_к_дампу.sql.gz>" >&2
  exit 1
fi

DUMP_PATH="$1"
if [ ! -f "$DUMP_PATH" ]; then
  echo "Файл $DUMP_PATH не найден" >&2
  exit 1
fi

MYSQL_DATABASE=${MYSQL_DATABASE:-warehouse_system}
MYSQL_USER=${MYSQL_USER:-root}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-}
MYSQL_HOST=${MYSQL_HOST:-localhost}
MYSQL_PORT=${MYSQL_PORT:-3306}

echo "[+] Восстанавливаю $MYSQL_DATABASE из $DUMP_PATH"
gunzip -c "$DUMP_PATH" | MYSQL_PWD="$MYSQL_PASSWORD" mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" "$MYSQL_DATABASE"
echo "[✓] Восстановление завершено"
