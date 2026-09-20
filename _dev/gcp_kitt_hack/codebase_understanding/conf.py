"""Sphinx configuration for the gcp_kitt codebase-understanding docs."""

project = "GCP KITT — Codebase Understanding"
author = "Tony Chen"
copyright = "2026, Atlassian KITT team"
release = "2026-05-08"

extensions = []
templates_path = ["_templates"]
exclude_patterns = ["_build", "_research_drops", "Thumbs.db", ".DS_Store"]

# Use a built-in theme so no extra installs are required.
html_theme = "alabaster"
html_static_path = []

# The master toctree document.
master_doc = "index"

# Be lenient about missing references during this initial build pass —
# Sphinx will still emit warnings, but they won't fail the build.
nitpicky = False

# Cosmetic warnings (title under/overline a few chars short due to em-dashes
# and other multi-byte characters in titles) are noisy but harmless. Suppress
# them so the build log highlights real structural problems only.
suppress_warnings = [
    "docutils",
]
