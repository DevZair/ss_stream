#!/bin/bash
# Сброс демо: восстановление БД из эталонного бэкапа (Postgres или SQLite).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE=${DJANGO_DB_ENGINE:-postgres}
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"

if [[ "$ENGINE" == sqlite* ]]; then
  DEMO_BACKUP="${DEMO_BACKUP:-$BACKUP_DIR/demo_seed.sqlite.gz}"
  SQLITE_PATH="${SQLITE_PATH:-$ROOT_DIR/db.sqlite3}"
  if [ ! -f "$DEMO_BACKUP" ]; then
    echo "Не найден файл демо-бэкапа $DEMO_BACKUP (создайте его через scripts/backup_db.sh)." >&2
    exit 1
  fi
  echo "[+] Восстанавливаю демо SQLite в $SQLITE_PATH из $DEMO_BACKUP"
  gunzip -c "$DEMO_BACKUP" > "$SQLITE_PATH"
else
  DEMO_BACKUP="${DEMO_BACKUP:-$BACKUP_DIR/demo_seed.sql.gz}"
  DB_NAME=${POSTGRES_DB:-warehouse_system}
  DB_USER=${POSTGRES_USER:-postgres}
  DB_PASSWORD=${POSTGRES_PASSWORD:-}
  DB_HOST=${POSTGRES_HOST:-localhost}
  DB_PORT=${POSTGRES_PORT:-5432}
  if [ ! -f "$DEMO_BACKUP" ]; then
    echo "Не найден файл демо-бэкапа $DEMO_BACKUP (создайте его через scripts/backup_db.sh)." >&2
    exit 1
  fi
  echo "[+] Сбрасываю схему public в $DB_NAME"
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" >/dev/null
  echo "[+] Восстанавливаю демо-данные из $DEMO_BACKUP"
  gunzip -c "$DEMO_BACKUP" | PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
fi

echo "[✓] Демо окружение сброшено."
