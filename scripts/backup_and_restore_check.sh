#!/bin/bash
# Делает бэкап и проверяет, что восстановление работает (Postgres: во временную БД; SQLite: во временный файл).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE=${DJANGO_DB_ENGINE:-postgres}

cd "$ROOT_DIR"
echo "[+] Создаю бэкап..."
BACKUP_OUTPUT=$(./scripts/backup_db.sh)
echo "$BACKUP_OUTPUT"
BACKUP_FILE=$(echo "$BACKUP_OUTPUT" | grep "Резервная копия" | awk -F': ' '{print $2}' | xargs)
if [ -z "$BACKUP_FILE" ]; then
  echo "Не удалось определить путь к бэкапу из вывода backup_db.sh" >&2
  exit 1
fi
if [[ "$BACKUP_FILE" != /* ]]; then
  BACKUP_FILE="$ROOT_DIR/$BACKUP_FILE"
fi
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Бэкап $BACKUP_FILE не найден" >&2
  exit 1
fi

case "$ENGINE" in
  postgres* )
    DB_NAME=${POSTGRES_DB:-warehouse_system}
    DB_USER=${POSTGRES_USER:-postgres}
    DB_PASSWORD=${POSTGRES_PASSWORD:-}
    DB_HOST=${POSTGRES_HOST:-localhost}
    DB_PORT=${POSTGRES_PORT:-5432}
    TEST_DB="${DB_NAME}_restorecheck"

    echo "[+] Создаю временную БД $TEST_DB для проверки восстановления"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS \"$TEST_DB\"; CREATE DATABASE \"$TEST_DB\" TEMPLATE template0;" >/dev/null

    echo "[+] Восстанавливаю в $TEST_DB из $BACKUP_FILE"
    gunzip -c "$BACKUP_FILE" | PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" >/dev/null

    echo "[+] Проверяю доступность данных"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" -c "SELECT count(*) AS tables_total FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema');" >/dev/null

    echo "[~] Удаляю временную БД $TEST_DB"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS \"$TEST_DB\";" >/dev/null
    ;;
  sqlite* )
    TMP_DB=$(mktemp "$ROOT_DIR/restorecheck_XXXX.sqlite")
    echo "[+] Распаковываю бэкап в $TMP_DB"
    gunzip -c "$BACKUP_FILE" > "$TMP_DB"
    echo "[+] Проверяю целостность SQLite"
    sqlite3 "$TMP_DB" "PRAGMA integrity_check;" >/dev/null
    rm -f "$TMP_DB"
    ;;
  * )
    echo "Неизвестный движок БД: $ENGINE (используй postgres или sqlite)" >&2
    exit 1
    ;;
esac

echo "[✓] Бэкап и проверка восстановления завершены успешно."
