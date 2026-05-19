"""canon/_meta/manifest.json mutation helpers."""
from __future__ import annotations

import copy
from typing import Literal


def bump_specialist(
    manifest: dict,
    expert: str,
    new_date: str,
    bump: Literal["patch", "minor", "major"] = "patch",
) -> dict:
    """Return a new manifest dict with the given specialist's version + date bumped."""
    out = copy.deepcopy(manifest)
    if expert not in out.get("experts", {}):
        raise KeyError(f"manifest has no expert {expert!r}")

    parts = [int(p) for p in str(out["experts"][expert]["version"]).split(".")]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts[:3]
    if bump == "patch":
        patch += 1
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"unknown bump {bump!r}")

    out["experts"][expert]["version"] = f"{major}.{minor}.{patch}"
    out["experts"][expert]["last_updated"] = new_date
    return out
