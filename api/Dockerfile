# Build stage
FROM golang:1.23.4-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Install specific version of migrate that's compatible with Go 1.21
RUN go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@v4.17.0

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/bin/server cmd/server/main.go

# Final stage
FROM alpine:3.19

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/bin/server .
COPY --from=builder /app/internal/platform/db/migrations ./migrations
COPY --from=builder /go/bin/migrate /usr/local/bin/migrate

# Create non-root user
RUN adduser -D appuser
USER appuser

EXPOSE 8000

# Use environment variables instead of .env file
ENV PORT=8000 \
    DB_URL="" \
    NODE_ENV="production"

CMD ["./server"] 