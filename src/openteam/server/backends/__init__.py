"""Pluggable inferencer backends for the OpenStartup conversation loop.

Importing this package triggers registration of the built-in ``mock``,
``rovodev``, and ``claude_cli`` backends on the module-level singleton.
"""

# Triggers built-in registration as a side effect of importing the package.
from openteam.server.backends import factories  # noqa: F401
from openteam.server.backends.registry import (
    BackendBuildContext,
    BackendDescriptor,
    BackendFactory,
    BackendRegistry,
    get_registry,
    register_backend,
)

__all__ = [
    "BackendBuildContext",
    "BackendDescriptor",
    "BackendFactory",
    "BackendRegistry",
    "get_registry",
    "register_backend",
]
