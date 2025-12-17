#!/bin/bash
# Восстановление бэкапа для Postgres или SQLite.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Использование: $0 <путь_к_дампу.gz>" >&2
  exit 1
fi

DUMP_PATH="$1"
if [ ! -f "$DUMP_PATH" ]; then
  echo "Файл $DUMP_PATH не найден" >&2
  exit 1
fi

ENGINE=${DJANGO_DB_ENGINE:-postgres}

case "$ENGINE" in
  postgres* )
    DB_NAME=${POSTGRES_DB:-warehouse_system}
    DB_USER=${POSTGRES_USER:-postgres}
    DB_PASSWORD=${POSTGRES_PASSWORD:-}
    DB_HOST=${POSTGRES_HOST:-localhost}
    DB_PORT=${POSTGRES_PORT:-5432}
    echo "[+] Очищаю схему public в $DB_NAME"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null
    echo "[+] Восстанавливаю $DB_NAME из $DUMP_PATH"
    gunzip -c "$DUMP_PATH" | PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
    ;;
  sqlite* )
    SQLITE_PATH=${SQLITE_PATH:-db.sqlite3}
    echo "[+] Восстанавливаю SQLite в $SQLITE_PATH из $DUMP_PATH"
    gunzip -c "$DUMP_PATH" > "$SQLITE_PATH"
    ;;
  * )
    echo "Неизвестный движок БД: $ENGINE (используй postgres или sqlite)" >&2
    exit 1
    ;;
esac

echo "[✓] Восстановление завершено"
