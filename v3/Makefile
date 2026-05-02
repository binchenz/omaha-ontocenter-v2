.PHONY: start stop test lint build

start:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f

# Python API
py-test:
	cd python-api && pytest

py-lint:
	cd python-api && ruff check app/ tests/

py-install:
	cd python-api && pip install -r requirements.txt

py-migrate:
	cd python-api && alembic upgrade head

# Next.js
fe-install:
	cd nextjs && npm install

fe-dev:
	cd nextjs && npm run dev

fe-build:
	cd nextjs && npm run build

fe-lint:
	cd nextjs && npm run lint

fe-typecheck:
	cd nextjs && npm run typecheck

# Full
install: py-install fe-install
lint: py-lint fe-lint fe-typecheck
test: py-test

build:
	docker compose build

clean:
	docker compose down -v
