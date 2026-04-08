# opengrasp Architecture

opengrasp is a local-first autonomous job search agent.
It runs on your machine, uses Ollama for inference, and keeps Human In The Loop (HITL) at all critical decision points.

## System Overview

Open Grasp is organized into four major layers:

1. CLI layer (`cli/`):
- User entrypoint (`opengrasp`)
- Command orchestration (`setup`, `apply`, `scan`, `batch`, `tracker`, `learn`)
- Rich terminal UX and confirmations

2. Agent layer (`agent/`):
- LLM adapter (`ollama_client.py`)
- Evaluator (`evaluator.py`) for 10-dimension scoring
- CV tailoring + PDF renderer (`cv_builder.py`)
- Web automation (`scraper.py`) for JD extraction and draft form filling
- Discovery engine (`scanner.py`) for portal scanning
- Batch executor (`batch.py`) for parallel processing

3. Memory layer (`memory/`):
- SQLAlchemy ORM models and DB session management
- SQLite database for jobs, evaluations, artifacts, applications, outcomes, weights, portals
- Evolving scoring weights based on outcomes

4. Artifact/config layer:
- Prompt files (`agent/prompts/*.md`)
- User CV (`cv.md`)
- Config (`config.yml`)
- Generated outputs (`output/`, `reports/`)
- Operational markdown logs (`data/*.md`)

## Runtime Flow Between Components

### Apply flow (`opengrasp apply <url-or-jd-text>`)

1. CLI command receives URL or JD text.
2. Scraper extracts structured JD if URL is provided.
3. Job record is inserted/updated in DB (`jobs`).
4. Evaluator loads prompt from `agent/prompts/evaluate.md` and calls Ollama.
5. Evaluator computes weighted score using `scoring_weights`, applies gate cap logic, writes markdown report, persists `evaluations`.
6. CV builder loads prompt from `agent/prompts/tailor_cv.md`, tailors CV, renders HTML template (`templates/cv.html`), exports PDF, persists `cvs`.
7. Cover letter is generated from `agent/prompts/cover_letter.md`.
8. CLI displays diff and asks user whether to apply now.
9. If user chooses yes and target is URL, scraper fills form drafts and returns all values for review.
10. Application row is persisted with explicit `auto_applied=False`; status only advances with human review confirmation.

### Scan flow (`opengrasp scan [--auto]`)

1. Scanner reads active portals from DB (`portals`).
2. Scanner loads `agent/prompts/scan_query.md` to generate per-portal queries.
3. Scanner collects listing links and scrapes candidate JDs.
4. Dedup checks run against:
- `jobs` table (`url`, normalized `company+role`)
- `data/scan-history.md`
5. New jobs are stored as `status=new`.
6. Every scan action is appended to `data/scan-history.md`.
7. `--auto` mode evaluates discovered jobs and appends B+ URLs to `data/pipeline.md`.

### Batch flow (`opengrasp batch`)

1. Batch command reads URLs from `data/pipeline.md` Pending.
2. `agent.batch.BatchProcessor` runs worker pool (asyncio, configurable concurrency).
3. Each worker executes: scrape -> evaluate -> filter by grade -> CV generation.
4. Failures are isolated per URL and do not block other workers.
5. Resumable behavior skips already completed URLs (existing evaluation + CV).
6. Pipeline markdown is updated: processed URLs moved to Processed section.

### Learn flow (`opengrasp learn <job-id> <outcome>`)

1. Outcome is logged to `applications` + `outcomes`.
2. Latest evaluation dimensions are analyzed.
3. `scoring_weights` are adjusted and normalized.
4. Weight updates are persisted for future evaluations.

## Memory Layer Design

The memory layer is SQLite + SQLAlchemy.

### Core entities

- `jobs`: canonical job records and lifecycle status.
- `evaluations`: per-job 10-dimension scoring snapshots and report path.
- `cvs`: generated tailored CV artifacts and metadata.
- `applications`: application execution records and review state.
- `outcomes`: post-application feedback events (interview/rejected/offer/ghosted).
- `scoring_weights`: mutable per-dimension weights used by evaluator.
- `portals`: configured sources for autonomous scanning.

### Why this design

- Separates raw opportunities (`jobs`) from analysis (`evaluations`) and action (`applications`).
- Supports repeat evaluations and artifact versioning.
- Supports learning loop by preserving outcomes over time.
- Keeps all user-sensitive data local.

## HITL Philosophy and Safety Controls

opengrasp enforces the rule: AI analyzes, human decides.

Implemented controls:

1. Never auto-submit:
- `scraper.fill_form()` always returns `requires_review=True`.
- No submit click is executed.
- Apply logging marks `auto_applied=False`.

2. Explicit confirmation gates:
- `apply` command prompts before continuing for low score (< 3.0).
- `apply` command prompts before form handling.
- Human review confirmation is separately captured before marking as applied.

3. Transparent outputs:
- Evaluation report saved to `reports/`.
- CV diff shown against base `cv.md`.
- Filled fields are shown in terminal for human audit.

## Prompt Loading and Versioning

Prompts are stored as markdown files under `agent/prompts/` and loaded at runtime.

Benefits:

- Prompt updates are code-reviewed like source changes.
- No hardcoded prompt strings in Python logic.
- Easier experimentation and model tuning.
- Prompt files can be semantically versioned using git tags/commits.

Current prompt set:

- `evaluate.md`
- `tailor_cv.md`
- `cover_letter.md`
- `apply_form.md`
- `scan_query.md`
- `deep_research.md`

## CV Tailoring Pipeline (Step-by-Step)

1. Load base CV from `cv.md`.
2. Fetch job + evaluation context from DB.
3. Call tailoring prompt (`tailor_cv.md`) for archetype and keyword plan.
4. Build keyword set (LLM output + deterministic JD fallback) targeting 15-20 keywords.
5. Detect language and paper format (A4/Letter).
6. Reorder experience bullets by JD relevance (no deletion).
7. Inject keywords naturally into summary and first bullet per role.
8. Render Jinja HTML template (`templates/cv.html`).
9. Generate PDF via Playwright.
10. Persist artifact metadata in `cvs` table.
11. Save markdown + PDF to `output/`.

## Local-First and Failure Modes

opengrasp is designed to degrade gracefully.

- If Ollama is unavailable:
  - Commands return clear actionable errors.
  - CLI remains usable and help screens load.
- If Playwright is missing:
  - Import-time crashes are avoided via lazy imports.
  - Commands emit dependency guidance when execution reaches browser steps.
- If portals are missing:
  - Scan command exits with clear setup guidance.

## Extensibility Points

1. Add portal adapters by extending `agent/scraper.py` selectors/strategies.
2. Extend scoring dimensions by:
- updating prompt contract
- adding DB columns
- updating evaluator calculations
3. Add new output templates in `templates/`.
4. Add additional learning heuristics in `learn` command.

## Data and Privacy Boundaries

- Inference: local Ollama endpoint (`localhost` by default)
- Database: local SQLite file under `data/`
- Artifacts: local files in `output/` and `reports/`
- Secrets/config: local `config.yml`

No cloud API key is required by architecture.
