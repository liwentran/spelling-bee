# spelling-bee. Standard targets shared by every droplet app (see ~/Developer/droplet/README.md):
#   local: install dev test lint migrate      prod: tunnel db-shell deploy status logs rollback restart
.DEFAULT_GOAL := help
.PHONY: help install dev test lint migrate seed local-db tunnel db-shell deploy status logs rollback restart

APP     := spelling-bee
BRANCH  := main
PORT    := 8003
PROD_DB := spellingbee
# Local dev runs on a local Postgres, never the prod DB: the migrations alter constraints, which
# SQLite can't do. `local-postgres` (:5434) is one container shared by every app on this laptop.
LOCAL_DB           := spellingbee
LOCAL_DATABASE_URL := postgresql://postgres:postgres@127.0.0.1:5434/$(LOCAL_DB)
VENV := .venv/bin

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# --- Local ------------------------------------------------------------------------------------

install: ## Create backend/.venv and install requirements
	cd backend && uv venv -q --allow-existing && uv pip install -q -r requirements.txt

local-db: ## Start local-postgres (:5434) and create the $(LOCAL_DB) database
	@docker start local-postgres >/dev/null 2>&1 || docker run -d --name local-postgres -p 127.0.0.1:5434:5432 \
		-e POSTGRES_PASSWORD=postgres -v local-postgres:/var/lib/postgresql/data postgres:15.19 >/dev/null
	@until docker exec local-postgres pg_isready -U postgres -q; do sleep 1; done
	@docker exec local-postgres psql -U postgres -tAc "select 1 from pg_database where datname='$(LOCAL_DB)'" | grep -q 1 \
		|| docker exec local-postgres createdb -U postgres $(LOCAL_DB)

dev: local-db ## Run on http://localhost:8003 against the local DB (0.0.0.0 so phones on the LAN can join)
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) $(VENV)/uvicorn main:app --host 0.0.0.0 --port $(PORT) --reload

migrate: local-db ## Apply migrations to the local DB
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) $(VENV)/alembic upgrade head

seed: migrate ## Load examples/*.json into the local DB
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) $(VENV)/python seed_examples.py

test: local-db ## Migration round trip (upgrade, downgrade, upgrade) on a scratch DB, then import the app
	@docker exec local-postgres dropdb -U postgres --if-exists spellingbee_test
	@docker exec local-postgres createdb -U postgres spellingbee_test
	cd backend && export DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5434/spellingbee_test && \
		$(VENV)/alembic upgrade head && $(VENV)/alembic downgrade base && $(VENV)/alembic upgrade head && \
		$(VENV)/python -c "import main; print('app imports OK')"

lint: ## Syntax errors and undefined names
	uvx ruff check --select E9,F63,F7,F82 backend

# --- Production (droplet) ---------------------------------------------------------------------

tunnel: ## Forward the prod Postgres to localhost:5433
	ssh -N -L 5433:127.0.0.1:5432 droplet

db-shell: ## psql on the prod $(PROD_DB) database
	ssh -t droplet "docker exec -it general-db psql -U postgres -d $(PROD_DB)"

deploy: ## Deploy origin/$(BRANCH) through CI (pushing to $(BRANCH) does the same)
	gh workflow run deploy.yml --ref $(BRANCH)
	@echo "Follow it with: gh run watch"

status: ## Release and health on the droplet
	ssh droplet droplet status $(APP)

logs: ## Follow prod logs
	ssh -t droplet droplet logs $(APP)

rollback: ## Roll back prod to the previous release
	ssh droplet droplet rollback $(APP)

restart: ## Restart the current prod release (resets live games)
	ssh droplet droplet restart $(APP)
