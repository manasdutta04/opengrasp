# OpenApply Architecture (Repo Guide)

## Layers
- `cli/`: Typer CLI + interactive terminal UX (Textual tracker).
- `agent/`: LLM adapters, scanning, scraping, evaluation, CV building, prompts/templates.
- `memory/`: SQLite + SQLAlchemy models.

## Data + artifacts
- `config.yml`: user settings (models, targets, scoring).
- `portals.yml`: scanner config (preferred).
- `cv.md`: base CV in markdown.
- `data/openapply.db`: SQLite DB.
- `data/pipeline.md`: queue for batch processing.
- `data/scan-history.tsv`: dedupe history (machine-friendly).
- `reports/`: evaluation + research markdown.
- `output/`: generated CV markdown/PDF + cover letters + outreach.

## Runtime flows
### scan
`cli/commands/scan.py` → `agent/scanner.py` → `agent/scraper.py` → persist jobs + write scan history.

### pipeline/apply
`cli/flows/offer_pipeline.py` → `agent/evaluator.py` + `agent/cv_builder.py` (+ cover letter) → persist eval/CV + artifacts.
`apply` optionally calls `agent/scraper.py fill_form()` to draft fields (never submits).

### tracker
`cli/commands/tracker.py` → `cli/tui/tracker_app.py` → reads DB, previews reports, logs outcomes, can jump into `apply`.

