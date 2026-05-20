"""Minimal git operations wrapper. Uses subprocess.run, no pygit2 dependency."""
from __future__ import annotations

import subprocess
from pathlib import Path


def shallow_clone(
    repo_url: str, dest: Path, branch: str = "main", token: str | None = None
) -> None:
    """Shallow-clone a GitHub repo. If `token` is provided, inject it into the
    URL so private repos can be fetched. The token-bearing URL is passed only
    to the git subprocess invocation and never written to git config.
    """
    url = repo_url
    if token:
        url = repo_url.replace("https://", f"https://x-access-token:{token}@", 1)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, url, str(dest)],
        check=True,
    )


def configure_user(repo: Path, name: str, email: str) -> None:
    subprocess.run(["git", "-C", str(repo), "config", "user.name", name], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", email], check=True)


def create_branch(repo: Path, branch: str) -> None:
    subprocess.run(["git", "-C", str(repo), "switch", "-c", branch], check=True)


def add_and_commit(repo: Path, message: str, paths: list[str] | None = None) -> None:
    if paths is None:
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    else:
        subprocess.run(["git", "-C", str(repo), "add", *paths], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", message], check=True)


def push_branch(repo: Path, branch: str, token: str) -> None:
    remote_url = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    # Inject token via temporary remote (avoids leaking in git config or history)
    auth_url = remote_url.replace(
        "https://", f"https://x-access-token:{token}@", 1
    )
    subprocess.run(["git", "-C", str(repo), "push", auth_url, branch], check=True)


def git_mv(repo: Path, src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "mv", str(src), str(dst)], check=True)
