#!/usr/bin/env bash
set -euo pipefail

# Optional pre-download of the reranker model into HF cache
python - <<'PY'
import os
try:
    from huggingface_hub import snapshot_download
    repo_id = os.environ.get('RERANKER_MODEL', 'BAAI/bge-reranker-large')
    snapshot_download(repo_id=repo_id)
    print(f"[entrypoint_worker] predownloaded: {repo_id}")
except Exception as e:
    print(f"[entrypoint_worker] warning: predownload failed: {e}")
PY

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Start Celery worker with hot-reload for dev
exec watchfiles --filter python "celery -A aegis.celery worker -Q gateway -n gateway_worker@%h --concurrency=1 --pool=solo -l INFO --logfile=-" /app /opt/athena-utils


