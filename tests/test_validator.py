import datetime
from pathlib import Path

import pytest

from curator.validator import (
    SoftWarning,
    ValidationError,
    validate,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_valid_canon_passes_hard_checks():
    result = validate(
        proposed=_load("canon-valid.md"),
        current_version="0.0.2",
        today=datetime.date(2026, 5, 18),
        expert="iam-org-policy",
    )
    assert result.hard_errors == []


def test_missing_section_fails():
    with pytest.raises(ValidationError) as exc:
        validate(
            proposed=_load("canon-missing-section.md"),
            current_version="0.0.2",
            today=datetime.date(2026, 5, 18),
            expert="iam-org-policy",
        )
    assert "## Patterns" in str(exc.value)


def test_bad_frontmatter_fails():
    with pytest.raises(ValidationError) as exc:
        validate(
            proposed=_load("canon-bad-frontmatter.md"),
            current_version="0.0.2",
            today=datetime.date(2026, 5, 18),
            expert="iam-org-policy",
        )
    assert "last_updated" in str(exc.value) or "frontmatter" in str(exc.value).lower()


def test_no_version_bump_fails():
    text = _load("canon-valid.md").replace('canon_version: "0.0.3"', 'canon_version: "0.0.2"')
    with pytest.raises(ValidationError) as exc:
        validate(proposed=text, current_version="0.0.2",
                 today=datetime.date(2026, 5, 18), expert="iam-org-policy")
    assert "canon_version" in str(exc.value)


def test_wrong_date_fails():
    text = _load("canon-valid.md")
    with pytest.raises(ValidationError) as exc:
        validate(proposed=text, current_version="0.0.2",
                 today=datetime.date(2026, 5, 19), expert="iam-org-policy")
    assert "last_updated" in str(exc.value)


def test_too_small_fails():
    tiny = '---\nexpert: foo\ncanon_version: "0.0.3"\nlast_updated: "2026-05-18"\n---\n'
    with pytest.raises(ValidationError):
        validate(proposed=tiny, current_version="0.0.2",
                 today=datetime.date(2026, 5, 18), expert="foo")


def test_too_large_fails():
    huge = _load("canon-valid.md") + ("X" * 60_000)
    with pytest.raises(ValidationError) as exc:
        validate(proposed=huge, current_version="0.0.2",
                 today=datetime.date(2026, 5, 18), expert="iam-org-policy")
    assert "size" in str(exc.value).lower()


def test_placeholder_yields_soft_warning():
    text = _load("canon-valid.md").replace("Some content.", "Some content. TODO: fill in.")
    result = validate(proposed=text, current_version="0.0.2",
                      today=datetime.date(2026, 5, 18), expert="iam-org-policy")
    assert result.hard_errors == []
    assert any(isinstance(w, SoftWarning) and "TODO" in w.message for w in result.soft_warnings)


def test_size_growth_3x_yields_soft_warning():
    text = _load("canon-valid.md")
    grown = text + ("Repeated paragraph. " * 200)
    result = validate(
        proposed=grown,
        current_version="0.0.2",
        today=datetime.date(2026, 5, 18),
        expert="iam-org-policy",
        current_size=len(text),
    )
    assert any("size" in w.message.lower() for w in result.soft_warnings)
