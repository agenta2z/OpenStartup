API reference
=============

The public API is documented with :mod:`sphinx.ext.autodoc`. Heavy
third-party dependencies are stubbed via ``autodoc_mock_imports`` so the
doc build remains self-contained.

.. note::

   Mock imports live alongside this page in
   ``docs/packages/mcp-atlassian-exp/_mock_imports.py`` as the executable module
   attribute ``MOCK_IMPORTS``. The top-level ``conf.py`` should union the
   per-package lists rather than duplicating them, e.g.::

       # conf.py
       from importlib import import_module
       autodoc_mock_imports: list[str] = []
       for pkg in ("code-conseil", "code-nautilus", "code-nemo",
                   "mcp-atlassian-exp", "mcp-scout", "web-gui"):
           mod = import_module(f"docs.packages.{pkg}._mock_imports")
           autodoc_mock_imports.extend(mod.MOCK_IMPORTS)

   For reference, the current list for ``mcp-atlassian-exp`` is::

       MOCK_IMPORTS = ["mcp", "mcp.server", "mcp.types", "atlassian", "httpx", "anyio", "starlette"]

Top-level module
----------------------------------------

.. automodule:: mcp_atlassian_exp
   :members:
   :undoc-members:
   :show-inheritance:

Server / app surface
----------------------------------------

.. automodule:: mcp_atlassian_exp.server
   :members:
   :undoc-members:
   :show-inheritance:

Adapters
----------------------------------------

.. automodule:: mcp_atlassian_exp.adapters
   :members:
   :undoc-members:
   :show-inheritance:

Models
----------------------------------------

.. automodule:: mcp_atlassian_exp.models
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
----------------------------------------

.. automodule:: mcp_atlassian_exp.config
   :members:
   :undoc-members:
   :show-inheritance:
