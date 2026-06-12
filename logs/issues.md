# Issues Log

## Open

### 2026-06-11 — No tab found for 2026-06-11
**Error:** `ValueError: No tab found for Nishant on 2026-06-11`
**Trigger:** `/update-by-date` or `/process-recent` called for today's date
**Cause:** No tab exists in the Google Sheet whose date range covers June 11, 2026
**Fix:** Create a new tab in the sheet covering this date (e.g. `Jun8/14`)
**Note:** Logic also breaks if the tab name format differs from the expected pattern — `_parse_tab_date_range` in `sheets/client.py` uses `re.fullmatch(r"([A-Za-z]+)(\d+)", ...)` so any variation (e.g. `Jun 8/14`, `Jun08/14`, `June8/14`) will silently be skipped and produce the same "No tab found" error

---

## Resolved

