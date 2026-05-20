from unittest.mock import patch

import pytest

from curator.main import main


def test_main_dispatches_promote(monkeypatch):
    monkeypatch.setenv("MODE", "promote")
    monkeypatch.setenv("EXPERT", "iam-org-policy")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "gcp-arch-expert-platform")
    monkeypatch.setenv("ANTHROPIC_VERTEX_REGION", "us")
    monkeypatch.setenv("GH_APP_ID", "1")
    monkeypatch.setenv("GH_APP_INSTALLATION_ID", "1")
    monkeypatch.setenv("GH_APP_PRIVATE_KEY", "-----BEGIN-----\nkey\n-----END-----")
    with patch("curator.main.promote.run", return_value="dry_run") as p, \
         patch("curator.main.freshness.run") as f:
        main()
    p.assert_called_once()
    f.assert_not_called()


def test_main_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("MODE", "delete-everything")
    monkeypatch.setenv("EXPERT", "iam-org-policy")
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_main_rejects_unknown_expert(monkeypatch):
    monkeypatch.setenv("MODE", "promote")
    monkeypatch.setenv("EXPERT", "not-a-thing")
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
