# Project Structure

## Root Directory Layout

```
api/
├── cmd/                    # Application entry points
├── internal/              # Private application code
├── pkg/                   # Public libraries
├── proto/                 # Protocol buffer definitions
├── docs/                  # Documentation
└── migrations/            # Database migrations
```

## Package Organization

### /cmd

- **Purpose**: Contains application entry points
- **Components**:
  - `server/`: Main application server
- **Rationale**: Separates executable build targets from library code

### /internal

- **Purpose**: Private application code
- **Components**:
  - `core/`: Core business logic
    - `auth/`: Authentication/authorization
  - `domain/`: Business entities and interfaces
  - `platform/`: Infrastructure concerns
    - `config/`: Configuration management
    - `db/`: Database connections
    - `logger/`: Logging setup
    - `metrics/`: Metrics collection
  - `server/`: Server implementations
    - `http/`: HTTP handlers
    - `grpc/`: gRPC services
  - `store/`: Data access layer
- **Rationale**: Go's internal package prevents unintended usage

### /platform

- **Purpose**: Cross-cutting infrastructure concerns
- **Components**:
  - `config/`: Configuration management
  - `db/`: Database connections
  - `logger/`: Logging infrastructure
  - `metrics/`: Metrics collection
- **Rationale**: Separates infrastructure from business logic

### /proto

- **Purpose**: Protocol buffer definitions
- **Components**:
  - Service definitions
  - Message types
- **Rationale**: Centralizes API contract definitions

### /migrations

- **Purpose**: Database schema management
- **Components**:
  - SQL migration files
- **Rationale**: Version control for database schema

## Design Principles

1. **Separation of Concerns**: Each package has a single responsibility
2. **Dependency Management**: Clear dependency flow between packages
3. **Encapsulation**: Internal packages for private implementation
4. **Reusability**: Common code in platform packages
5. **Testability**: Clear boundaries for unit testing
