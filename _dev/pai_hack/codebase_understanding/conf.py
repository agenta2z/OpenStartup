# Configuration file for the Sphinx documentation builder.
# Modeled on convo_ai_hack reference (RTD theme, Mermaid, copybutton).

# -- Project information -------------------------------------------------------

project = "Proactive AI Service"
copyright = "2026, Atlassian"
author = "Proactive AI Team"
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

templates_path = ["_templates"]

# Exclude legacy Markdown files from the Sphinx build — they live in
# _legacy_md/ for reference only and must not be parsed as source.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "*.md",
    "_legacy_md",
]

# -- Nitpicky mode -------------------------------------------------------------
# Warn about all missing references.
nitpicky = True

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
