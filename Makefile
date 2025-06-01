.PHONY: help install test test-cov lint format check clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync --extra dev

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=custom_components --cov-report=html --cov-report=term --cov-report=xml

coverage: test-cov ## Generate coverage report
	@echo "Opening coverage report..."
	@open htmlcov/index.html || echo "Install 'open' command or manually open htmlcov/index.html"

lint: ## Run linting checks
	uv run ruff check custom_components tests
	uv run mypy custom_components

format: ## Format code
	uv run ruff format custom_components tests

check: format lint test ## Run all checks (format, lint, test)

clean: ## Clean up generated files
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
