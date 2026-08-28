.PHONY: install test lint fmt up down logs seed

install:
	pip install -r requirements-dev.txt

test:
	pytest

lint:
	ruff check taskq tests

fmt:
	ruff check --fix taskq tests

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f worker

# Enqueue a few demo jobs against a running API (needs the stack up).
seed:
	curl -s -X POST localhost:8000/jobs -H 'content-type: application/json' -d '{"task":"compute_fibonacci","payload":{"n":20},"priority":"high"}'; echo
	curl -s -X POST localhost:8000/jobs -H 'content-type: application/json' -d '{"task":"slow_query","payload":{"seconds":3},"priority":"default"}'; echo
	curl -s -X POST localhost:8000/jobs -H 'content-type: application/json' -d '{"task":"always_fail","priority":"low"}'; echo
