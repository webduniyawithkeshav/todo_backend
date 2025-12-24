up:
	docker compose up -d --build

down:
	docker compose down -v

test:
	docker compose run --rm app pytest -q

.PHONY: up down test
