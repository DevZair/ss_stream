#!/bin/bash
# Quick SQLite snapshot + media archive (lightweight local copy).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SQLITE_PATH=${SQLITE_PATH:-"$ROOT_DIR/db.sqlite3"}
BACKUP_ROOT=${BACKUP_DIR:-"$ROOT_DIR/backups"}
MEDIA_DIR=${MEDIA_DIR:-"$ROOT_DIR/media"}
TS=$(date +%Y%m%d_%H%M%S)

if [ ! -f "$SQLITE_PATH" ]; then
  echo "SQLite file $SQLITE_PATH not found" >&2
  exit 1
fi

TARGET_DIR="$BACKUP_ROOT/sqlite_${TS}"
mkdir -p "$TARGET_DIR"

echo "[+] Copying SQLite to $TARGET_DIR/db.sqlite3"
cp "$SQLITE_PATH" "$TARGET_DIR/db.sqlite3"

if [ -d "$MEDIA_DIR" ]; then
  echo "[+] Archiving media from $MEDIA_DIR"
  tar -czf "$TARGET_DIR/media.tgz" -C "$MEDIA_DIR" .
else
  echo "[~] Media directory $MEDIA_DIR not found, skipping"
fi

echo "[✓] SQLite snapshot saved to $TARGET_DIR"
