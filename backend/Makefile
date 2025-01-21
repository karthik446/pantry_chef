include .env
export

SHELL := /bin/bash
.PHONY: up down logs token db setup-security db-reset db-start db-stop db-restart db-status db-setup-user

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

token:
	curl -X POST '${SUPABASE_URL}/auth/v1/token?grant_type=password' \
	-H "apikey: ${SUPABASE_API_KEY}" \
	-H "Content-Type: application/json" \
	-d '{"email": "admin@example.com", "password": "admin123"}'

create-admin:
	# First create the user
	curl -X POST '${SUPABASE_URL}/auth/v1/signup' \
		-H "apikey: ${SUPABASE_API_KEY}" \
		-H "Content-Type: application/json" \
		-d '{"email": "skarthikc.dev@gmail.com", "password": "cUcsuv-majtyc-9gejfa", "data": {"role": "admin"}}'


db:
	docker exec -i supabase_db_pantry_chef_db psql -U ${DB_USER} -d ${DB_NAME} -c "\dt"

setup-security:
	# Revoke public access
	PGPASSWORD=postgres docker exec -i supabase_db_pantry_chef_db psql -U postgres -d ${DB_NAME} -c "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;"
	# Additional security policies...

# Database management commands
db-stop:
	supabase stop

db-start:
	supabase start

db-status:
	supabase status

db-reset:
	@supabase status > /dev/null 2>&1 || (echo "Supabase is not running, starting..." && make db-start)
	supabase db reset
	@echo "Verifying database setup..."
	docker exec -i supabase_db_pantry_chef_db psql -U postgres -d ${DB_NAME} -c "\dt"
	docker exec -i supabase_db_pantry_chef_db psql -U postgres -d ${DB_NAME} -c "SELECT COUNT(*) FROM categories;"

define CONFIRM_REBUILD
	@echo "This will delete all data and rebuild the database."
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" != "y" ]; then \
		echo "Aborting."; \
		exit 1; \
	fi
endef

db-rebuild:
	$(CONFIRM_REBUILD)
	supabase db reset
	make db-setup-user

# Create superuser for our application
db-setup-user:
	@echo "Creating application user..."
	@docker exec -i supabase_db_pantry_chef_db psql -U postgres -d postgres -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" || true
	@docker exec -i supabase_db_pantry_chef_db psql -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${DB_USER};" || true
	@echo "✅ User created"