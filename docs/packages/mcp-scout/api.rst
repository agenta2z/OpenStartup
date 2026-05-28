API reference
=============

The public API is documented with :mod:`sphinx.ext.autodoc`. Heavy
third-party dependencies are stubbed via ``autodoc_mock_imports`` so the
doc build remains self-contained.

.. note::

   Mock imports live alongside this page in
   ``docs/packages/mcp-scout/_mock_imports.py`` as the executable module
   attribute ``MOCK_IMPORTS``. The top-level ``conf.py`` should union the
   per-package lists rather than duplicating them, e.g.::

       # conf.py
       from importlib import import_module
       autodoc_mock_imports: list[str] = []
       for pkg in ("code-conseil", "code-nautilus", "code-nemo",
                   "mcp-atlassian-exp", "mcp-scout", "web-gui"):
           mod = import_module(f"docs.packages.{pkg}._mock_imports")
           autodoc_mock_imports.extend(mod.MOCK_IMPORTS)

   For reference, the current list for ``mcp-scout`` is::

       MOCK_IMPORTS = ["mcp", "mcp.server", "mcp.types", "atlassian", "googleapiclient", "slack_sdk", "httpx"]

Top-level module
----------------------------------------

.. automodule:: mcp_scout
   :members:
   :undoc-members:
   :show-inheritance:

Server / app surface
----------------------------------------

.. automodule:: mcp_scout.server
   :members:
   :undoc-members:
   :show-inheritance:

Adapters
----------------------------------------

.. automodule:: mcp_scout.adapters
   :members:
   :undoc-members:
   :show-inheritance:

Models
----------------------------------------

.. automodule:: mcp_scout.models
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
----------------------------------------

.. automodule:: mcp_scout.config
   :members:
   :undoc-members:
   :show-inheritance:
