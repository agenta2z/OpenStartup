# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""REST route backing the Setup Wizard's "From Library" template dropdown.

Ported from RankEvolve ``submission_templates_routes.py`` — thin transport
adapter over ``AF-EH/submission_templates_service.list_submission_templates``.

The FE hook ``useSubmissionTemplates`` fetches this on modal open. Mounted at
``/api/submission-templates`` (global, no session/hub prefix — the templates
are process-wide, bundled resources).
"""

from __future__ import annotations

import logging
from typing import Any

from agent_foundation.experiment_hub import submission_templates_service
from fastapi import APIRouter

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/submission-templates")
async def list_submission_templates() -> dict[str, Any]:
    """Return the reference-script manifest as a flat list.

    Returns ``{"templates": []}`` if the bundled manifest is missing (setup
    wizard still works; only the From-Library tab degrades)."""
    return await submission_templates_service.list_submission_templates()
