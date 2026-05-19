import json
from pathlib import Path

import pytest

from curator.manifest import bump_specialist

FIXTURE = Path(__file__).parent / "fixtures" / "manifest.json"


def _load() -> dict:
    return json.loads(FIXTURE.read_text())


def test_bump_patch_version():
    m = _load()
    updated = bump_specialist(m, expert="iam-org-policy", new_date="2026-05-19", bump="patch")
    assert updated["experts"]["iam-org-policy"]["version"] == "0.0.3"
    assert updated["experts"]["iam-org-policy"]["last_updated"] == "2026-05-19"
    # Other specialists untouched
    assert updated["experts"]["networking"]["version"] == "0.0.1"


def test_bump_unknown_expert_raises():
    m = _load()
    with pytest.raises(KeyError):
        bump_specialist(m, expert="not-a-thing", new_date="2026-05-19", bump="patch")


def test_bump_minor_resets_patch():
    m = _load()
    updated = bump_specialist(m, expert="iam-org-policy", new_date="2026-05-19", bump="minor")
    assert updated["experts"]["iam-org-policy"]["version"] == "0.1.0"


def test_input_dict_not_mutated():
    m = _load()
    bump_specialist(m, expert="iam-org-policy", new_date="2026-05-19", bump="patch")
    assert m["experts"]["iam-org-policy"]["version"] == "0.0.2"
