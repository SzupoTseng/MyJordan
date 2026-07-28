.PHONY: help check lint types test assets clean

PY ?= python3
export PYTHONPATH := src

help:      ## 顯示可用目標
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

lint:      ## ruff
	ruff check src tests

types:     ## mypy strict
	mypy src

test:      ## pytest（覆蓋率門檻 85%）
	$(PY) -m pytest --cov=railway_core --cov-report=term-missing --cov-fail-under=85

check: lint types test   ## 全套

assets:    ## 產生列印用資產到 out/
	$(PY) -m railway_core.app assets

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage out
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
