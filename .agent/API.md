# opengrasp API (Commands)

This repo ships a Python CLI tool: `opengrasp` (see `pyproject.toml` entrypoint `cli.main:app`).

## Install

### Users (PyPI)
```bash
pip install opengrasp
```

### Contributors (editable)
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e .
python -m playwright install chromium
```

## Commands (core)
- `opengrasp setup`: bootstrap `config.yml`, `cv.md`, DB, and (if missing) `portals.yml`.
- `opengrasp doctor`: health checks (Ollama/Playwright/DB/config/portals/queue).
- `opengrasp scan [--auto]`: discover jobs from `portals.yml` (preferred) or DB portals.
- `opengrasp pipeline <url-or-jd-text>`: auto-pipeline (evaluate → report → CV PDF → cover letter).
- `opengrasp apply <url-or-jd-text>`: pipeline + optional HITL form draft (never submits).
- `opengrasp batch --min-score B --limit 20`: process `data/pipeline.md` in parallel.
- `opengrasp tracker`: interactive TUI tracker (cross-platform).
- `opengrasp learn <job-id> <outcome>`: log outcome + update weights.

## Commands (stretch parity)
- `opengrasp research <job-id>`: generate a research report for a stored job.
- `opengrasp outreach <job-id> --channel linkedin|email`: draft outreach.
- `opengrasp compare "12,15,22"`: compare 2+ stored jobs.

