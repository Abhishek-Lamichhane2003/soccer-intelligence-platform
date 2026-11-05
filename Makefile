.PHONY: up down logs test backend-test frontend-test check train-xg frontend-lock ensure-frontend-lock loadtest reset prod-config

frontend-lock:
	docker run --rm --user "$(shell id -u):$(shell id -g)" -e HOME=/tmp -v "$(CURDIR)/frontend:/app" -w /app node:22-alpine npm install --package-lock-only --ignore-scripts --no-audit --no-fund

ensure-frontend-lock:
	@if [ ! -f frontend/package-lock.json ]; then echo "Generating frontend/package-lock.json for reproducible installs..."; $(MAKE) frontend-lock; fi

up:
	./scripts/start-dev.sh

down:
	docker compose down

logs:
	docker compose logs -f backend worker frontend

backend-test:
	docker compose run --rm -e APP_ENV=test -e DATABASE_URL=sqlite+aiosqlite:////tmp/soccer_intelligence_test.db backend pytest -q

frontend-test: ensure-frontend-lock
	docker compose run --rm frontend npm test

test: backend-test frontend-test

check:
	./scripts/release-audit.sh

train-xg:
	docker compose run --rm backend python -m ml.train_xg --max-matches 50

loadtest:
	docker compose run --rm -p 8089:8089 -v ./loadtest:/loadtest backend locust -f /loadtest/locustfile.py --host http://backend:8000

prod-config:
	docker compose -f docker-compose.prod.yml --env-file .env.production config

reset:
	docker compose down -v
