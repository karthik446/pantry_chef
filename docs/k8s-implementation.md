# Kubernetes Implementation with Helm

## Overview

This document details our complete Kubernetes setup using Helm charts, focusing on local development with k3d. Our infrastructure includes PostgreSQL, Redis, RabbitMQ, New Relic monitoring, and Istio service mesh, all managed through Helm charts.

## Prerequisites

- Docker Desktop
- kubectl
- helm
- k3d
- make

## Complete Setup Process

### 1. Initial Cluster Setup

First, we need to create our k3d cluster and initialize Helm repositories:

```bash
# Clean up any existing k3d resources
make k3d-clean

# Create new k3d cluster with registry
make k3d-create

# Initialize all required Helm repositories
make helm-init

# Create basic Helm chart structure
make helm-setup
```

### 2. Infrastructure Namespace and Core Components

We keep all infrastructure components in a dedicated namespace:

```bash
# Create infrastructure namespace
make create-infra-ns

# Install complete infrastructure stack
make install-infra
```

This installs:

- PostgreSQL (Bitnami chart)
- Redis (Bitnami chart)
- RabbitMQ (Bitnami chart)
- External Secrets Operator

### 3. Verify Infrastructure

After installation, verify all components are running:

```bash
# Verify all infrastructure components
make verify-infra

# Test data persistence
make verify-persistence
```

### 4. Get Infrastructure Credentials

Store these for later use:

```bash
# Get PostgreSQL password
PG_PASSWORD=$(make get-postgres-password)

# Get Redis password
REDIS_PASSWORD=$(make get-redis-password)

# Get RabbitMQ password
RABBITMQ_PASSWORD=$(make get-rabbitmq-password)
```

### 5. Observability Stack

Set up monitoring and observability:

```bash
# Create monitoring namespace
make create-monitoring-ns

# Install New Relic bundle
make install-newrelic

# Install complete observability stack
make install-observability
```

### 6. Service Mesh (Istio)

Install and configure Istio:

```bash
# Create Istio namespace
make create-istio-ns

# Install complete Istio stack
make install-istio
```

This includes:

- Istio base
- Istiod (control plane)
- Istio ingress gateway
- Automatic sidecar injection for default namespace

### 7. Application Deployment

Deploy the API service:

```bash
# Build and push API image
make build-api

# Install API chart
make install-api

# Setup database and run migrations
make setup-db

# Deploy seed data (if needed)
make deploy-seed
```

### 8. Verify Deployment

Check if everything is running correctly:

```bash
# Port forward API service
make api-forward

# Port forward all services (API, PostgreSQL)
make forward-all
```

## Helm Charts Structure

### 1. API Chart (Custom)

Location: `helm/charts/api/`

```yaml
api/
├── Chart.yaml              # Chart metadata
├── values.yaml            # Default values
└── templates/
    ├── deployment.yaml    # API pod configuration
    ├── service.yaml       # Service definition
    ├── configmap.yaml     # Configuration
    ├── secrets.yaml       # Secrets management
    ├── gateway.yaml       # Istio gateway
    └── virtualservice.yaml # Istio routing
```

### 2. Infrastructure Charts (Bitnami)

We use the following Bitnami charts with custom values:

#### PostgreSQL

```yaml
# helm/values/postgres-values.yaml
postgresql:
  auth:
    username: postgres
    database: pantry_chef
  primary:
    persistence:
      size: 1Gi
  metrics:
    enabled: true
```

#### Redis

```yaml
# helm/values/redis-values.yaml
redis:
  architecture: standalone
  auth:
    enabled: true
  master:
    persistence:
      size: 1Gi
  metrics:
    enabled: true
```

#### RabbitMQ

```yaml
# helm/values/rabbitmq-values.yaml
rabbitmq:
  auth:
    username: user
  persistence:
    size: 1Gi
  metrics:
    enabled: true
  plugins: "rabbitmq_management rabbitmq_prometheus"
```

## Maintenance Operations

### Scaling

```bash
# Scale API replicas
kubectl scale deployment api --replicas=3
```

### Updates and Upgrades

```bash
# Update API deployment
make install-api

# Update infrastructure components
make install-infra
```

### Monitoring and Debugging

#### View Logs

```bash
# API logs
kubectl logs -l app=pantry-chef-api -f

# PostgreSQL logs
kubectl logs -n infrastructure -l app.kubernetes.io/name=postgresql -f

# Redis logs
kubectl logs -n infrastructure -l app.kubernetes.io/name=redis -f

# RabbitMQ logs
kubectl logs -n infrastructure -l app.kubernetes.io/name=rabbitmq -f
```

#### Debug Connections

```bash
# Port forward services
make forward-all

# Test database connection
PGPASSWORD=$PG_PASSWORD psql -h localhost -U postgres -d pantry_chef

# Test Redis connection
redis-cli -h localhost -p 6379 -a $REDIS_PASSWORD

# Access RabbitMQ management UI
# Forward port 15672 and access http://localhost:15672
```

### Cleanup Operations

#### Partial Cleanup

```bash
# Remove API only
make uninstall-api

# Clean up infrastructure
make clean-infra
```

#### Complete Cleanup

```bash
# Remove everything and delete cluster
make clean-all
make k3d-delete
```

## Troubleshooting Guide

### Common Issues

1. **Database Connection Issues**

```bash
# Verify PostgreSQL pod is running
kubectl get pods -n infrastructure -l app.kubernetes.io/name=postgresql

# Check PostgreSQL logs
kubectl logs -n infrastructure -l app.kubernetes.io/name=postgresql -f

# Verify secrets exist
kubectl get secrets -n default
```

2. **API Issues**

```bash
# Check API pod status
kubectl get pods -l app=pantry-chef-api

# View API logs
kubectl logs -l app=pantry-chef-api -f

# Describe API pod for events
kubectl describe pod -l app=pantry-chef-api
```

3. **Infrastructure Issues**

```bash
# Check all infrastructure pods
kubectl get pods -n infrastructure

# Verify persistent volumes
kubectl get pv,pvc -n infrastructure

# Check infrastructure services
kubectl get services -n infrastructure
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Infrastructure health
make verify-infra
```

## Monitoring and Metrics

### New Relic Integration

Our setup includes comprehensive monitoring through New Relic:

1. **Kubernetes Monitoring**

   - Cluster metrics
   - Pod metrics
   - Node metrics

2. **Application Monitoring**

   - Request traces
   - Error tracking
   - Performance metrics

3. **Infrastructure Monitoring**
   - Resource usage
   - Network metrics
   - Storage metrics

Access all metrics through the New Relic dashboard.

## Best Practices

1. **Always use make commands** for consistent operations
2. **Check logs in New Relic** for comprehensive monitoring
3. **Use port forwarding** for local development
4. **Verify infrastructure** before deploying applications
5. **Keep values files updated** with latest configurations

## Reference Commands

### Quick Start

```bash
# Complete setup from scratch
make k3d-clean && \
make k3d-create && \
make helm-init && \
make install-infra && \
make install-observability && \
make install-istio && \
make install-api && \
make setup-db
```

### Daily Development

```bash
# Start development environment
make k3d-start
make forward-all

# Stop development environment
make k3d-stop
```

# Complete rebuild of cluster

# 1. Clean everything and delete the cluster

make clean-all # Clean up API and Docker images
make clean-infra # Clean up all infrastructure components
make clean-istio # Clean up Istio components
make clean-monitoring # Clean up monitoring components
make k3d-delete # Delete the k3d cluster completely

# 2. Create new cluster and setup Helm

make k3d-create # Create new k3d cluster with registry
make helm-init # Initialize Helm repositories

# 3. Setup infrastructure

make install-infra # Install PostgreSQL, Redis, RabbitMQ, and External Secrets
make verify-infra # Verify infrastructure is running correctly
make verify-persistence # Verify data persistence is working

# 4. Setup monitoring

make install-monitoring # Install New Relic monitoring stack

# 5. Setup service mesh

make install-istio # Install complete Istio stack

# 6. Deploy application

make install-api # Build and push API image & Install API using Helm
make setup-db # Setup database and run migrations

# 7. Setup port forwarding for local access

make forward-all # Port forward API and PostgreSQL services
