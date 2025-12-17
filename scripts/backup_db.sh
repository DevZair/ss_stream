#!/bin/bash
# Универсальный бэкап БД для локалки: Postgres или SQLite.
set -euo pipefail

ENGINE=${DJANGO_DB_ENGINE:-postgres}
BACKUP_DIR=${BACKUP_DIR:-backups}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

case "$ENGINE" in
  postgres* )
    DB_NAME=${POSTGRES_DB:-warehouse_system}
    DB_USER=${POSTGRES_USER:-postgres}
    DB_PASSWORD=${POSTGRES_PASSWORD:-}
    DB_HOST=${POSTGRES_HOST:-localhost}
    DB_PORT=${POSTGRES_PORT:-5432}
    BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"
    echo "[+] Создаю бэкап PostgreSQL в $BACKUP_FILE"
    PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"
    ;;
  sqlite* )
    SQLITE_PATH=${SQLITE_PATH:-db.sqlite3}
    if [ ! -f "$SQLITE_PATH" ]; then
      echo "Файл SQLite $SQLITE_PATH не найден" >&2
      exit 1
    fi
    BACKUP_FILE="$BACKUP_DIR/$(basename "${SQLITE_PATH%.sqlite}")_${TIMESTAMP}.sqlite.gz"
    echo "[+] Создаю бэкап SQLite в $BACKUP_FILE"
    gzip < "$SQLITE_PATH" > "$BACKUP_FILE"
    ;;
  * )
    echo "Неизвестный движок БД: $ENGINE (используй postgres или sqlite)" >&2
    exit 1
    ;;
esac

echo "[✓] Резервная копия готова: $BACKUP_FILE"
