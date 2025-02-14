FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and env file
COPY src/ ./src/
COPY .env .

# Environment
ENV RABBITMQ_HOST=rabbitmq
ENV RABBITMQ_PORT=5672
ENV RABBITMQ_USER=user
ENV RABBITMQ_PASSWORD=rabbitmq

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import pika; pika.BlockingConnection(pika.ConnectionParameters(host='$RABBITMQ_HOST', port=$RABBITMQ_PORT, credentials=pika.PlainCredentials('$RABBITMQ_USER', '$RABBITMQ_PASSWORD')))"

# Execute
CMD ["python", "src/main.py"]