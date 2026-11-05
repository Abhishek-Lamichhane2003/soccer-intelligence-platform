#!/bin/sh
set -eu
python -m compileall -q backend/app backend/ml
python - <<'PY'
import json
from pathlib import Path
json.loads(Path('frontend/package.json').read_text())
json.loads(Path('observability/grafana/dashboards/soccer-api.json').read_text())
print('JSON OK')
PY
if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
  echo 'Docker Compose OK'
fi
if [ -d frontend/node_modules ]; then
  (cd frontend && npm test && npm run build)
else
  echo 'frontend/node_modules absent: skipping local frontend test/build; Docker/CI will install dependencies.'
fi
echo 'Static checks OK'
