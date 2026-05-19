"""Fetch GCP doc URLs → readable markdown for freshness grounding."""
from __future__ import annotations

from dataclasses import dataclass

import httpx
import trafilatura


@dataclass
class FetchResult:
    url: str
    ok: bool
    markdown: str = ""
    error: str = ""


def fetch_url(url: str, timeout: float = 30.0) -> FetchResult:
    try:
        r = httpx.get(url, follow_redirects=True, timeout=timeout)
    except httpx.HTTPError as e:
        return FetchResult(url=url, ok=False, error=f"transport error: {e}")
    if r.status_code != 200:
        return FetchResult(url=url, ok=False, error=f"HTTP {r.status_code}")
    extracted = trafilatura.extract(r.text, output_format="markdown")
    if not extracted:
        return FetchResult(url=url, ok=False, error="trafilatura extracted no content")
    return FetchResult(url=url, ok=True, markdown=extracted)


def fetch_all(urls: list[str], timeout: float = 30.0) -> list[FetchResult]:
    return [fetch_url(u, timeout=timeout) for u in urls]
