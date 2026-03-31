# Release PR Template

Use this template whenever opening a release PR (`dev → main`). Reference `release-notes.md` and verify QA steps before merging.

## Summary

- Describe what changed (e.g., alerts, APIs, docs).
- Link to the release note: [release-notes.md](release-notes.md).
- Note any rollout considerations (e.g., Alertmanager rules, Docker image tag).

## Verification

- `uv run poe lint`
- `./.venv/bin/pytest -v`
- `docker compose build`
- Reload Prometheus/Alertmanager (see `observability.md` → "Reloading Alert Rules").

## QA Checklist

- [ ] Release note referenced above
- [ ] Alert rules reloaded in target environment
- [ ] Docker image tagged and pushed (`ghcr.io/thedataenginex/dex:sha-<8-char-sha>`)
- [ ] Observability and QA docs updated as needed
