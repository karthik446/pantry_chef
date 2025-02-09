# Service-specific Makefile
SERVICE_NAME := recipe-agent-service
IMAGE_TAG := latest
DOCKERFILE := Dockerfile
ROOT_DIR := ../../..

.PHONY: build test-unit
build:
	docker build --no-cache -t recipe-agent-service . 
	docker tag recipe-agent-service:latest kar446/recipe-agent-service:v1.0.0
	docker push kar446/recipe-agent-service:v1.0.0



test-unit: 
		pytest src/tests