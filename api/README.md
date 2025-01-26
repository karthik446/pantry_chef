# Pantry Chef API

Go implementation of the Pantry Chef backend API. This service provides both HTTP and gRPC endpoints for managing recipes, ingredients, and user pantries.

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)

## Structure

```
api/
├── cmd/              # Application entry points
├── internal/         # Private application code
├── pkg/             # Public packages
├── proto/           # Protocol buffers
├── docs/            # Documentation
└── migrations/      # SQL migrations
```

## Development

### Prerequisites

- Go 1.21+
- PostgreSQL 14+
- Protocol Buffers v3
- Make

### Environment Setup

1. Copy `.env.example` to `.env` and configure:

   ```bash
   cp .env.example .env
   ```

2. Required environment variables:
   ```
   PORT=8000
   SUPABASE_DB_URL=your_db_url
   ```

### Getting Started

1. Install dependencies:

   ```bash
   go mod download
   make dev-deps
   ```

2. Run the development server:

   ```bash
   make run
   ```

3. Test the API:
   ```bash
   curl http://localhost:8000/v1/health
   ```

### Available Endpoints

- Health Check: `GET /v1/health`
- Ingredients:
  - List: `GET /v1/ingredients`
  - Create: `POST /v1/ingredients`
  - Get: `GET /v1/ingredients/{id}`
  - Update: `PUT /v1/ingredients/{id}`
  - Delete: `DELETE /v1/ingredients/{id}`

### Development Commands

- `make run` - Start the development server
- `make build` - Build the binary
- `make test` - Run tests
- `make proto` - Generate protobuf code
- `make lint` - Run linters
- `make mock` - Generate mocks

### Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
