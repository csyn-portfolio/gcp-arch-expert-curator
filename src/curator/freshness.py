"""Freshness check: canon vs current GCP docs."""
from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

import yaml

from curator import git_ops, manifest, validator
from curator.claude_client import ClaudeClient, build_freshness_request
from curator.fetcher import fetch_all
from curator.git_ops import shallow_clone
from curator.github_app import GitHubApp

LOG = logging.getLogger(__name__)

PLUGIN_REPO = "csyn-portfolio/gcp-arch-expert"
PLUGIN_REPO_URL = f"https://github.com/{PLUGIN_REPO}.git"
COMMITTER_NAME = "gcp-arch-expert-curator[bot]"
COMMITTER_EMAIL = "gcp-arch-expert-curator[bot]@users.noreply.github.com"
NO_CHANGES_SENTINEL = "NO_CHANGES"


def _resolve_workdir() -> Path:
    """Return a fresh temp directory that will serve as the repo root.

    In production, shallow_clone() populates it. Tests patch this to return
    a pre-populated directory, and also patch shallow_clone to a no-op, so
    run() treats the returned path directly as the repo root (repo = workdir).
    """
    return Path(tempfile.mkdtemp(prefix="curator-freshness-"))


def _git_ops_commit(repo: Path, message: str) -> None:
    git_ops.add_and_commit(repo, message)


def _git_ops_push(repo: Path, branch: str, token: str) -> None:
    git_ops.push_branch(repo, branch, token)


def _git_ops_configure_user(repo: Path, name: str, email: str) -> None:
    git_ops.configure_user(repo, name, email)


def _git_ops_create_branch(repo: Path, branch: str) -> None:
    git_ops.create_branch(repo, branch)


def _load_prompt_prefix() -> str:
    prompts_dir = Path(__file__).parent.parent.parent / "config" / "prompts"
    return (prompts_dir / "freshness.md").read_text()


def _load_sources(expert: str) -> list[str]:
    config_path = (
        Path(__file__).parent.parent.parent / "config" / expert / "freshness-sources.yaml"
    )
    data = yaml.safe_load(config_path.read_text())
    return [entry["url"] for entry in data.get("sources", [])]


def run(*, expert: str, dry_run: bool, github_app: GitHubApp) -> str:
    """Execute the freshness pipeline. Returns 'no_changes' | 'pr_opened' | 'dry_run'."""
    urls = _load_sources(expert)
    if not urls:
        LOG.warning("no freshness-sources configured for %s", expert)
        return "no_changes"

    fetches = fetch_all(urls)
    failures = sum(1 for f in fetches if not f.ok)
    if failures > len(fetches) // 2:
        LOG.error("majority URL fetch failure (%d/%d); aborting", failures, len(fetches))
        sys.exit(1)
    fetched_docs = [(f.url, f.markdown) for f in fetches if f.ok]

    workdir = _resolve_workdir()
    # workdir IS the repo root. _resolve_workdir returns a temp dir for production
    # (which shallow_clone then populates), or a pre-populated dir in tests.
    repo = workdir

    # Mint the installation token once; the plugin repo is private, so the
    # clone needs it. Re-used for push later. Tokens last 1 hour > 30m job timeout.
    token = github_app.installation_token()

    if not (repo / ".git").exists():  # tests pre-populate the workdir; production clones
        shallow_clone(PLUGIN_REPO_URL, repo, token=token)

    canon_path = repo / "canon" / expert / "index.md"
    manifest_path = repo / "canon" / "_meta" / "manifest.json"
    current_canon = canon_path.read_text()

    client = ClaudeClient(
        project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
        region=os.environ.get("ANTHROPIC_VERTEX_REGION", "us"),
    )
    request = build_freshness_request(
        system_prefix=_load_prompt_prefix(),
        fetched_docs=fetched_docs,
        current_canon=current_canon,
        expert=expert,
    )

    LOG.info("calling claude api for freshness/%s with %d sources", expert, len(fetched_docs))
    proposed = client.call(request)

    if proposed.strip() == NO_CHANGES_SENTINEL:
        LOG.info("no staleness detected for %s", expert)
        return "no_changes"

    today = datetime.date.today()
    current_meta = json.loads(manifest_path.read_text())
    current_version = current_meta["experts"][expert]["version"]

    try:
        result = validator.validate(
            proposed=proposed,
            current_version=current_version,
            today=today,
            expert=expert,
            current_size=len(current_canon),
        )
    except validator.ValidationError as e:
        LOG.error("validation failed: %s", e)
        LOG.error("proposed canon was:\n%s", proposed)
        sys.exit(1)

    if dry_run:
        LOG.info("DRY_RUN: would write canon, open PR")
        LOG.info("soft warnings: %s", [w.message for w in result.soft_warnings])
        return "dry_run"

    # Apply edits to working tree
    canon_path.write_text(proposed)
    new_meta = manifest.bump_specialist(current_meta, expert=expert, new_date=today.isoformat())
    manifest_path.write_text(json.dumps(new_meta, indent=2) + "\n")

    _git_ops_configure_user(repo, COMMITTER_NAME, COMMITTER_EMAIL)
    branch = f"curator/freshness/{expert}/{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    _git_ops_create_branch(repo, branch)
    _git_ops_commit(repo, f"chore(canon): freshness pass for {expert}")
    _git_ops_push(repo, branch, token)

    labels = ["curator/freshness"]
    if result.soft_warnings:
        labels.append("needs-fixup")
    body_lines = [
        f"Curator freshness pass for `{expert}` on {today.isoformat()}.",
        "",
        f"Grounded in {len(fetched_docs)}/{len(urls)} fetched sources:",
        *(f"- {url}" for url, _ in fetched_docs),
    ]
    if failures:
        body_lines.append(f"\n_Note: {failures} sources failed to fetch._")
    if result.soft_warnings:
        body_lines.append("")
        body_lines.append("**Soft warnings (`needs-fixup`):**")
        body_lines.extend(f"- {w.message}" for w in result.soft_warnings)
    pr = github_app.create_pull_request(
        repo=PLUGIN_REPO,
        head=branch,
        base="main",
        title=f"chore(canon): freshness pass for {expert}",
        body="\n".join(body_lines),
        labels=labels,
    )
    LOG.info("PR opened: %s", pr["html_url"])
    return "pr_opened"
