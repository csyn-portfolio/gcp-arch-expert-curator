"""Promote LESSONS_PENDING/<expert>/* into canon/<expert>/index.md via PR."""
from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from curator import git_ops, manifest, validator
from curator._paths import CONFIG_DIR
from curator.claude_client import ClaudeClient, build_promote_request
from curator.git_ops import shallow_clone
from curator.github_app import GitHubApp

LOG = logging.getLogger(__name__)

PLUGIN_REPO = "csyn-portfolio/gcp-arch-expert"
PLUGIN_REPO_URL = f"https://github.com/{PLUGIN_REPO}.git"
COMMITTER_NAME = "gcp-arch-expert-curator[bot]"
COMMITTER_EMAIL = "gcp-arch-expert-curator[bot]@users.noreply.github.com"


def _resolve_workdir() -> Path:
    """Return a fresh temp directory that will serve as the repo root.

    In production, shallow_clone() populates it. Tests patch this to return
    a pre-populated directory, and also patch shallow_clone to a no-op, so
    run() treats the returned path directly as the repo root (repo = workdir).
    """
    return Path(tempfile.mkdtemp(prefix="curator-promote-"))


def _git_ops_commit(repo: Path, message: str) -> None:
    git_ops.add_and_commit(repo, message)


def _git_ops_push(repo: Path, branch: str, token: str) -> None:
    git_ops.push_branch(repo, branch, token)


def _git_ops_mv(repo: Path, src: Path, dst: Path) -> None:
    git_ops.git_mv(repo, src, dst)


def _git_ops_configure_user(repo: Path, name: str, email: str) -> None:
    git_ops.configure_user(repo, name, email)


def _git_ops_create_branch(repo: Path, branch: str) -> None:
    git_ops.create_branch(repo, branch)


def _load_prompt_prefix() -> str:
    return (CONFIG_DIR / "prompts" / "promote.md").read_text()


def run(*, expert: str, dry_run: bool, github_app: GitHubApp) -> str:
    """Execute the promote pipeline. Returns 'no_pending' | 'pr_opened' | 'dry_run'."""
    workdir = _resolve_workdir()
    # workdir IS the repo root. _resolve_workdir returns a temp dir for production
    # (which shallow_clone then populates), or a pre-populated dir in tests.
    repo = workdir

    # Mint the installation token once; the plugin repo is private, so the
    # clone needs it. Re-used for push later. Tokens are valid for 1 hour;
    # job timeout is 30m, so a single token covers the whole run.
    token = github_app.installation_token()

    if not (repo / ".git").exists():  # tests pre-populate the workdir; production clones
        shallow_clone(PLUGIN_REPO_URL, repo, token=token)

    pending_dir = repo / "canon" / "LESSONS_PENDING" / expert
    processed_dir = repo / "canon" / "LESSONS_PROCESSED" / expert
    canon_path = repo / "canon" / expert / "index.md"
    manifest_path = repo / "canon" / "_meta" / "manifest.json"

    if not pending_dir.exists():
        LOG.info("no pending dir for %s", expert)
        return "no_pending"
    pending_files = sorted(pending_dir.glob("*.md"))
    if not pending_files:
        LOG.info("no pending files for %s", expert)
        return "no_pending"

    current_canon = canon_path.read_text()
    pending_contents = [(p.name, p.read_text()) for p in pending_files]

    client = ClaudeClient(
        project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
        region=os.environ.get("ANTHROPIC_VERTEX_REGION", "us"),
    )
    request = build_promote_request(
        system_prefix=_load_prompt_prefix(),
        current_canon=current_canon,
        pending_files=pending_contents,
        expert=expert,
    )

    LOG.info("calling claude api for promote/%s with %d pending files", expert, len(pending_files))
    proposed = client.call(request)

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
        LOG.info("DRY_RUN: would write canon, move %d pending files, open PR", len(pending_files))
        LOG.info("soft warnings: %s", [w.message for w in result.soft_warnings])
        return "dry_run"

    # Apply edits to working tree
    canon_path.write_text(proposed)
    for p in pending_files:
        _git_ops_mv(repo, p, processed_dir / p.name)
    new_meta = manifest.bump_specialist(current_meta, expert=expert, new_date=today.isoformat())
    manifest_path.write_text(json.dumps(new_meta, indent=2) + "\n")

    _git_ops_configure_user(repo, COMMITTER_NAME, COMMITTER_EMAIL)
    branch = f"curator/promote/{expert}/{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    _git_ops_create_branch(repo, branch)
    _git_ops_commit(repo, f"chore(canon): promote {len(pending_files)} lessons for {expert}")
    _git_ops_push(repo, branch, token)

    labels = ["curator/promote"]
    if result.soft_warnings:
        labels.append("needs-fixup")
    body_lines = [
        f"Curator promote run for `{expert}` on {today.isoformat()}.",
        "",
        f"Promoted {len(pending_files)} lessons:",
        *(f"- `{p.name}`" for p in pending_files),
    ]
    if result.soft_warnings:
        body_lines.append("")
        body_lines.append("**Soft warnings (`needs-fixup`):**")
        body_lines.extend(f"- {w.message}" for w in result.soft_warnings)
    pr = github_app.create_pull_request(
        repo=PLUGIN_REPO,
        head=branch,
        base="main",
        title=f"chore(canon): promote {len(pending_files)} lessons for {expert}",
        body="\n".join(body_lines),
        labels=labels,
    )
    LOG.info("PR opened: %s", pr["html_url"])
    return "pr_opened"
