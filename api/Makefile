include .env
export

.PHONY: proto server clean

# Generate proto files
proto:
	protoc --go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		proto/health.proto

# Run the server
server:
	go run cmd/server/main.go

# Build the server
build:
	go build -o bin/server cmd/server/main.go

# Clean generated files and binaries
clean:
	rm -f proto/*.pb.go
	rm -rf bin/

# Install dependencies
deps:
	go mod tidy

# Default target
all: proto deps build 


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