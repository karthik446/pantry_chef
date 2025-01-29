.PHONY: dev migrate-up migrate-down seed db-reset down build run test clean k3d-create k3d-delete k3d-start k3d-stop helm-init k3d-clean helm-setup create-infra-ns install-postgres uninstall-postgres get-postgres-password install-infra install-redis uninstall-redis get-redis-password install-rabbitmq uninstall-rabbitmq get-rabbitmq-password verify-persistence install-external-secrets uninstall-external-secrets create-monitoring-ns install-newrelic uninstall-newrelic install-observability create-istio-ns install-istio-base install-istiod install-istio-ingress enable-istio-injection uninstall-istio build-api install-api uninstall-api create-db k8s-migrate clean-images deploy-all clean-all deploy-seed api-forward forward-all

# =============================================================================
# Base Variables
# =============================================================================
# Database connection string (for both local and container use)
DB_URL ?= postgresql://postgres:postgres@localhost:5432/pantry_chef?sslmode=disable

# Build variables
BINARY_NAME=pantry-chef-api
BUILD_DIR=build

# Kubernetes cluster name
CLUSTER_NAME=pantry-chef

# Infrastructure namespace
INFRA_NAMESPACE=infrastructure

# =============================================================================
# K3D Cluster Management
# =============================================================================
# Create k3d cluster with registry
k3d-create:
	k3d cluster create $(CLUSTER_NAME) \
		--api-port 6550 \
		--port "8080:80@loadbalancer" \
		--registry-create k3d-pantry-registry.localhost:5050 \
		--registry-config "$(PWD)/registries.yaml" \
		--servers 1 \
		--agents 2 \
		--image rancher/k3s:latest \
		--k3s-arg "--disable=traefik@server:0" \
		--volume "$(PWD)/manifests:/var/lib/rancher/k3s/server/manifests@server:0"

# Delete k3d cluster
k3d-delete:
	k3d cluster delete $(CLUSTER_NAME)

# Stop k3d cluster
k3d-stop:
	k3d cluster stop $(CLUSTER_NAME)

# Start k3d cluster
k3d-start:
	k3d cluster start $(CLUSTER_NAME)

# Clean up any existing k3d resources
k3d-clean:
	k3d cluster delete $(CLUSTER_NAME) || true
	docker rm -f pantry-registry || true
	docker network prune -f

# =============================================================================
# Helm Setup and Management
# =============================================================================
# Initialize Helm repos
helm-init:
	helm repo add newrelic https://helm-charts.newrelic.com
	helm repo add bitnami https://charts.bitnami.com/bitnami
	helm repo add external-secrets https://charts.external-secrets.io
	helm repo add istio https://istio-release.storage.googleapis.com/charts
	helm repo update

# Create Helm directory structure if it doesn't exist
helm-setup:
	mkdir -p helm/charts/api/templates
	mkdir -p helm/charts/api/values
	helm create helm/charts/api

# =============================================================================
# Infrastructure Management
# =============================================================================
# Create infrastructure namespace
create-infra-ns:
	kubectl create namespace $(INFRA_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -

# Install PostgreSQL with seed data
install-postgres:
	helm upgrade --install postgres bitnami/postgresql \
		--namespace $(INFRA_NAMESPACE) \
		--create-namespace \
		--values helm/values/postgres-values.yaml

# Install Redis
install-redis:
	helm upgrade --install redis bitnami/redis \
		--namespace $(INFRA_NAMESPACE) \
		--values helm/values/redis-values.yaml

# Install RabbitMQ
install-rabbitmq:
	helm upgrade --install rabbitmq bitnami/rabbitmq \
		--namespace $(INFRA_NAMESPACE) \
		--values helm/values/rabbitmq-values.yaml

# Install external-secrets operator
install-external-secrets:
	helm upgrade --install external-secrets external-secrets/external-secrets \
		--namespace $(INFRA_NAMESPACE) \
		--values helm/values/external-secrets-values.yaml

# Install core infrastructure
install-infra: helm-init create-infra-ns install-external-secrets install-postgres install-redis install-rabbitmq
	@echo "Core infrastructure installed"
	@echo "Run 'make get-postgres-password' to get the PostgreSQL password"
	@echo "Run 'make get-redis-password' to get the Redis password"
	@echo "Run 'make get-rabbitmq-password' to get the RabbitMQ password"

# =============================================================================
# Infrastructure Cleanup
# =============================================================================
# Uninstall PostgreSQL
uninstall-postgres:
	helm uninstall postgres --namespace $(INFRA_NAMESPACE)
	kubectl delete pvc -l app.kubernetes.io/name=postgresql -n $(INFRA_NAMESPACE)

# Uninstall Redis
uninstall-redis:
	helm uninstall redis --namespace $(INFRA_NAMESPACE)
	kubectl delete pvc -l app.kubernetes.io/name=redis -n $(INFRA_NAMESPACE)

# Uninstall RabbitMQ
uninstall-rabbitmq:
	helm uninstall rabbitmq --namespace $(INFRA_NAMESPACE)
	kubectl delete pvc -l app.kubernetes.io/name=rabbitmq -n $(INFRA_NAMESPACE)

# Uninstall external-secrets operator
uninstall-external-secrets:
	helm uninstall external-secrets --namespace $(INFRA_NAMESPACE)

# Clean infrastructure
clean-infra:
	helm uninstall postgres --namespace $(INFRA_NAMESPACE) || true
	helm uninstall redis --namespace $(INFRA_NAMESPACE) || true
	helm uninstall rabbitmq --namespace $(INFRA_NAMESPACE) || true
	helm uninstall external-secrets --namespace $(INFRA_NAMESPACE) || true
	kubectl delete pvc -l app.kubernetes.io/name=postgresql -n $(INFRA_NAMESPACE) || true
	kubectl delete pvc -l app.kubernetes.io/name=redis -n $(INFRA_NAMESPACE) || true
	kubectl delete pvc -l app.kubernetes.io/name=rabbitmq -n $(INFRA_NAMESPACE) || true
	kubectl delete namespace $(INFRA_NAMESPACE) || true

# =============================================================================
# Infrastructure Credentials
# =============================================================================
# Get PostgreSQL password
get-postgres-password:
	@kubectl get secret --namespace $(INFRA_NAMESPACE) postgres-postgresql -o jsonpath="{.data.postgres-password}" | base64 --decode | tr -d '\n'

# Get Redis password
get-redis-password:
	@kubectl get secret --namespace $(INFRA_NAMESPACE) redis -o jsonpath="{.data.redis-password}" | base64 --decode | tr -d '\n'

# Get RabbitMQ password
get-rabbitmq-password:
	@kubectl get secret --namespace $(INFRA_NAMESPACE) rabbitmq -o jsonpath="{.data.rabbitmq-password}" | base64 --decode | tr -d '\n'

# =============================================================================
# Monitoring and Observability
# =============================================================================
# Create monitoring namespace
create-monitoring-ns:
	kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

# Install New Relic observability stack with reduced data ingestion
install-newrelic:
	helm upgrade --install newrelic-bundle newrelic/nri-bundle \
		--namespace newrelic \
		--create-namespace \
		--set global.licenseKey=b5028d26c93bb0da0ef619d9e071f7abFFFFNRAL \
		--set global.cluster=$(CLUSTER_NAME) \
		--set global.lowDataMode=true \
		--set kube-state-metrics.image.tag=v2.13.0 \
		--set kube-state-metrics.enabled=false \
		--set kubeEvents.enabled=true \
		--set newrelic-prometheus-agent.enabled=false \
		--set newrelic-prometheus-agent.lowDataMode=true \
		--set newrelic-prometheus-agent.config.kubernetes.integrations_filter.enabled=false \
		--set k8s-agents-operator.enabled=true \
		--set logging.enabled=true \
		--set newrelic-logging.lowDataMode=true

# Install monitoring stack
install-monitoring: clean-monitoring create-monitoring-ns install-newrelic
	@echo "New Relic observability stack installed"
	@echo "Access your data at: https://one.newrelic.com"

# Clean monitoring namespace and CRDs
clean-monitoring:
	helm uninstall newrelic-bundle --namespace monitoring || true
	helm uninstall newrelic-bundle --namespace newrelic || true
	kubectl delete namespace monitoring || true
	kubectl delete namespace newrelic || true
	kubectl delete crd instrumentations.newrelic.com || true
	kubectl delete crd newrelicapmconfigs.newrelic.com || true
	kubectl delete crd newrelicrequests.newrelic.com || true
	kubectl delete crd alerts.newrelic.com || true

# =============================================================================
# Service Mesh (Istio)
# =============================================================================
# Create istio-system namespace
create-istio-ns:
	kubectl create namespace istio-system --dry-run=client -o yaml | kubectl apply -f -

# Install Istio base
install-istio-base:
	helm upgrade --install istio-base istio/base \
		--namespace istio-system \
		--create-namespace \
		--wait

# Install Istio control plane
install-istiod:
	helm upgrade --install istiod istio/istiod \
		--namespace istio-system \
		--wait

# Install Istio ingress gateway
install-istio-ingress:
	helm upgrade --install istio-ingress istio/gateway \
		--namespace istio-system \
		--wait

# Enable Istio injection for default namespace
enable-istio-injection:
	kubectl label namespace default istio-injection=enabled --overwrite

# Install complete Istio stack
install-istio: create-istio-ns install-istio-base install-istiod install-istio-ingress enable-istio-injection
	@echo "Istio service mesh installed"
	@echo "Injection enabled for default namespace"

# Uninstall Istio components
clean-istio:
	helm uninstall istio-ingress --namespace istio-system || true
	helm uninstall istiod --namespace istio-system || true
	helm uninstall istio-base --namespace istio-system || true
	kubectl delete namespace istio-system || true

# =============================================================================
# API Deployment and Management
# =============================================================================
# Build and push API image with clean first
build-api: clean-images
	@echo "Building and pushing API image..."
	docker build -t kar446/pantry-chef-api:latest ./api
	docker push kar446/pantry-chef-api:latest
	@echo "Image pushed successfully"

# Install API chart
install-api: build-api
	helm upgrade --install api ./helm/charts/api \
		--values helm/values/api-values.yaml \
		--namespace default \
		--create-namespace

# Uninstall API chart
uninstall-api:
	helm uninstall api --namespace default || true

# =============================================================================
# Database Operations
# =============================================================================
# Database setup sequence
setup-db: install-postgres create-db k8s-migrate

# Create database in PostgreSQL if not exists
create-db:
	@echo "Checking database..."
	@PG_PASSWORD=$$(kubectl get secret --namespace $(INFRA_NAMESPACE) postgres-postgresql -o jsonpath="{.data.postgres-password}" | base64 --decode); \
	if ! kubectl exec -n $(INFRA_NAMESPACE) postgres-postgresql-0 -- /bin/bash -c "PGPASSWORD=$$PG_PASSWORD psql -U postgres -lqt | cut -d \| -f 1 | grep -qw pantry_chef"; then \
		echo "Creating database..."; \
		kubectl exec -n $(INFRA_NAMESPACE) postgres-postgresql-0 -- /bin/bash -c "PGPASSWORD=$$PG_PASSWORD psql -U postgres -c 'CREATE DATABASE pantry_chef;'"; \
	else \
		echo "Database already exists, skipping..."; \
	fi

# Run database migrations in Kubernetes environment
# This command:
# 1. Waits for the API pod to be ready
# 2. Gets PostgreSQL password from K8s secret
# 3. Constructs database URL with the password
# 4. Executes migrate command inside the API pod
k8s-migrate:
	# Wait until API pod is ready to accept commands
	@echo "Waiting for API pod to be ready..."
	@kubectl wait --for=condition=ready pod -l app=pantry-chef-api -n default --timeout=60s
	
	@echo "Running migrations..."
	# Get PostgreSQL password from Kubernetes secret and construct DB URL
	@PG_PASSWORD=$$(kubectl get secret --namespace $(INFRA_NAMESPACE) postgres-postgresql -o jsonpath="{.data.postgres-password}" | base64 --decode); \
	DB_URL="postgresql://postgres:$$PG_PASSWORD@postgres-postgresql.infrastructure:5432/pantry_chef?sslmode=disable"; \
	# Execute migrate command inside the API pod using the constructed DB URL
	kubectl exec -n default $$(kubectl get pod -l app=pantry-chef-api -o jsonpath='{.items[0].metadata.name}') -- \
		migrate -path /app/migrations -database "$$DB_URL" up

# Run migrations (local)
migrate-up:
	migrate -path api/internal/platform/db/migrations -database "$(DB_URL)" up

# Reverse migrations (local)
migrate-down:
	migrate -path api/internal/platform/db/migrations -database "$(DB_URL)" down

# =============================================================================
# Local Development
# =============================================================================
# Start API and database
dev:
	docker compose -f docker/compose/docker-compose.base.yml up -d --build

# Stop and remove all containers
down:
	docker compose -f docker/compose/docker-compose.base.yml down -v

# Initialize everything (first time setup)
init: dev migrate-up

# =============================================================================
# Port Forwarding
# =============================================================================
# Port forward API service to localhost
api-forward:
	kubectl port-forward svc/api 8000:8000 9000:9000

# Port forward both API and PostgreSQL
forward-all:
	kubectl port-forward svc/api 8000:8000 9000:9000 & \
	kubectl port-forward -n infrastructure svc/postgres-postgresql 5432:5432

# =============================================================================
# Deployment and Cleanup
# =============================================================================
# Deploy all components without seed data
deploy-all: install-infra verify-infra install-istio deploy-api
	@echo "\n=== Deployment Complete ==="
	@echo "To verify infrastructure: make verify-infra"
	@echo "To apply seed data: make verify-and-seed"

# Clean everything
clean-all: uninstall-api clean-images
	@echo "Cleaned up API and images"

# Clean up Docker images
clean-images:
	docker rmi kar446/pantry-chef-api:latest || true
	docker system prune -f

# =============================================================================
# Verification and Testing
# =============================================================================
# Verify all infrastructure components are ready
verify-infra:
	@echo "\n=== Verifying PostgreSQL ==="
	@kubectl -n $(INFRA_NAMESPACE) rollout status statefulset postgres-postgresql --timeout=600s
	@echo "\n=== Verifying Redis ==="
	@kubectl -n $(INFRA_NAMESPACE) rollout status statefulset redis-master --timeout=300s
	@echo "\n=== Verifying RabbitMQ ==="
	@kubectl -n $(INFRA_NAMESPACE) rollout status statefulset rabbitmq --timeout=300s
	@echo "\n=== All infrastructure components are ready ==="

# Verify data persistence
verify-persistence:
	@echo "Testing PostgreSQL persistence..."
	@echo "Creating test database..."
	kubectl exec -n $(INFRA_NAMESPACE) postgres-postgresql-0 -- /bin/bash -c 'PGPASSWORD=$(shell make get-postgres-password) psql -U postgres -c "CREATE DATABASE persistence_test;"'
	@echo "Restarting PostgreSQL pod..."
	kubectl delete pod -n $(INFRA_NAMESPACE) postgres-postgresql-0
	@echo "Waiting for PostgreSQL to restart..."
	sleep 10
	@echo "Verifying database exists..."
	kubectl exec -n $(INFRA_NAMESPACE) postgres-postgresql-0 -- /bin/bash -c 'PGPASSWORD=$(shell make get-postgres-password) psql -U postgres -c "\l"' | grep persistence_test

	@echo "\nTesting Redis persistence..."
	@echo "Setting test key..."
	kubectl exec -n $(INFRA_NAMESPACE) redis-master-0 -- redis-cli -a $(shell make get-redis-password) SET persistence_test "working"
	@echo "Restarting Redis pod..."
	kubectl delete pod -n $(INFRA_NAMESPACE) redis-master-0
	@echo "Waiting for Redis to restart..."
	sleep 10
	@echo "Verifying key exists..."
	kubectl exec -n $(INFRA_NAMESPACE) redis-master-0 -- redis-cli -a $(shell make get-redis-password) GET persistence_test

	@echo "\nTesting RabbitMQ persistence..."
	@echo "Creating test queue..."
	kubectl exec -n $(INFRA_NAMESPACE) rabbitmq-0 -- rabbitmqctl add_vhost test_vhost
	@echo "Restarting RabbitMQ pod..."
	kubectl delete pod -n $(INFRA_NAMESPACE) rabbitmq-0
	@echo "Waiting for RabbitMQ to restart..."
	sleep 20
	@echo "Verifying vhost exists..."
	kubectl exec -n $(INFRA_NAMESPACE) rabbitmq-0 -- rabbitmqctl list_vhosts | grep test_vhost

	@echo "\nAll persistence tests completed!"




	