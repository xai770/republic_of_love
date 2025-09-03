# ty_learn Task Runner
# Usage: make <target>

.PHONY: help test validate run-prod run-research rollback clean check status

# Default target
help:
	@echo "ty_learn Task Runner"
	@echo ""
	@echo "Available targets:"
	@echo "  test          - Run all tests"
	@echo "  validate      - Run validation suite"
	@echo "  run-prod      - Run production system (V=7|14)"
	@echo "  run-research  - Work on research (V=16)"
	@echo "  rollback      - Rollback production system (V=7|14)"
	@echo "  clean         - Clean temporary files"
	@echo "  check         - Check system health"
	@echo "  status        - Show workspace status"
	@echo ""
	@echo "Examples:"
	@echo "  make test"
	@echo "  make run-prod V=14"
	@echo "  make rollback V=14"
	@echo "  make run-research V=16"

# Testing targets
test:
	@echo "🧪 Running tests..."
	cd tests && python -m pytest -v

validate:
	@echo "✅ Running validation suite..."
	cd validation && python -m pytest -v

# Production targets
run-prod:
	@if [ "$(V)" = "7" ]; then \
		echo "🚀 Running V7 production..."; \
		cd production/v7 && python main.py; \
	elif [ "$(V)" = "14" ]; then \
		echo "🚀 Running V14 production..."; \
		cd production/v14 && python reports.py; \
	else \
		echo "❌ Specify version: make run-prod V=7 or V=14"; \
		exit 1; \
	fi

# Research targets  
run-research:
	@if [ "$(V)" = "16" ]; then \
		echo "🔬 Entering V16 research environment..."; \
		cd experiments/research/v16_development; \
	else \
		echo "❌ Specify version: make run-research V=16"; \
		exit 1; \
	fi

# Rollback targets
rollback:
	@if [ "$(V)" = "7" ]; then \
		echo "🔄 Rolling back V7 to last known good..."; \
		cd production/v7 && git checkout HEAD~1 .; \
		echo "✅ V7 rollback complete"; \
	elif [ "$(V)" = "14" ]; then \
		echo "🔄 Rolling back V14 to last known good..."; \
		cd production/v14 && git checkout HEAD~1 .; \
		echo "✅ V14 rollback complete"; \
	else \
		echo "❌ Specify version: make rollback V=7 or V=14"; \
		exit 1; \
	fi

# Maintenance targets
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.tmp" -delete 2>/dev/null || true
	find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

check:
	@echo "🔍 Checking system health..."
	@echo "📁 Directory structure:"
	@ls -la | grep "^d" | wc -l | xargs echo "  Directories:"
	@echo "🔗 External links:"
	@ls -la | grep "^l" | awk '{print "  " $$9 " -> " $$11}'
	@echo "🐍 Python environment:"
	@python --version 2>/dev/null || echo "  Python not available"
	@echo "✅ Health check complete"

status:
	@echo "📊 ty_learn Workspace Status"
	@echo ""
	@echo "🏗️ Architecture: Clean (2025-08-28)"
	@echo "📁 Structure:"
	@tree -d -L 2 | head -15
	@echo ""
	@echo "🚀 Production Systems:"
	@echo "  V7:  production/v7/  (current, 411s/job)"
	@echo "  V14: production/v14/ (ready, 29.1s/job)"
	@echo ""
	@echo "🔬 Active Research:"
	@echo "  V16: experiments/research/v16_development/"
	@echo ""
	@echo "For detailed info: cat ARCHITECTURE.md"

# CI enforcement target
ci-gate:
	@echo "🚪 CI Gate: Enforcing quality standards..."
	make test
	make validate
	@echo "✅ CI Gate passed - merge approved"
