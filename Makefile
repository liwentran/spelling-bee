.PHONY: up dev down tunnel db-status run migrate seed db-shell deploy logs restart

tunnel:
	@if lsof -Pi :5433 -sTCP:LISTEN -t >/dev/null ; then \
		echo "✅ SSH tunnel to deployed DB is already active on port 5433."; \
	else \
		echo "🔌 Starting SSH tunnel to droplet general-db (172.18.0.3:5432)..."; \
		ssh -f -N -L 5433:172.18.0.3:5432 droplet; \
		echo "✅ Tunnel connected on port 5433."; \
	fi

db-status:
	@echo "📊 Querying spellingbee tables on remote droplet..."
	ssh droplet "docker exec general-db psql -U postgres -d spellingbee -c '\dt'"

db-shell:
	ssh -t droplet "docker exec -it general-db psql -U postgres -d spellingbee"

migrate: tunnel
	cd backend && uv run alembic upgrade head

seed: migrate
	cd backend && uv run python seed_examples.py

up: tunnel
	@echo "🚀 Starting backend server on http://0.0.0.0:8003..."
	cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8003 --reload

dev: up  ## alias for `make up`

down:
	@pkill -f "uvicorn main:app --host 0.0.0.0 --port 8003" || true
	@echo "Stopped backend."

# --- Droplet deployment (http://143.244.162.12:8003) ---
# Only ever touches the spelling-bee-backend container; other apps share this droplet.

deploy:
	@git diff --quiet && git diff --cached --quiet || (echo "❌ Uncommitted changes. Commit and push first."; exit 1)
	@git fetch -q origin main
	@[ "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" ] || (echo "❌ HEAD is not origin/main. Push first."; exit 1)
	@echo "🚀 Deploying $$(git rev-parse --short HEAD) to droplet..."
	ssh droplet 'cd ~/spelling-bee && git pull --ff-only && docker-compose up -d --build --no-deps spelling-bee-backend'
	@echo "✅ Deployed: http://143.244.162.12:8003/"

logs:
	ssh -t droplet "docker logs --tail=100 -f spelling-bee-backend"

restart:
	ssh droplet "docker restart spelling-bee-backend"
