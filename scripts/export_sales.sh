#!/bin/bash
# Export sales data (Sales, SaleItem, SalesReport) to JSON snapshots.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EXPORT_DIR=${EXPORT_DIR:-"$ROOT_DIR/exports"}
TS=$(date +%Y%m%d_%H%M%S)

if [ -n "${VENV_PATH:-}" ] && [ -f "$VENV_PATH/bin/activate" ]; then
  # Optional virtualenv activation.
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
fi

mkdir -p "$EXPORT_DIR"
cd "$ROOT_DIR"

python3 manage.py dumpdata inventory.Sale --indent 2 > "$EXPORT_DIR/sales_${TS}.json"
python3 manage.py dumpdata inventory.SaleItem --indent 2 > "$EXPORT_DIR/sale_items_${TS}.json"
python3 manage.py dumpdata inventory.SalesReport --indent 2 > "$EXPORT_DIR/sale_reports_${TS}.json"

echo "[✓] Exported to $EXPORT_DIR (timestamp $TS)"
