#!/usr/bin/env bash
set -euo pipefail

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Start ASGI server with hot-reload for dev
exec watchfiles --filter python "daphne -b 0.0.0.0 -p 8000 aegis.asgi:application" /app /opt/athena-utils


