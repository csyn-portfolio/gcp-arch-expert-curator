"""Entry point. Reads MODE + EXPERT env, dispatches to promote or freshness."""
from __future__ import annotations

import logging
import os
import sys

from curator import freshness, promote
from curator.github_app import GitHubApp

ALLOWED_EXPERTS = frozenset({
    "ai-agents", "compute-serverless", "gke-containers",
    "data-platform", "databases", "networking",
    "iam-org-policy", "security-compliance", "observability-sre",
    "finops", "iac-devops",
})
ALLOWED_MODES = frozenset({"promote", "freshness"})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log = logging.getLogger("curator")

    mode = os.environ.get("MODE", "").strip()
    expert = os.environ.get("EXPERT", "").strip()
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    if mode not in ALLOWED_MODES:
        log.error("invalid MODE=%r (allowed: %s)", mode, sorted(ALLOWED_MODES))
        sys.exit(2)
    if expert not in ALLOWED_EXPERTS:
        log.error("invalid EXPERT=%r (allowed: %s)", expert, sorted(ALLOWED_EXPERTS))
        sys.exit(2)

    github_app = GitHubApp(
        app_id=int(os.environ["GH_APP_ID"]),
        private_key_pem=os.environ["GH_APP_PRIVATE_KEY"],
        installation_id=int(os.environ["GH_APP_INSTALLATION_ID"]),
    )

    log.info("curator run: mode=%s expert=%s dry_run=%s", mode, expert, dry_run)
    if mode == "promote":
        result = promote.run(expert=expert, dry_run=dry_run, github_app=github_app)
    else:
        result = freshness.run(expert=expert, dry_run=dry_run, github_app=github_app)
    log.info("result: %s", result)


if __name__ == "__main__":
    main()
