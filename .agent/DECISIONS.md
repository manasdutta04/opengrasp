# Decisions (ADR-lite)

## Local-first constraint
- All inference is via local Ollama by default.
- No required cloud keys.

## Source of truth for scanning
- Prefer `portals.yml` (career-ops style) when present.
- Fall back to DB `portals` table for backward compatibility.

## Scan history format
- `data/scan-history.tsv` is the primary dedupe log.
- If legacy `data/scan-history.md` exists, we still read it for dedupe and append to it for visibility.

## Tracker UI
- Use Textual for a cross-platform terminal UI (tabs, palette, preview pane).

## Prompt strategy
- Keep prompts in `agent/prompts/*.md` so they are versioned and reviewable.

