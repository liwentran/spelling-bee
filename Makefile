.PHONY: up down tunnel db-status run migrate db-shell

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

up: tunnel
	@echo "🚀 Starting backend server on http://0.0.0.0:8003..."
	cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8003 --reload

down:
	@pkill -f "uvicorn main:app --host 0.0.0.0 --port 8003" || true
	@echo "Stopped backend."
