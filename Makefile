COMPOSE_LOCAL=ops/docker/compose/docker-compose.local.yml
COMPOSE_PROD=ops/docker/compose/docker-compose.prod.yml
ENV_FILE=.env

.PHONY: up down logs ps build prod-up prod-down

up:
	docker compose -f $(COMPOSE_LOCAL) --env-file $(ENV_FILE) up -d --build

down:
	docker compose -f $(COMPOSE_LOCAL) --env-file $(ENV_FILE) down

logs:
	docker compose -f $(COMPOSE_LOCAL) --env-file $(ENV_FILE) logs -f --tail=100

ps:
	docker compose -f $(COMPOSE_LOCAL) --env-file $(ENV_FILE) ps

build:
	docker compose -f $(COMPOSE_LOCAL) --env-file $(ENV_FILE) build

prod-up:
	docker compose -f $(COMPOSE_PROD) --env-file $(ENV_FILE) up -d --build

prod-down:
	docker compose -f $(COMPOSE_PROD) --env-file $(ENV_FILE) down
