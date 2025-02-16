.PHONY: dev migrate-up migrate-down seed db-reset down build run test clean k3d-create k3d-delete k3d-start k3d-stop helm-init k3d-clean helm-setup create-infra-ns install-postgres uninstall-postgres get-postgres-password install-infra install-redis uninstall-redis get-redis-password create-monitoring-ns install-newrelic uninstall-newrelic install-observability  build-api install-api uninstall-api create-db k8s-migrate clean-images deploy-all clean-all deploy-seed api-forward forward-all verify-rabbitmq-dns create-pantry-chef delete-pantry-chef

# =============================================================================
# Base Variables
# =============================================================================
# Database connection string (for both local and container use)
DB_URL ?= postgresql://postgres:postgres@localhost:5432/pantry_chef?sslmode=disable

# Build variables
BINARY_NAME=pantry-chef-api
BUILD_DIR=build

# Kubernetes cluster name
CLUSTER_NAME=agentic-platform

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

	helm repo update



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



# Install external-secrets operator
install-external-secrets:
	helm upgrade --install external-secrets external-secrets/external-secrets \
		--namespace $(INFRA_NAMESPACE) \
		--values helm/values/external-secrets-values.yaml

# Install RabbitMQ
install-rabbitmq:
	helm upgrade --install rabbitmq bitnami/rabbitmq \
		--namespace $(INFRA_NAMESPACE) \
		--values helm/values/rabbitmq-values.yaml

# Install core infrastructure
install-infra: helm-init create-infra-ns install-external-secrets install-postgres install-redis install-rabbitmq
	@echo "Core infrastructure installed"
	@echo "Run 'make get-postgres-password' to get the PostgreSQL password"
	@echo "Run 'make get-redis-password' to get the Redis password"

create-queues:
	kubectl exec -n infrastructure $$(kubectl get pod -n infrastructure -l app.kubernetes.io/name=rabbitmq -o jsonpath='{.items[0].metadata.name}') -- \
	sh -c "curl -X PUT -u user:rabbitmq http://localhost:15672/api/queues/%2f/workflow_commands -H 'content-type:application/json' -d '{\"durable\":true, \"arguments\": {\"x-queue-type\": \"quorum\"}}'"

check-queue-messages:
	kubectl exec -n infrastructure $$(kubectl get pod -n infrastructure -l app.kubernetes.io/name=rabbitmq -o jsonpath='{.items[0].metadata.name}') -- \
		curl -s -u user:rabbitmq http://localhost:15672/api/queues/%2F/recipe_searches | jq '{messages: .messages, ready: .messages_ready, unacked: .messages_unacknowledged}'

create-workflow-queue:
	kubectl exec -n infrastructure $$(kubectl get pod -n infrastructure -l app.kubernetes.io/name=rabbitmq -o jsonpath='{.items[0].metadata.name}') -- \
	  sh -c "curl -X PUT -u user:rabbitmq http://localhost:15672/api/queues/%2f/workflow_queue -H 'content-type:application/json' -d '{\"durable\":true, \"arguments\": {\"x-queue-type\": \"quorum\", \"x-max-length\": 10000, \"x-max-length-bytes\": 104857600, \"x-overflow\": \"reject-publish\"}}'"
	kubectl exec -n infrastructure $$(kubectl get pod -n infrastructure -l app.kubernetes.io/name=rabbitmq -o jsonpath='{.items[0].metadata.name}') -- \
  curl -s -u user:rabbitmq http://localhost:15672/api/queues/%2F/workflow_queue | jq '{messages: .messages, ready: .messages_ready, unacked: .messages_unacknowledged}'

send-test-message:
	kubectl exec -n infrastructure $$(kubectl get pod -n infrastructure -l app.kubernetes.io/name=rabbitmq -o jsonpath='{.items[0].metadata.name}') -- \
	  rabbitmqctl publish exchange=workflow_commands routing_key=workflow_commands payload='{"message": "Test message from make command"}'
	  
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
# API Deployment and Management
# =============================================================================
# Build and push API image with clean first
build-api: clean-images
	@echo "Building and pushing API image..."
	docker build -t kar446/pantry-chef-api:latest ./api
	docker push kar446/pantry-chef-api:latest
	@echo "Image pushed successfully"

# Install API chart
install-pantry-chef: build-api
	helm upgrade --install pantry-chef-api ./helm/charts/pantry-chef-api \
		--set secrets.enabled=false \
		--namespace default \
		--create-namespace

redeploy-api: install-pantry-chef 
	kubectl rollout restart deployment pantry-chef-api -n default

api-logs:
	kubectl logs -f deployment/pantry-chef-api -n default

# Uninstall API chart
uninstall-api:
	helm uninstall pantry-chef-api --namespace default || true

# =============================================================================
# Agent Management
# =============================================================================
# Build and push recipe agent image


# Deploy recipe agent to cluster
install-recipe-agent-service: build-recipe-agent-service
	helm upgrade --install recipe-agent-service ./helm/charts/recipe-agent-service \
		--set rabbitmq.url=amqp://user:rabbitmq@rabbitmq.$(INFRA_NAMESPACE).svc.cluster.local:5672 \
		--namespace default

build-recipe-agent-service:
	cd agentic_platform/services/recipes && \
	docker build --no-cache -t recipe-agent-service . && \
	docker tag recipe-agent-service:latest kar446/recipe-agent-service:v1.0.0 && \
	docker push kar446/recipe-agent-service:v1.0.0

redeploy-as: install-recipe-agent-service
		kubectl rollout restart deployment recipe-agent-service -n default
	

# Run recipe agent locally (for testing)
run-recipe-agent-service-local:
	RABBITMQ_URL=amqp://localhost:5672 python -m agentic_platform.services.recipes.main

# Tail recipe agent logs
as-logs:
	kubectl logs -f deployment/recipe-agent-service -n default

# Uninstall recipe agent
uninstall-recipe-agent-service:
	helm uninstall recipe-agent-service --namespace default || true

# Get RabbitMQ password
get-rabbitmq-password:
	@kubectl get secret --namespace $(INFRA_NAMESPACE) rabbitmq -o jsonpath="{.data.rabbitmq-password}" | base64 --decode | tr -d '\n'

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

forward-all:
	kubectl port-forward svc/pantry-chef-api 8000:8000 & \
	kubectl port-forward -n infrastructure svc/postgres-postgresql 5432:5432 & \
	kubectl port-forward --insecure-skip-tls-verify -n infrastructure svc/rabbitmq 5672:5672 & \
	kubectl port-forward --insecure-skip-tls-verify -n infrastructure svc/rabbitmq 15672:15672 & \
	kubectl port-forward -n infrastructure svc/redis-master 6379:6379

# =============================================================================
# Deployment and Cleanup
# =============================================================================
# Deploy all components without seed data
deploy-all: install-infra verify-infra 
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

	@echo "\nAll persistence tests completed!"

# Verify RabbitMQ DNS resolution
verify-rabbitmq-dns:
	@echo "Verifying RabbitMQ DNS resolution..."
	@kubectl run -it --rm --restart=Never dns-test \
		--image=busybox:1.28 \
		-- nslookup rabbitmq.infrastructure.svc.cluster.local

# =============================================================================
# Production Deployment
# =============================================================================
# Create complete Pantry Chef deployment
create-pantry-chef: k3d-create helm-init create-infra-ns install-infra verify-infra create-monitoring-ns install-monitoring install-pantry-chef install-recipe-agent-service create-workflow-queue
	@echo "\n=== Pantry Chef Deployment Complete ==="
	@echo "To verify infrastructure: make verify-infra"
	@echo "To get credentials:"
	@echo "  PostgreSQL: make get-postgres-password"
	@echo "  Redis: make get-redis-password"
	@echo "  RabbitMQ: make get-rabbitmq-password"
	@echo "To forward ports: make forward-all"

# Delete complete Pantry Chef deployment
delete-pantry-chef: uninstall-pantry-chef uninstall-recipe-agent-service clean-monitoring clean-infra k3d-delete clean-images
	@echo "\n=== Pantry Chef Deletion Complete ==="
	@echo "All components have been removed"
	@echo "To completely reset, you may also want to run: docker system prune -a"





	