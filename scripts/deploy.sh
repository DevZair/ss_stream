#!/bin/bash
# Simple deploy helper: backup, pull, install deps, migrate, collect static, reload services.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PATH=${VENV_PATH:-"$ROOT_DIR/venv"}

cd "$ROOT_DIR"

if [ "${SKIP_BACKUP:-0}" != "1" ]; then
  echo "[+] Running backup_full.sh before deploy"
  ./scripts/backup_full.sh
fi

echo "[+] Updating sources"
git pull --ff-only

if [ -d "$VENV_PATH" ]; then
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
fi

echo "[+] Installing requirements"
pip install -r requirements.txt

echo "[+] Applying migrations"
python3 manage.py migrate

echo "[+] Collecting static files"
python3 manage.py collectstatic --noinput

if command -v systemctl >/dev/null 2>&1; then
  echo "[~] Reloading services via systemctl (best effort)"
  systemctl reload gunicorn 2>/dev/null || true
  systemctl reload nginx 2>/dev/null || true
else
  echo "[~] systemctl not available, reload app server manually if needed"
fi

echo "[✓] Deploy steps completed"
