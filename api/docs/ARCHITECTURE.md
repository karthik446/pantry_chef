# Architecture Documentation

## Overview

The Pantry Chef API is built using a clean, layered architecture that emphasizes separation of concerns, maintainability, and testability.

## Architectural Decisions

### 1. Layer Separation

- **HTTP/gRPC Layer** (`/server`): Handles incoming requests, routing, and response formatting
- **Domain Layer** (`/domain`): Contains core business logic and entities
- **Store Layer** (`/store`): Manages data persistence and database interactions
- **Platform Layer** (`/platform`): Houses infrastructure concerns

### 2. Dependency Flow

```
HTTP/gRPC → Domain → Store → Database
     ↓
Platform (cross-cutting concerns)
```

### 3. Key Design Decisions

#### a. Dual Protocol Support

- Supports both HTTP and gRPC protocols
- Shared business logic between protocols
- Protocol-specific handlers and middleware

#### b. Configuration Management

- Environment-based configuration
- Centralized config package
- Strong typing for configuration values

#### c. Database Access

- Connection pooling with pgxpool
- Repository pattern for data access
- Structured error handling

#### d. Error Handling

- Domain-specific error types
- Consistent error responses
- Proper error logging

#### e. Middleware Architecture

- Request/Response logging
- Authentication/Authorization
- Request ID tracking
- Metrics collection

#### f. Health Checking

- Component-based health system
- Readiness vs Liveness checks
- Uptime tracking

#### g. Observability

- Structured logging (Zap)
- Prometheus metrics
- Request tracing

## Future Considerations

1. Caching layer integration
2. Rate limiting
3. API versioning strategy
4. Event sourcing/messaging
5. Service mesh integration
