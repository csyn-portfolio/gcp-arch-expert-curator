"""Anthropic SDK wrapper with prompt caching."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import anthropic

MODEL = "claude-opus-4-7"
MAX_INPUT_TOKENS = int(os.environ.get("CURATOR_MAX_INPUT_TOKENS", "12000"))
MAX_OUTPUT_TOKENS = int(os.environ.get("CURATOR_MAX_OUTPUT_TOKENS", "6000"))


def _cached_system_block(text: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": text,
        "cache_control": {"type": "ephemeral"},
    }


def build_promote_request(
    *,
    system_prefix: str,
    current_canon: str,
    pending_files: list[tuple[str, str]],  # [(filename, content), ...]
    expert: str,
) -> dict:
    user_parts = [
        f"Current canon for {expert}:\n\n{current_canon}\n\n---\n\n"
        "Pending lessons to merge:\n"
    ]
    for name, body in pending_files:
        user_parts.append(f"\n### {name}\n\n{body}\n")
    user_parts.append(
        "\n\nTask: merge the pending lessons into the canon. Preserve YAML frontmatter, "
        "all required sections (## Manifest, ## Pillar-weighted defaults, ## Patterns). "
        "Bump canon_version patch. Set last_updated to today's UTC date. "
        "Return ONLY the new canon markdown, no prose around it."
    )
    return {
        "model": MODEL,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "system": [_cached_system_block(system_prefix)],
        "messages": [{"role": "user", "content": "".join(user_parts)}],
    }


def build_freshness_request(
    *,
    system_prefix: str,
    fetched_docs: list[tuple[str, str]],  # [(url, markdown), ...]
    current_canon: str,
    expert: str,
) -> dict:
    doc_block = "\n\n".join(
        f"## SOURCE: {url}\n\n{body}" for url, body in fetched_docs
    )
    cached_prefix = f"{system_prefix}\n\n# REFERENCE_SOURCES\n\n{doc_block}"
    return {
        "model": MODEL,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "system": [_cached_system_block(cached_prefix)],
        "messages": [{
            "role": "user",
            "content": (
                f"Current canon for {expert}:\n\n{current_canon}\n\n"
                "Task: review each claim in the current canon against REFERENCE_SOURCES. "
                "Where claims are stale, contradicted, or missing important updates, "
                "propose a corrected canon. "
                "Cite the source URL inline for each correction. "
                "Bump canon_version patch and set last_updated to today's UTC date. "
                "If NO staleness is detected, return the literal string NO_CHANGES "
                "on a line by itself. Otherwise return ONLY the new canon markdown."
            ),
        }],
    }


@dataclass
class ClaudeClient:
    api_key: str

    def __post_init__(self) -> None:
        self._anthropic = anthropic.Anthropic(api_key=self.api_key)

    def call(self, request: dict) -> str:
        response = self._anthropic.messages.create(**request)
        # Concatenate all text blocks
        return "".join(b.text for b in response.content if b.type == "text")
