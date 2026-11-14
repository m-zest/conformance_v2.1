.DEFAULT_GOAL := help
COMPOSE := docker compose

help:  ## Show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

up:  ## Build and start the full stack
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  Dashboard        http://localhost:8080   (admin@meridian.example / see ADMIN_PASSWORD)"
	@echo "  Sample tool      http://localhost:8090"
	@echo "  Gateway          http://localhost:8000"

down:  ## Stop the stack and keep the data
	$(COMPOSE) down

reset:  ## Stop the stack and delete all data
	$(COMPOSE) down -v

logs:  ## Follow the gateway log
	$(COMPOSE) logs -f gateway

ps:  ## Show service status
	$(COMPOSE) ps

guard:  ## Start the optional Llama Guard service (set GUARD_LLM_ENABLED=true in .env)
	$(COMPOSE) --profile guard up -d

examples:  ## Send a few example requests through the gateway
	./scripts/send-examples.sh

verify:  ## Verify the audit ledger from the command line
	$(COMPOSE) exec gateway python -m app.cli verify-ledger

test:  ## Run the backend test suite locally
	cd backend && python -m pytest -q

.PHONY: help up down reset logs ps guard examples verify test
