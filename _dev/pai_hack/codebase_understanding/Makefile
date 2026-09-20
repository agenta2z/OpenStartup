# Makefile for Sphinx documentation
# Targets: html, linkcheck, clean, install

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help html linkcheck clean install

help:
	@echo "Proactive AI Service — Documentation Build Targets"
	@echo "  make install    Install Python dependencies (sphinx, theme, extensions)"
	@echo "  make html       Build HTML documentation"
	@echo "  make linkcheck  Check all external links"
	@echo "  make clean      Remove build artifacts"

install:
	pip install sphinx sphinx-rtd-theme sphinx-copybutton sphinxcontrib-mermaid

html:
	@$(SPHINXBUILD) -b html $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/html"
	@echo "Build finished. Open $(BUILDDIR)/html/index.html to view."

linkcheck:
	@$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck"
	@echo "Link check complete. See $(BUILDDIR)/linkcheck/output.txt for results."

clean:
	rm -rf $(BUILDDIR)
	@echo "Build directory cleaned."
