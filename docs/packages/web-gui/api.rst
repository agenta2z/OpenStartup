API reference
=============

The public API is documented with :mod:`sphinx.ext.autodoc`. Heavy
third-party dependencies are stubbed via ``autodoc_mock_imports`` so the
doc build remains self-contained.

.. note::

   Mock imports live alongside this page in
   ``docs/packages/web-gui/_mock_imports.py`` as the executable module
   attribute ``MOCK_IMPORTS``. The top-level ``conf.py`` should union the
   per-package lists rather than duplicating them, e.g.::

       # conf.py
       from importlib import import_module
       autodoc_mock_imports: list[str] = []
       for pkg in ("code-conseil", "code-nautilus", "code-nemo",
                   "mcp-atlassian-exp", "mcp-scout", "web-gui"):
           mod = import_module(f"docs.packages.{pkg}._mock_imports")
           autodoc_mock_imports.extend(mod.MOCK_IMPORTS)

   For reference, the current list for ``web-gui`` is::

       MOCK_IMPORTS = ["fastapi", "starlette", "uvicorn", "gunicorn", "jinja2", "httpx", "websockets"]

Top-level module
----------------------------------------

.. automodule:: web_gui
   :members:
   :undoc-members:
   :show-inheritance:

Server / app surface
----------------------------------------

.. automodule:: web_gui.server
   :members:
   :undoc-members:
   :show-inheritance:

Adapters
----------------------------------------

.. automodule:: web_gui.adapters
   :members:
   :undoc-members:
   :show-inheritance:

Models
----------------------------------------

.. automodule:: web_gui.models
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
----------------------------------------

.. automodule:: web_gui.config
   :members:
   :undoc-members:
   :show-inheritance:
