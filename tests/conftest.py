import json
from pathlib import Path

import pytest


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """Simulate a cloned plugin repo with iam-org-policy expert set up."""
    repo = tmp_path / "repo"
    (repo / "canon" / "iam-org-policy").mkdir(parents=True)
    (repo / "canon" / "LESSONS_PENDING" / "iam-org-policy").mkdir(parents=True)
    (repo / "canon" / "LESSONS_PROCESSED" / "iam-org-policy").mkdir(parents=True)
    (repo / "canon" / "_meta").mkdir(parents=True)
    _index = (
        '---\nexpert: iam-org-policy\ncanon_version: "0.0.2"\n'
        'last_updated: "2026-05-17"\nstatus: stub\n---\n\n'
        "# IAM & org policy — canon\n\n## Manifest\n\n"
        "## Pillar-weighted defaults\n\n## Patterns\n\n"
    )
    (repo / "canon" / "iam-org-policy" / "index.md").write_text(_index)
    (repo / "canon" / "LESSONS_PENDING" / "iam-org-policy" / "lesson1.md").write_text(
        "Some pending lesson"
    )
    (repo / "canon" / "_meta" / "manifest.json").write_text(json.dumps({
        "schema_version": 1,
        "experts": {
            "iam-org-policy": {
                "version": "0.0.2",
                "last_updated": "2026-05-17",
                "status": "stub",
            }
        },
    }))
    return repo
