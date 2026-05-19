from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from curator.promote import run


def test_promote_no_pending_files_exits_early(workdir: Path):
    # Remove the lesson file
    (workdir / "canon" / "LESSONS_PENDING" / "iam-org-policy" / "lesson1.md").unlink()
    with patch("curator.promote.shallow_clone") as clone, \
         patch("curator.promote.ClaudeClient") as claude_mock:
        clone.side_effect = lambda *a, **kw: None  # no-op; workdir is pre-populated
        # Patch the target_dir resolution to point at workdir
        with patch("curator.promote._resolve_workdir", return_value=workdir):
            result = run(expert="iam-org-policy", dry_run=True, github_app=MagicMock())
    assert result == "no_pending"
    claude_mock.assert_not_called()


def test_promote_opens_pr_when_files_present(workdir: Path):
    fake_canon = (
        '---\nexpert: iam-org-policy\ncanon_version: "0.0.3"\n'
        f'last_updated: "{__import__("datetime").date.today().isoformat()}"\nstatus: stub\n---\n\n'
        "# IAM & org policy — canon\n\nNew content from promote.\n\n"
        "## Manifest\n\n## Pillar-weighted defaults\n\n## Patterns\n\n### NewPattern\n\n"
        "body" * 202  # pad to meet MIN_SIZE (202 * 4 + prefix = 1031 UTF-8 bytes >= 1024)
    )
    fake_app = MagicMock()
    fake_app.installation_token.return_value = "ghs_test"
    fake_app.create_pull_request.return_value = {
        "html_url": "https://github.com/test/pr/1",
        "number": 1,
    }

    with patch("curator.promote.shallow_clone"), \
         patch("curator.promote._resolve_workdir", return_value=workdir), \
         patch("curator.promote._git_ops_push"), \
         patch("curator.promote._git_ops_commit"), \
         patch("curator.promote._git_ops_mv"), \
         patch("curator.promote._git_ops_configure_user"), \
         patch("curator.promote._git_ops_create_branch"), \
         patch("curator.promote.ClaudeClient") as ClaudeClientCls:
        ClaudeClientCls.return_value.call.return_value = fake_canon
        result = run(expert="iam-org-policy", dry_run=False, github_app=fake_app)

    assert result == "pr_opened"
    fake_app.create_pull_request.assert_called_once()
    kwargs = fake_app.create_pull_request.call_args.kwargs
    assert kwargs["repo"] == "csyn-portfolio/gcp-arch-expert"
    assert "curator/promote" in kwargs["labels"]


def test_promote_validation_failure_exits_nonzero(workdir: Path):
    bad_canon = "not valid markdown"
    fake_app = MagicMock()
    with patch("curator.promote.shallow_clone"), \
         patch("curator.promote._resolve_workdir", return_value=workdir), \
         patch("curator.promote.ClaudeClient") as ClaudeClientCls:
        ClaudeClientCls.return_value.call.return_value = bad_canon
        with pytest.raises(SystemExit) as exc:
            run(expert="iam-org-policy", dry_run=False, github_app=fake_app)
    assert exc.value.code == 1
    fake_app.create_pull_request.assert_not_called()
