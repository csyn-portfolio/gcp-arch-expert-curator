import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from curator.fetcher import FetchResult
from curator.freshness import run

_FETCH_OK = [FetchResult(url="u", ok=True, markdown="body")]
_FETCH_OK_B = [FetchResult(url="u", ok=True, markdown="b")]


def test_freshness_no_changes_exits_zero(workdir: Path):
    fake_app = MagicMock()
    with (
        patch("curator.freshness._resolve_workdir", return_value=workdir),
        patch("curator.freshness.shallow_clone"),
        patch("curator.freshness.fetch_all", return_value=_FETCH_OK),
        patch("curator.freshness.ClaudeClient") as ClaudeClientCls,
        patch("curator.freshness._load_sources", return_value=["https://example/foo"]),
    ):
        ClaudeClientCls.return_value.call.return_value = "NO_CHANGES"
        result = run(expert="iam-org-policy", dry_run=False, github_app=fake_app)
    assert result == "no_changes"
    fake_app.create_pull_request.assert_not_called()


def test_freshness_majority_fetch_failure_aborts(workdir: Path):
    fake_app = MagicMock()
    failing = [FetchResult(url=f"u{i}", ok=False, error="503") for i in range(6)]
    succeeding = [FetchResult(url=f"u{i}", ok=True, markdown="ok") for i in range(4)]
    with (
        patch("curator.freshness._resolve_workdir", return_value=workdir),
        patch("curator.freshness.shallow_clone"),
        patch("curator.freshness.fetch_all", return_value=failing + succeeding),
        patch("curator.freshness._load_sources", return_value=["u"] * 10),
        pytest.raises(SystemExit) as exc,
    ):
        run(expert="iam-org-policy", dry_run=False, github_app=fake_app)
    assert exc.value.code == 1


def test_freshness_proposes_changes_opens_pr(workdir: Path):
    today = datetime.date.today().isoformat()
    # 212 * 4 + 180-byte prefix = 1028 UTF-8 bytes, satisfies MIN_SIZE 1024
    sections = (
        "# IAM & org policy — canon\n\n"
        "## Manifest\n\n## Pillar-weighted defaults\n\n## Patterns\n\n"
    )
    fake_canon = (
        f'---\nexpert: iam-org-policy\ncanon_version: "0.0.3"\n'
        f'last_updated: "{today}"\nstatus: stub\n---\n\n'
        + sections
        + "body" * 212
    )
    fake_app = MagicMock()
    fake_app.installation_token.return_value = "ghs_test"
    fake_app.create_pull_request.return_value = {"html_url": "x", "number": 2}
    with (
        patch("curator.freshness._resolve_workdir", return_value=workdir),
        patch("curator.freshness.shallow_clone"),
        patch("curator.freshness.fetch_all", return_value=_FETCH_OK_B),
        patch("curator.freshness._load_sources", return_value=["https://example"]),
        patch("curator.freshness._git_ops_push"),
        patch("curator.freshness._git_ops_commit"),
        patch("curator.freshness._git_ops_configure_user"),
        patch("curator.freshness._git_ops_create_branch"),
        patch("curator.freshness.ClaudeClient") as ClaudeClientCls,
    ):
        ClaudeClientCls.return_value.call.return_value = fake_canon
        result = run(expert="iam-org-policy", dry_run=False, github_app=fake_app)
    assert result == "pr_opened"
    kwargs = fake_app.create_pull_request.call_args.kwargs
    assert "curator/freshness" in kwargs["labels"]
