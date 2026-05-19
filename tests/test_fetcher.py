from unittest.mock import MagicMock, patch

from curator.fetcher import fetch_all, fetch_url


def test_fetch_url_success():
    html = "<html><body><h1>Title</h1><p>Body text.</p></body></html>"
    fake = MagicMock(status_code=200, text=html)
    with patch("curator.fetcher.httpx.get", return_value=fake):
        result = fetch_url("https://cloud.google.com/iam")
    assert result.ok
    assert "Body text" in result.markdown


def test_fetch_url_404_returns_not_ok():
    fake = MagicMock(status_code=404)
    fake.text = "not found"
    with patch("curator.fetcher.httpx.get", return_value=fake):
        result = fetch_url("https://cloud.google.com/missing")
    assert not result.ok
    assert "404" in result.error


def test_fetch_all_aggregates_failures():
    def fake_get(url, **kwargs):
        if "good" in url:
            html = "<html><body><p>ok</p></body></html>"
            return MagicMock(status_code=200, text=html)
        return MagicMock(status_code=503, text="server error")
    with patch("curator.fetcher.httpx.get", side_effect=fake_get):
        results = fetch_all(["https://good.example", "https://bad.example"])
    assert len(results) == 2
    assert sum(r.ok for r in results) == 1
