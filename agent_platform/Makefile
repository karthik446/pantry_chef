.PHONY: setup run clean test lint format test-all test-unit test-integration test-coverage create-test-dirs

# Python environment variables
PYTHON := python3
VENV := recipe
VENV_BIN := $(VENV)/bin

# Project variables
MAIN_FILE := main.py

# Testing configuration
TEST_DIR := tests
UNIT_TEST_DIR := $(TEST_DIR)/unit
INTEGRATION_TEST_DIR := $(TEST_DIR)/integration
COV_THRESHOLD := 90



install: 
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	$(VENV_BIN)/pip install -r requirements.txt
	$(VENV_BIN)/pip install -e .

	@echo "Setup complete! Activate the environment with: source recipe/bin/activate"
	
run:
	@if [ -d "$(VENV)" ]; then \
		$(VENV_BIN)/python $(MAIN_FILE); \
	else \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi

clean:
	@echo "Cleaning up..."
	

test: test-unit test-integration

test-unit:
	@if [ -d "$(VENV)" ]; then \
		$(VENV_BIN)/pytest $(UNIT_TEST_DIR) -v --cov=agent_platform --cov-report=term-missing; \
	else \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi

test-integration:
	@if [ -d "$(VENV)" ]; then \
		$(VENV_BIN)/pytest $(INTEGRATION_TEST_DIR) -v --cov=agent_platform --cov-append; \
	else \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi

test-coverage:
	@if [ -d "$(VENV)" ]; then \
		$(VENV_BIN)/pytest --cov=agent_platform --cov-report=html --cov-fail-under=$(COV_THRESHOLD); \
	else \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi

lint:
	@if [ -d "$(VENV)" ]; then \
		$(VENV_BIN)/ruff check .; \
	else \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi

format:
	@if [ -d "$(VENV)" ]; then \
		$(VENV_BIN)/ruff format .; \
	else \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi



