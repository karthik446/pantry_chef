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

check-jq:
	@which jq > /dev/null || (echo "Error: jq is required but not installed. Install with 'brew install jq'" && exit 1)

create-admin: check-jq
	@echo "Creating admin user..."
	@auth_response=`curl -s -X POST '${SUPABASE_URL}/auth/v1/signup' \
		-H "apikey: ${SUPABASE_API_KEY}" \
		-H "Content-Type: application/json" \
		-d '{"email": "skarthikc.dev@gmail.com", "password": "cUcsuv-majtyc-9gejfa", "data": {"role": "admin"}}'` && \
	echo "Auth user created with ID: " && echo $$auth_response | jq -r '.id' && \
	echo "\n✅ Admin user created successfully"

db-reset:
	supabase db reset --db-url="postgresql://postgres:jicqy6-pajqij-micrUg@db.rsztmhzcvbcluhwffzyu.supabase.co:5432/postgres"

remote-db-reset: db-reset create-admin 

hello:
	echo "Hello"

setup-security:
	# Revoke public access
	PGPASSWORD=postgres docker exec -i supabase_db_pantry_chef_db psql -U postgres -d ${DB_NAME} -c "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;"
	# Additional security policies...





