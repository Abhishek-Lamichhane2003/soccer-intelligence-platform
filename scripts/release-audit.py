"""Offline release audit for structural invariants that previously caused bugs."""
from __future__ import annotations

import ast
import io
import json
import tokenize
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f'RELEASE AUDIT FAILED: {message}')


for path in list((ROOT / 'backend').rglob('*.py')):
    ast.parse(path.read_text(), filename=str(path))

for path in [ROOT / 'docker-compose.yml', ROOT / 'docker-compose.prod.yml', ROOT / '.github/workflows/ci.yml']:
    yaml.safe_load(path.read_text())
json.loads((ROOT / 'frontend/package.json').read_text())
json.loads((ROOT / 'observability/grafana/dashboards/soccer-api.json').read_text())

compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
backend_volumes = compose['services']['backend'].get('volumes', [])
require('./backend/models:/app/models' in backend_volumes, 'trained xG model directory is not persisted in dev Compose')

prod = yaml.safe_load((ROOT / 'docker-compose.prod.yml').read_text())
extra = prod['services']['backend']['environment']['UVICORN_EXTRA_ARGS']
require('--workers 1' in extra, 'Prometheus in-process metrics require one Uvicorn worker per container')
require(prod['services']['backend']['environment'].get('TRUST_PROXY_HEADERS') == 'true', 'production proxy trust flag missing')
require('caddy' in prod['services'], 'production Compose must bundle HTTPS termination')
require(prod['services']['caddy']['environment'].get('PUBLIC_DOMAIN') is not None, 'production HTTPS domain is not wired')
require((ROOT / 'Caddyfile').exists(), 'Caddy TLS configuration missing')

routes = (ROOT / 'backend/app/api/routes.py').read_text()
require("'access_token': token" not in routes, 'browser auth response still leaks JWT into JSON')

demo = (ROOT / 'backend/app/services/demo_sessions.py').read_text()
require('_prune_local' in demo and '_last_seen' in demo, 'Demo Lab local session cleanup missing')

conftest = (ROOT / 'backend/tests/conftest.py').read_text()
require("os.environ['DATABASE_URL']" in conftest, 'tests must force, not default, the isolated test database')
require('soccer_intelligence_test.db' in conftest and '_assert_safe_test_database' in conftest, 'destructive test DB safety guard missing')

pitch = (ROOT / 'frontend/src/components/PitchRadar.tsx').read_text()
require('Number(p.id)%' not in pitch and 'Number(p.id) %' not in pitch, 'provider-backed shirt numbers are still fabricated')
require('shirt number unavailable' in pitch, 'missing shirt-number state is not explicit')

xg_lab = (ROOT / 'frontend/src/components/XGLab.tsx').read_text()
require('api.xgPredict' in xg_lab, 'interactive UI does not exercise the xG inference endpoint')

provider_text = (ROOT / 'backend/app/providers/football_data.py').read_text()
require('penalty_home' in provider_text and 'regular_home' in provider_text and 'extra_home' in provider_text, 'knockout score context is not normalized')
require('timedelta(days=days + 1)' in provider_text, 'upcoming dateTo exclusive-boundary correction missing')
require("timedelta(days=1)).isoformat()" in provider_text, 'recent dateTo exclusive-boundary correction missing')

makefile = (ROOT / 'Makefile').read_text()
require('ensure-frontend-lock' in makefile and './scripts/start-dev.sh' in makefile, 'first-run frontend lock bootstrap missing')
start_dev = (ROOT / 'scripts/start-dev.sh').read_text()
require('package-lock.json' in start_dev and 'package-lock-only' in start_dev, 'start script does not generate the dependency lock before build')

for dockerfile_name in ['frontend/Dockerfile', 'frontend/Dockerfile.dev']:
    dockerfile = (ROOT / dockerfile_name).read_text()
    require('package-lock.json' in dockerfile and 'npm ci' in dockerfile, f'{dockerfile_name} must require the dependency lock and use npm ci')

raw_crest_patterns = [
    'r.team.crest?<img', 's.team.crest&&<img', 't.crest?<img className="club-crest"',
    'team.crest?<img src={team.crest}', 'm.competition.emblem?<img',
]
frontend_text = '\n'.join(p.read_text() for p in (ROOT / 'frontend/src').rglob('*.tsx'))
for pattern in raw_crest_patterns:
    require(pattern not in frontend_text, f'raw image path without resilient fallback remains: {pattern}')

provider_bytes = (ROOT / 'backend/app/providers/football_data.py').read_bytes()
for token in tokenize.tokenize(io.BytesIO(provider_bytes).readline):
    if token.type == tokenize.OP and token.string == ';':
        raise SystemExit(f'RELEASE AUDIT FAILED: semicolon statement in provider line {token.start[0]}')

print('Release audit PASS')
