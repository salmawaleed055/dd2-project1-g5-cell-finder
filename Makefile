# DD2 Project 1, Option 2: Finding Cells Worth Adding
# CSCE 3304 Digital Design II - Fall 2026
# Required Makefile targets according to Overview Section 5.1

SHELL := /bin/bash
PDK_ROOT ?= $(HOME)/.ciel
GIVEN    ?= ../given
IN       ?=

PYTHON ?= python3

.PHONY: setup check test all demo clean help

setup:            ## environment, and links to the PDK and the given files
	@mkdir -p build/aigs results/aigs libs ai report tests/broken
	@if [ ! -d "given" ]; then \
		if [ -d "../given" ]; then \
			ln -sfn ../given given; \
		elif [ -d "../DD2_Project1_student_pack/given" ]; then \
			ln -sfn ../DD2_Project1_student_pack/given given; \
		elif [ -d "./given" ]; then \
			echo "given/ directory already present locally"; \
		fi; \
	fi
	@if [ -d "$(PDK_ROOT)/sky130A" ]; then \
		ln -sfn $(PDK_ROOT)/sky130A pdk; \
	fi
	@echo "Setup complete. Workspace configured."

check:            ## tool versions, PDK, and library validation
	@$(PYTHON) src/runner.py check

test:             ## run every test, including the broken cases in tests/broken/
	@echo "=== Running Test Suite: Unit Tests ==="
	$(PYTHON) tests/test_aig.py
	$(PYTHON) tests/test_cuts.py
	$(PYTHON) tests/test_redundancy.py
	@echo "=== Running Test Suite: Deliberately Broken Cases ==="
	$(PYTHON) tests/broken/test_broken_cut_tt.py
	$(PYTHON) tests/broken/test_broken_redundancy.py
	$(PYTHON) tests/broken/test_broken_liberty.py
	$(PYTHON) tests/broken/test_broken_cec.py
	@echo "All tests passed successfully (including all broken-case checks)."

all:              ## run the whole Milestone 1 flow
	@echo "=== Step 1: Synthesizing Designs to AIG and Restructuring with ABC ==="
	$(PYTHON) src/run_step.py 1
	@echo "=== Steps 2, 3 & 4: Cut Enumeration, 100% Simulation Check, Classification & Costing ==="
	$(PYTHON) src/run_step.py cut_stats
	@echo "=== Step 5: Redundancy Checking & Table 4 Self-Test ==="
	$(PYTHON) src/run_step.py 5
	@echo "=== Reproducing Table 1: Usable vs Reduced Library Mapping ==="
	$(PYTHON) src/run_step.py table1
	@echo "=== Generating HD Library Class Table ==="
	$(PYTHON) src/run_step.py hd_classes
	@echo "=== Milestone 1 Flow Complete ==="
	@echo "All deliverables generated in results/:"
	@ls -la results/

demo:             ## demo run for interview: make demo IN=<design.v or design_name>
	@test -n "$(IN)" || (echo "Usage: make demo IN=<design_name (e.g. cpu8) or design.v path>" && exit 1)
	@echo "=== Running Option 2 Tool Demo on: $(IN) ==="
	$(PYTHON) src/run_step.py demo "$(IN)"

clean:            ## clean temporary and build files
	rm -rf build __pycache__ src/__pycache__ tests/__pycache__ tests/broken/__pycache__
	@echo "Clean complete."
