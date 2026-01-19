# Docker Compose command 
COMPOSE = docker compose

# Service names (must match docker-compose.yml)
APP_SERVICE = app
DB_SERVICE  = postgres

# Default target
.DEFAULT_GOAL := help

# ======================================
# Phony targets (not real files)
# ======================================
.PHONY: help init build up down restart logs app-logs db-logs ps shell db-shell clean

# ======================================
# Help
# ======================================
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# ======================================
# Environment setup
# ======================================
init: ## Create .env file from example if missing
	@[ -f .env ] || cp .env.example .env

# Build
build: init ## Build application images
	$(COMPOSE) build
	

# Run
up: init ## Start all services in background
	$(COMPOSE) up -d

rebuild: init ## Rebuild and restart all services
	$(COMPOSE) up -d --build
restart: ## Restart all services
	$(COMPOSE) restart

down: ## Stop and remove containers, networks
	$(COMPOSE) down

# ======================================
# Logs
# ======================================
logs: ## Follow logs from all services
	$(COMPOSE) logs -f

app-logs: ## Follow Streamlit app logs only
	$(COMPOSE) logs -f $(APP_SERVICE)

db-logs: ## Follow Postgres/PostGIS logs only
	$(COMPOSE) logs -f $(DB_SERVICE)

# ======================================
# Status
# ======================================
ps: ## Show running containers
	$(COMPOSE) ps

# ======================================
# Shell access
# ======================================
shell: ## Open a shell inside the Streamlit app container
	$(COMPOSE) exec $(APP_SERVICE) /bin/bash

db-shell: ## Open a psql shell inside the Postgres container
	$(COMPOSE) exec $(DB_SERVICE) psql -U $$POSTGRES_USER -d $$POSTGRES_DB

# ======================================
# Cleanup
# ======================================
clean: ## Remove stopped containers, networks, and dangling images
	$(COMPOSE) down -v --remove-orphans
	docker system prune -f
