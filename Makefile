.PHONY: help install snapshot server test clean

# Use venv python if available, otherwise system python
PYTHON := $(shell if [ -f venv/bin/python ]; then echo venv/bin/python; else echo python; fi)

help:
	@echo "SafeRunner - Automated Bug Fixing Service"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install Python dependencies"
	@echo "  make snapshot   - Create Daytona snapshot"
	@echo "  make server     - Run webhook server"
	@echo "  make test       - Run tests (if available)"
	@echo "  make clean      - Clean up temporary files"

install:
	$(PYTHON) -m pip install -r requirements.txt

snapshot:
	bash scripts/make_snapshot.sh

server:
	$(PYTHON) -m control.server

test:
	pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
