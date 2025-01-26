.PHONY: dev migrate-up migrate-down seed db-reset down build run test clean

# Database connection string (for both local and container use)
DB_URL ?= postgresql://postgres:postgres@localhost:5432/pantry_chef?sslmode=disable

# Build variables
BINARY_NAME=pantry-chef-api
BUILD_DIR=build

# Start everything
dev:
	docker compose -f 'docker/compose/docker-compose.base.yml' up -d --build 
	

# Run migrations
migrate-up:
	migrate -path api/internal/platform/db/migrations -database "$(DB_URL)" up

# Reverse migrations
migrate-down:
	migrate -path api/internal/platform/db/migrations -database "$(DB_URL)" down

# Start API server
api:
	cd api && go run cmd/server/main.go

# Stop and remove containers
down:
	docker compose -f docker/compose/docker-compose.base.yml down -v

# Clean up
clean: down
	docker system prune -f


