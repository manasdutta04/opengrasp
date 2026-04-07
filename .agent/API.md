# OpenApply API (Commands)

This repo ships a Python CLI tool: `openapply` (see `pyproject.toml` entrypoint `cli.main:app`).

## Install

### Users (PyPI)
```bash
pip install openapply
```

### Contributors (editable)
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e .
python -m playwright install chromium
```

## Commands (core)
- `openapply setup`: bootstrap `config.yml`, `cv.md`, DB, and (if missing) `portals.yml`.
- `openapply doctor`: health checks (Ollama/Playwright/DB/config/portals/queue).
- `openapply scan [--auto]`: discover jobs from `portals.yml` (preferred) or DB portals.
- `openapply pipeline <url-or-jd-text>`: auto-pipeline (evaluate → report → CV PDF → cover letter).
- `openapply apply <url-or-jd-text>`: pipeline + optional HITL form draft (never submits).
- `openapply batch --min-score B --limit 20`: process `data/pipeline.md` in parallel.
- `openapply tracker`: interactive TUI tracker (cross-platform).
- `openapply learn <job-id> <outcome>`: log outcome + update weights.

## Commands (stretch parity)
- `openapply research <job-id>`: generate a research report for a stored job.
- `openapply outreach <job-id> --channel linkedin|email`: draft outreach.
- `openapply compare "12,15,22"`: compare 2+ stored jobs.

