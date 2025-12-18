#!/bin/bash
# Delete old ActivityLog rows (default older than 90 days). Set DRY_RUN=1 to only count.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RETENTION_DAYS=${LOG_RETENTION_DAYS:-90}
DRY_RUN=${DRY_RUN:-0}

cd "$ROOT_DIR"

python3 manage.py shell <<PY
from datetime import timedelta
from django.utils import timezone
from inventory.models import ActivityLog

retention_days = int("$RETENTION_DAYS")
dry_run = bool(int("$DRY_RUN"))
cutoff = timezone.now() - timedelta(days=retention_days)
qs = ActivityLog.objects.filter(created_at__lt=cutoff)
count = qs.count()
print(f"[info] ActivityLog older than {retention_days}d (before {cutoff:%Y-%m-%d %H:%M}): {count}")
if dry_run:
    print("[info] DRY_RUN=1, nothing deleted")
else:
    deleted, _ = qs.delete()
    print(f"[done] Deleted {deleted} rows")
PY
