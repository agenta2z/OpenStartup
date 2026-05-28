API reference
=============

The public API is documented with :mod:`sphinx.ext.autodoc`. Heavy
third-party dependencies are stubbed via ``autodoc_mock_imports`` so the
doc build remains self-contained.

.. note::

   Mock imports live alongside this page in
   ``docs/packages/code-conseil/_mock_imports.py`` as the executable module
   attribute ``MOCK_IMPORTS``. The top-level ``conf.py`` should union the
   per-package lists rather than duplicating them, e.g.::

       # conf.py
       from importlib import import_module
       autodoc_mock_imports: list[str] = []
       for pkg in ("code-conseil", "code-nautilus", "code-nemo",
                   "mcp-atlassian-exp", "mcp-scout", "web-gui"):
           mod = import_module(f"docs.packages.{pkg}._mock_imports")
           autodoc_mock_imports.extend(mod.MOCK_IMPORTS)

   For reference, the current list for ``code-conseil`` is::

       MOCK_IMPORTS = ["fastapi", "starlette", "uvicorn", "atlassian", "openai", "anthropic", "github"]

Top-level module
----------------------------------------

.. automodule:: code_conseil
   :members:
   :undoc-members:
   :show-inheritance:

Server / app surface
----------------------------------------

.. automodule:: code_conseil.server
   :members:
   :undoc-members:
   :show-inheritance:

Adapters
----------------------------------------

.. automodule:: code_conseil.adapters
   :members:
   :undoc-members:
   :show-inheritance:

Models
----------------------------------------

.. automodule:: code_conseil.models
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
----------------------------------------

.. automodule:: code_conseil.config
   :members:
   :undoc-members:
   :show-inheritance:
