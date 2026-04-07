# Progress Log

Update this file whenever behavior changes, commands are added/removed, or data formats migrate.

## Latest changes
- Added `portals.yml` (preferred scan config) + templates.
- Scanner now scrapes real JDs and writes `data/scan-history.tsv` for dedupe.
- Added `openapply pipeline` (auto-pipeline) and refactored core pipeline into `cli/flows/offer_pipeline.py`.
- Replaced Windows-only tracker with cross-platform Textual TUI (tabs + palette + preview).
- Added `openapply doctor` and basic unit tests under `tests/`.
- Added stretch commands: `research`, `outreach`, `compare`.

