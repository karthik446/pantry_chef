.PHONY: setup run clean test lint format

# Python environment variables
PYTHON := python3
VENV := recipe
VENV_BIN := $(VENV)/bin

# Project variables
MAIN_FILE := main.py

setup: clean
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	$(VENV_BIN)/pip install -r requirements.txt
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
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".DS_Store" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.egg" -delete
	@echo "Cleanup complete!"

test:
	@if [ -d "$(VENV)" ]; then \
		$(VENV_BIN)/python -m pytest tests/; \
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

