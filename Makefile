# Makefile for compiling LaTeX learning steps

TOPIC_DIRS := $(wildcard [0-9][0-9]-*)

.PHONY: all clean compile build_pdfs site

all: build_pdfs clean

site:
	python3 scripts/md2html.py

build_pdfs:
	@for dir in $(TOPIC_DIRS); do \
		echo "Building in $$dir..."; \
		cd $$dir; \
		find . -name "*.tex" | while read tex; do \
			texdir=$$(dirname "$$tex"); \
			texfile=$$(basename "$$tex"); \
			cd "$$texdir" && lualatex -interaction=nonstopmode "$$texfile" && cd - > /dev/null; \
		done; \
		cd ..; \
	done

clean:
	@./scripts/clean.sh
