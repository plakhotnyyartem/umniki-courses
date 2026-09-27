#!/bin/zsh
# Запуск рабочей копии сайта. Настройки и секреты — в data/prod.env (не в git):
#   DATABASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD, COOKIE_SECURE=1, SEED_DEMO_CONTENT=1, PORT
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
set -a
source "$ROOT/data/prod.env"
set +a
# Слушаем только localhost: снаружи сайт доступен лишь через туннель Cloudflare
exec "$ROOT/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port "${PORT:-8020}" --app-dir "$ROOT/backend"
