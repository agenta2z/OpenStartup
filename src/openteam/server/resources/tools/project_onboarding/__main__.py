"""Module entrypoint: enables ``python -m openteam.server.resources.tools.project_onboarding``."""

import sys

from .cli import main

sys.exit(main())
