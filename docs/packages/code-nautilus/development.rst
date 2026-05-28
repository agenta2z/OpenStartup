Development
===========

Project layout
----------------------------------------

::

    packages/code-nautilus/
    |-- pyproject.toml
    |-- README.md
    |-- src/code_nautilus/
    |   |-- __init__.py
    |   |-- server.py | app.py | cli.py
    |   |-- adapters/
    |   |-- models/
    |   `-- config.py
    `-- tests/

Editable install
----------------------------------------

.. code-block:: bash

    pip install -e 'packages/code-nautilus[dev]'

Running the test suite
----------------------------------------

.. code-block:: bash

    pytest packages/code-nautilus/tests -q

Linting & typing
----------------------------------------

.. code-block:: bash

    ruff check packages/code-nautilus
    mypy packages/code-nautilus/src

Building the docs locally
----------------------------------------

From the repo root::

    sphinx-build -b html docs docs/_build/html

The HTML for this package will be rendered under
``docs/_build/html/packages/code-nautilus/index.html``.

Release process
----------------------------------------

* All packages are versioned together. Bump the monorepo version, tag,
  and let CI publish wheels.
* Changelogs live in ``CHANGELOG.md`` at the package root.

Contributing
----------------------------------------

* Open a Bitbucket pull request targeting ``main``.
* Ensure ``pytest``, ``ruff`` and ``mypy`` pass locally.
* New public APIs require docstrings so they surface in :doc:`api`.
