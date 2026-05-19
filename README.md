# gcp-arch-expert-curator

Cloud Run jobs that curate the `canon/` knowledge base of [`csyn-portfolio/gcp-arch-expert`](https://github.com/csyn-portfolio/gcp-arch-expert).

## Modes

- **`promote`** — merge `canon/LESSONS_PENDING/<expert>/*.md` into `canon/<expert>/index.md`, atomically moving processed files to `canon/LESSONS_PROCESSED/<expert>/`. Opens a PR.
- **`freshness`** — fetch canonical GCP doc URLs for a specialist, ask Claude API (Opus 4.7) to flag staleness in the current canon, propose corrections. Opens a PR if changes are needed.

## Invocation

Manual only — no scheduler. Pete fires runs on-demand:

```bash
gcloud run jobs execute curator-promote \
  --region us-central1 --project gcp-arch-expert-platform \
  --update-env-vars EXPERT=iam-org-policy --wait

gcloud run jobs execute curator-freshness \
  --region us-central1 --project gcp-arch-expert-platform \
  --update-env-vars EXPERT=networking --wait
```

Set `DRY_RUN=true` to skip PR creation and dump the would-be PR to job logs.

## Development

```bash
pip install -e ".[dev]"
pytest -v
ruff check src tests
```

See `docs/DEPLOY.md` for the manual GitHub App setup runbook (one-time, Pete-only).

Design spec: [`csyn-portfolio/gcp-arch-expert/docs/superpowers/specs/2026-05-18-plan-b2-curator-jobs-design.md`](https://github.com/csyn-portfolio/gcp-arch-expert/blob/main/docs/superpowers/specs/2026-05-18-plan-b2-curator-jobs-design.md).
