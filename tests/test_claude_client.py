from unittest.mock import MagicMock, patch

from curator.claude_client import ClaudeClient, build_freshness_request, build_promote_request


def test_build_promote_request_uses_cache_control_on_system():
    req = build_promote_request(
        system_prefix="pillar definitions and schema",
        current_canon="# current",
        pending_files=[("file1.md", "pending body")],
        expert="iam-org-policy",
    )
    assert isinstance(req["system"], list)
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert req["model"] == "claude-sonnet-4-6"
    assert any("iam-org-policy" in m["content"] for m in req["messages"])


def test_build_freshness_request_includes_fetched_docs_in_cached_prefix():
    req = build_freshness_request(
        system_prefix="pillar definitions",
        fetched_docs=[("https://cloud.google.com/iam", "doc body")],
        current_canon="# current",
        expert="iam-org-policy",
    )
    system_text = " ".join(b["text"] for b in req["system"])
    assert "https://cloud.google.com/iam" in system_text
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_claude_client_returns_text_block():
    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="proposed canon body")]
    fake_anthropic = MagicMock()
    fake_anthropic.messages.create.return_value = fake_response
    with patch("curator.claude_client.AnthropicVertex", return_value=fake_anthropic):
        client = ClaudeClient(project_id="gcp-arch-expert-platform", region="us")
        text = client.call({
            "model": "claude-sonnet-4-6",
            "system": [],
            "messages": [],
            "max_tokens": 4096,
        })
    assert text == "proposed canon body"


def test_claude_client_defaults_region_to_us():
    with patch("curator.claude_client.AnthropicVertex") as ctor:
        ClaudeClient(project_id="gcp-arch-expert-platform")
    ctor.assert_called_once_with(project_id="gcp-arch-expert-platform", region="us")
