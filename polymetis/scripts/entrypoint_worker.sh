#!/usr/bin/env bash
set -euo pipefail

exec watchfiles --filter python "celery -A polymetis.celery worker -Q sensitive -n sensitive_worker@%h --concurrency=1 --pool=solo" /app /opt/athena-utils


