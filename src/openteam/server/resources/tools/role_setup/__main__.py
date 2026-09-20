"""Module entrypoint: enables ``python -m openteam.server.resources.tools.role_setup``."""

import sys

from .cli import main

sys.exit(main())
