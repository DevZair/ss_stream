#!/bin/bash
# Restore backup directory (db.sql.gz + media.tgz) for MySQL/Postgres/SQLite.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup_dir>" >&2
  exit 1
fi

BACKUP_DIR="$1"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE=${DJANGO_DB_ENGINE:-postgres}
MEDIA_DIR=${MEDIA_DIR:-"$ROOT_DIR/media"}
DB_DUMP="$BACKUP_DIR/db.sql.gz"
MEDIA_ARCHIVE="$BACKUP_DIR/media.tgz"

if [ ! -f "$DB_DUMP" ]; then
  echo "DB dump $DB_DUMP not found" >&2
  exit 1
fi

case "$ENGINE" in
  mysql* )
    DB_NAME=${MYSQL_DB:-warehouse_system}
    DB_USER=${MYSQL_USER:-root}
    DB_PASSWORD=${MYSQL_PASSWORD:-}
    DB_HOST=${MYSQL_HOST:-localhost}
    DB_PORT=${MYSQL_PORT:-3306}
    echo "[+] Dropping and recreating MySQL database $DB_NAME"
    MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -e "DROP DATABASE IF EXISTS \`$DB_NAME\`; CREATE DATABASE \`$DB_NAME\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    echo "[+] Restoring $DB_NAME from $DB_DUMP"
    gunzip -c "$DB_DUMP" | MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME"
    ;;
  postgres* )
    DB_NAME=${POSTGRES_DB:-warehouse_system}
    DB_USER=${POSTGRES_USER:-postgres}
    DB_PASSWORD=${POSTGRES_PASSWORD:-}
    DB_HOST=${POSTGRES_HOST:-localhost}
    DB_PORT=${POSTGRES_PORT:-5432}
    echo "[+] Resetting public schema in Postgres $DB_NAME"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" >/dev/null
    echo "[+] Restoring $DB_NAME from $DB_DUMP"
    gunzip -c "$DB_DUMP" | PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
    ;;
  sqlite* )
    SQLITE_PATH=${SQLITE_PATH:-"$ROOT_DIR/db.sqlite3"}
    echo "[+] Restoring SQLite to $SQLITE_PATH from $DB_DUMP"
    gunzip -c "$DB_DUMP" > "$SQLITE_PATH"
    ;;
  * )
    echo "Unknown DB engine: $ENGINE (use mysql, postgres, sqlite)" >&2
    exit 1
    ;;
esac

if [ -f "$MEDIA_ARCHIVE" ]; then
  echo "[+] Restoring media to $MEDIA_DIR"
  mkdir -p "$MEDIA_DIR"
  tar -xzf "$MEDIA_ARCHIVE" -C "$MEDIA_DIR"
else
  echo "[~] Media archive not found in $BACKUP_DIR, skipping"
fi

echo "[✓] Restore completed from $BACKUP_DIR"
