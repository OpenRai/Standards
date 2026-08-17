.DEFAULT_GOAL := help

EDITOR_PORT ?= 8008

.PHONY: help editor

help:
	@echo "Targets:"
	@echo "  editor  Start the local Standards editor"

editor:
	uv run tools/standards_editor.py --port $(EDITOR_PORT)
