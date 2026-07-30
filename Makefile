.PHONY: install dev-api dev-web test build docker-up clean

install:
	python -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
	cd frontend && npm install

dev-api:
	PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

test:
	.venv/bin/python -m pytest
	cd frontend && npm test

build:
	cd frontend && npm run build

docker-up:
	docker compose up --build

clean:
	find backend -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf frontend/dist .pytest_cache .coverage
