"""GitHub App JWT signing + installation token minting + PR creation."""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
import jwt

GITHUB_API = "https://api.github.com"


def _build_jwt(app_id: int, private_key_pem: str, now: int | None = None) -> str:
    """Sign a 9-minute JWT for GitHub App auth. `now` injectable for tests."""
    if now is None:
        now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 540, "iss": str(app_id)}
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


@dataclass
class GitHubApp:
    app_id: int
    private_key_pem: str
    installation_id: int

    def installation_token(self) -> str:
        jwt_token = _build_jwt(self.app_id, self.private_key_pem)
        url = f"{GITHUB_API}/app/installations/{self.installation_id}/access_tokens"
        r = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        if r.status_code == 401:
            raise RuntimeError(
                "GH App token mint returned 401. Rotate the private key in Secret Manager."
            )
        if r.status_code != 201:
            raise RuntimeError(f"GH App token mint failed: {r.status_code} {r.text[:200]}")
        return r.json()["token"]

    def create_pull_request(
        self,
        *,
        repo: str,  # e.g. "csyn-portfolio/gcp-arch-expert"
        head: str,
        base: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict:
        token = self.installation_token()
        url = f"{GITHUB_API}/repos/{repo}/pulls"
        r = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"title": title, "body": body, "head": head, "base": base},
            timeout=30.0,
        )
        if r.status_code != 201:
            raise RuntimeError(f"PR creation failed: {r.status_code} {r.text[:200]}")
        pr = r.json()
        if labels:
            httpx.post(
                f"{GITHUB_API}/repos/{repo}/issues/{pr['number']}/labels",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                json={"labels": labels},
                timeout=30.0,
            )
        return pr
