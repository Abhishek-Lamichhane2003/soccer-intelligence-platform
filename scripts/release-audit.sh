#!/bin/sh
set -eu
python -m compileall -q backend/app backend/ml backend/tests backend/alembic
python scripts/release-audit.py
if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
  docker compose -f docker-compose.prod.yml --env-file .env.production.example config >/dev/null
  echo 'Docker Compose config PASS'
else
  echo 'Docker unavailable: Compose YAML was parsed by the release audit.'
fi
if [ -d frontend/node_modules ]; then
  (cd frontend && npm test && npm run build)
else
  echo 'frontend/node_modules absent: runtime frontend tests require npm install/Docker.'
fi
printf '%s\n' 'Release audit PASS'
