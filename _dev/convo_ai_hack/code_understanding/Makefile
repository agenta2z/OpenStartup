# Minimal Makefile for Sphinx documentation
# Usage:
#   make html         # build HTML docs (output: _build/html/)
#   make linkcheck    # verify all external links work
#   make clean        # remove _build/

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help html clean linkcheck nitpicky install

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

html:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo ""
	@echo "Build complete. Open: file://$(PWD)/$(BUILDDIR)/html/architecture/index.html"

linkcheck:
	@$(SPHINXBUILD) -M linkcheck "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

nitpicky:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -n $(SPHINXOPTS) $(O)

clean:
	@rm -rf "$(BUILDDIR)"
	@echo "Removed $(BUILDDIR)"

install:
	@echo "Installing Sphinx + extensions..."
	pip install sphinx sphinx-rtd-theme sphinxcontrib-mermaid sphinx-copybutton

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
