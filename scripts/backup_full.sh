#!/bin/bash
# Full backup: database (MySQL/Postgres/SQLite) + media folder with retention.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE=${DJANGO_DB_ENGINE:-postgres}
BACKUP_ROOT=${BACKUP_DIR:-"$ROOT_DIR/backups"}
MEDIA_DIR=${MEDIA_DIR:-"$ROOT_DIR/media"}
RETENTION_DAYS=${RETENTION_DAYS:-14}
TS=$(date +%Y%m%d_%H%M%S)
TARGET_DIR="$BACKUP_ROOT/$TS"
DB_DUMP="$TARGET_DIR/db.sql.gz"

mkdir -p "$TARGET_DIR"

case "$ENGINE" in
  mysql* )
    DB_NAME=${MYSQL_DB:-warehouse_system}
    DB_USER=${MYSQL_USER:-root}
    DB_PASSWORD=${MYSQL_PASSWORD:-}
    DB_HOST=${MYSQL_HOST:-localhost}
    DB_PORT=${MYSQL_PORT:-3306}
    echo "[+] Dumping MySQL $DB_NAME -> $DB_DUMP"
    MYSQL_PWD="$DB_PASSWORD" mysqldump \
      --single-transaction \
      --routines \
      --triggers \
      --default-character-set=utf8mb4 \
      --set-gtid-purged=OFF \
      -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" | gzip > "$DB_DUMP"
    ;;
  postgres* )
    DB_NAME=${POSTGRES_DB:-warehouse_system}
    DB_USER=${POSTGRES_USER:-postgres}
    DB_PASSWORD=${POSTGRES_PASSWORD:-}
    DB_HOST=${POSTGRES_HOST:-localhost}
    DB_PORT=${POSTGRES_PORT:-5432}
    echo "[+] Dumping Postgres $DB_NAME -> $DB_DUMP"
    PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$DB_DUMP"
    ;;
  sqlite* )
    SQLITE_PATH=${SQLITE_PATH:-"$ROOT_DIR/db.sqlite3"}
    if [ ! -f "$SQLITE_PATH" ]; then
      echo "SQLite file $SQLITE_PATH not found" >&2
      exit 1
    fi
    echo "[+] Archiving SQLite $SQLITE_PATH -> $DB_DUMP"
    gzip < "$SQLITE_PATH" > "$DB_DUMP"
    ;;
  * )
    echo "Unknown DB engine: $ENGINE (use mysql, postgres, sqlite)" >&2
    exit 1
    ;;
esac

if [ -d "$MEDIA_DIR" ]; then
  echo "[+] Archiving media from $MEDIA_DIR"
  tar -czf "$TARGET_DIR/media.tgz" -C "$MEDIA_DIR" .
else
  echo "[~] Media directory $MEDIA_DIR not found, skipping"
fi

if [ -d "$BACKUP_ROOT" ]; then
  echo "[~] Cleaning backups older than $RETENTION_DAYS days in $BACKUP_ROOT"
  find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} +
fi

echo "[✓] Backup completed: $TARGET_DIR"
