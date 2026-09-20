# Configuration file for the Sphinx documentation builder.
#
# Documentation set: "LLM-Native Recommendation — Data Collection".
# Modeled on the house config used elsewhere in _dev (RTD theme, Mermaid,
# copybutton) so this project renders consistently with the rest of the repo.

# -- Project information -------------------------------------------------------

project = "LLM-Native Recommendation — Data Collection"
copyright = "2026, native_llm_ranking"
author = "native_llm_ranking"
release = "1.0.0"

# -- General configuration -----------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
]

# Exclude the raw Markdown reference exports (under references/) from the Sphinx
# build — they are verbatim source artifacts kept for provenance, not RST pages.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "*.md",
    "references/*",
]

# -- Nitpicky mode -------------------------------------------------------------
# Intentionally OFF: this doc set links heavily to external internalfb.com /
# workplace / arxiv URLs and to Meta-internal symbols that Sphinx cannot
# resolve as cross-references. Turning nitpicky on would produce noise, not
# signal. Internal :doc:/:ref: links are still validated by the normal build.
nitpicky = False

# -- Options for HTML output ---------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
}
html_static_path = ["_static"]

# -- Mermaid configuration -----------------------------------------------------
# Pin to Mermaid 10.6.1 for deterministic rendering.
mermaid_version = "10.6.1"
mermaid_init_js = "mermaid.initialize({startOnLoad:true, theme:'default'});"

# -- Copy-button configuration -------------------------------------------------
copybutton_prompt_text = r"^\$ "
copybutton_prompt_is_regexp = True

# -- To-do configuration -------------------------------------------------------
todo_include_todos = True

# -- Intersphinx ---------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
