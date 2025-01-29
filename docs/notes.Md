kubectl get pods -n infrastructure
kubectl get nodes

# Clean everything first

make clean-infra

# Install infrastructure (PostgreSQL + Redis)

make install-infrastructure

# Verify Redis installation

kubectl get pods -n infrastructure
kubectl get svc -n infrastructure

# Get Redis password

make get-redis-password

Here's how to verify Redis installation:

1. **Check Redis pod status**:

```bash
kubectl get pods -n infrastructure | grep redis
```

2. **Test Redis connection**:

```bash
# Port-forward Redis service
kubectl port-forward -n infrastructure svc/redis-master 6379:6379

# In another terminal, test with redis-cli
redis-cli -a $(make get-redis-password)

# Try basic Redis commands
> PING
> SET test "Hello"
> GET test
> exit
```

# Testing RabbitMQ

2. Check the pod logs for any startup issues:

```bash
kubectl logs -n infrastructure $(kubectl get pods -n infrastructure | grep rabbitmq | awk '{print $1}')
```

4. If that doesn't work, let's check the services:

```bash
# List all services to verify the correct service name
kubectl get svc -n infrastructure | grep rabbitmq
```

5. You can also check if the management plugin is enabled:

```bash
# Get into the RabbitMQ pod
kubectl exec -it -n infrastructure $(kubectl get pods -n infrastructure | grep rabbitmq | awk '{print $1}') -- bash

# List enabled plugins
rabbitmq-plugins list
```

# Check if pods are running

kubectl get pods -n monitoring

kubectl logs -n monitoring otel-collector-opentelemetry-collector-8569d495bc-psrvz

kubectl describe pod -n monitoring otel-collector-opentelemetry-collector-8569d495bc-psrvz

Run this command to enable APM auto-instrumentation using the instrumentation file.

kubectl apply -f ./instrumentation.yaml -n newrelic

# Check pod status

kubectl get pods -n default -l app=pantry-chef-api

# Check logs

kubectl logs -n default -l app=pantry-chef-api -c api

kubectl get pods -l app=pantry-chef-api

# Wait for pods to start

kubectl logs -f <pod-name>
