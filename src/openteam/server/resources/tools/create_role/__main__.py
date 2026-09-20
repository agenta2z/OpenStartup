"""Module entrypoint: enables ``python -m openteam.server.resources.tools.create_role``."""

import sys

from .cli import main

sys.exit(main())
