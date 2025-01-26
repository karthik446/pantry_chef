include .env
export

.PHONY: proto server clean migrate-up migrate-down

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

migrate-up:
	migrate -path internal/platform/db/migrations -database ${DB_URL} up

migrate-down:
	migrate -path internal/platform/db/migrations -database ${DB_URL} down 
