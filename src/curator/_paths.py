"""Centralized path resolution for runtime config (prompts + freshness sources).

In dev (source tree), config lives at `<repo>/config/`. After `pip install .`
in the container, the package lands at `site-packages/curator/` and the source
tree's `config/` is no longer a sibling — the Dockerfile copies it to
`/app/config/`. Set `CURATOR_CONFIG_DIR` to override; the default falls back
to the dev-tree layout for local pytest / `python -m curator.main` runs.
"""
from __future__ import annotations

import os
from pathlib import Path

_DEV_CONFIG = Path(__file__).parent.parent.parent / "config"
CONFIG_DIR = Path(os.environ.get("CURATOR_CONFIG_DIR", str(_DEV_CONFIG)))
