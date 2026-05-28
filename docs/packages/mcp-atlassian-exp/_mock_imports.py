"""Mock imports for Sphinx autodoc.

This module exposes ``MOCK_IMPORTS`` so the project-level ``conf.py`` can
union the per-package mock import lists without hard-coding them centrally::

    # conf.py
    from importlib import import_module
    autodoc_mock_imports = []
    for pkg in ("code_conseil", "code_nautilus", "code_nemo",
                "mcp_atlassian_exp", "mcp_scout", "web_gui"):
        try:
            mod = import_module(f"docs.packages.{pkg.replace('_', '-')}._mock_imports")
            autodoc_mock_imports.extend(mod.MOCK_IMPORTS)
        except ModuleNotFoundError:
            pass

The list intentionally lives next to the per-package documentation so the
declaration tracks the docs, not the build configuration.
"""

MOCK_IMPORTS: list[str] = ['mcp', 'mcp.server', 'mcp.types', 'atlassian', 'httpx', 'anyio', 'starlette']
