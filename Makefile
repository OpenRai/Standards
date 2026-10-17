.DEFAULT_GOAL := help

EDITOR_PORT ?= 8008

.PHONY: help editor noms-vectors

help:
	@echo "Targets:"
	@echo "  editor  Start the local Standards editor"
	@echo "  noms-vectors  Generate independent ORIS-001 conformance fixtures"

editor:
	uv run tools/standards_editor.py --port $(EDITOR_PORT)

noms-vectors:
	python3 scripts/noms/generate_vectors.py
