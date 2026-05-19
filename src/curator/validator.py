"""Hard schema + soft heuristic validation for curator-generated canon."""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field

import yaml

REQUIRED_SECTIONS = (
    re.compile(r"^# .+ — canon\b", re.MULTILINE),
    re.compile(r"^## Manifest\b", re.MULTILINE),
    re.compile(r"^## Pillar-weighted defaults\b", re.MULTILINE),
    re.compile(r"^## Patterns\b", re.MULTILINE),
)
MIN_SIZE = 1024
MAX_SIZE = 51_200
PLACEHOLDERS = ("TBD", "TODO", "FIXME", "[…]", "[...]")
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


class ValidationError(Exception):
    """Hard validation failure — job exits 1, no PR opened."""


@dataclass
class SoftWarning:
    message: str


@dataclass
class ValidationResult:
    hard_errors: list[str] = field(default_factory=list)
    soft_warnings: list[SoftWarning] = field(default_factory=list)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_PATTERN.match(text)
    if not m:
        raise ValidationError("missing YAML frontmatter")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise ValidationError(f"frontmatter not valid YAML: {e}") from e
    if not isinstance(meta, dict):
        raise ValidationError("frontmatter is not a mapping")
    return meta, m.group(2)


def _check_version_bumped(new: str, current: str) -> None:
    def parse(v: str) -> tuple[int, ...]:
        return tuple(int(p) for p in str(v).split("."))
    if parse(new) <= parse(current):
        raise ValidationError(
            f"canon_version not bumped: proposed {new} <= current {current}"
        )


def validate(
    proposed: str,
    current_version: str,
    today: datetime.date,
    expert: str,
    current_size: int | None = None,
) -> ValidationResult:
    """Validate proposed canon content. Raise ValidationError on hard fail.

    Returns ValidationResult with soft_warnings populated.
    """
    size = len(proposed.encode("utf-8"))
    if size < MIN_SIZE:
        raise ValidationError(f"size {size} below MIN_SIZE {MIN_SIZE}")
    if size > MAX_SIZE:
        raise ValidationError(f"size {size} above MAX_SIZE {MAX_SIZE}")

    meta, body = _parse_frontmatter(proposed)

    for required in ("expert", "canon_version", "last_updated"):
        if required not in meta:
            raise ValidationError(f"frontmatter missing required key: {required}")

    if meta["expert"] != expert:
        raise ValidationError(
            f"frontmatter expert {meta['expert']!r} != target {expert!r}"
        )

    try:
        last = meta["last_updated"]
        if isinstance(last, datetime.date):
            last_date = last
        else:
            last_date = datetime.date.fromisoformat(str(last))
    except (ValueError, TypeError) as e:
        msg = f"last_updated not a parseable date: {meta.get('last_updated')!r}"
        raise ValidationError(msg) from e
    if last_date != today:
        raise ValidationError(f"last_updated {last_date.isoformat()} != today {today.isoformat()}")

    _check_version_bumped(str(meta["canon_version"]), current_version)

    for pattern in REQUIRED_SECTIONS:
        if not pattern.search(proposed):
            raise ValidationError(f"required section missing: {pattern.pattern}")

    result = ValidationResult()

    for token in PLACEHOLDERS:
        if token in body:
            result.soft_warnings.append(SoftWarning(f"placeholder token present: {token}"))

    if current_size is not None and size > current_size * 3:
        result.soft_warnings.append(
            SoftWarning(f"size delta exceeds 3x: {size} bytes vs current {current_size}")
        )

    return result
