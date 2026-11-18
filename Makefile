PORT ?= 8000

# Load settings from .env when it exists (copy .env.example to .env).
ifneq ($(wildcard .env),)
ENV_ARG = --env-file ../.env
endif

.PHONY: start test seed

# One command: install, build the frontend, serve everything on http://localhost:$(PORT)
start:
	cd frontend && npm install --no-audit --no-fund && npm run build
	cd backend && uv run uvicorn app.main:app_factory --factory --host 127.0.0.1 --port $(PORT) $(ENV_ARG)

# One command: backend tests, then frontend tests. No network or API key needed.
test:
	cd backend && uv run pytest -q
	cd frontend && npm install --no-audit --no-fund && npm test

# While the app is running: file sample reports so the console has something to show.
# Uses your API key if one is set in .env, otherwise the free offline demo mode.
seed:
	cd backend && uv run python -m app.seed --url http://127.0.0.1:$(PORT)
