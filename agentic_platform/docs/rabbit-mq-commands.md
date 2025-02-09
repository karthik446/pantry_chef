
### Check queue status and messages
```bash
kubectl exec -n infrastructure rabbitmq-0 -- \
  curl -s -u user:$(kubectl get secret -n infrastructure rabbitmq -o jsonpath='{.data.rabbitmq-password}' | base64 -d) \
  http://localhost:15672/api/queues/%2F/recipe_searches | jq '{messages: .messages, ready: .messages_ready, unacked: .messages_unacknowledged}'
```

### Check pod events
```bash
kubectl describe pod -n default -l app=recipe-agent-service | grep -A 30 "Events"
```

### Get RabbitMQ service IP
```bash
kubectl get svc -n infrastructure rabbitmq
```