from unittest.mock import MagicMock, patch

from curator.claude_client import ClaudeClient, build_freshness_request, build_promote_request


def test_build_promote_request_uses_cache_control_on_system():
    req = build_promote_request(
        system_prefix="pillar definitions and schema",
        current_canon="# current",
        pending_files=[("file1.md", "pending body")],
        expert="iam-org-policy",
    )
    # System should be a list with one block carrying cache_control
    assert isinstance(req["system"], list)
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert req["model"].startswith("claude-opus-4-7")
    assert any("iam-org-policy" in m["content"] for m in req["messages"])


def test_build_freshness_request_includes_fetched_docs_in_cached_prefix():
    req = build_freshness_request(
        system_prefix="pillar definitions",
        fetched_docs=[("https://cloud.google.com/iam", "doc body")],
        current_canon="# current",
        expert="iam-org-policy",
    )
    # Fetched docs should be part of the cached prefix
    system_text = " ".join(b["text"] for b in req["system"])
    assert "https://cloud.google.com/iam" in system_text
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_claude_client_returns_text_block():
    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="proposed canon body")]
    client = ClaudeClient(api_key="sk-ant-test")
    with patch.object(client._anthropic.messages, "create", return_value=fake_response):
        text = client.call({
            "model": "claude-opus-4-7",
            "system": [],
            "messages": [],
            "max_tokens": 4096,
        })
    assert text == "proposed canon body"
