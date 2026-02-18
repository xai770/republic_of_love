# 2026-02-18 — Pipeline Reliability

**Session start:** ~05:15 CET (early morning, pipeline monitoring)
**System time at writing:** Di 18. Feb 05:35 CET

---

## Starting state

| Metric | Value | Δ from yesterday |
|--------|-------|-----------------|
| Total postings | 271,812 | +11,608 |
| Active postings | 258,140 | +9,492 |
| Embeddings | 283,349 | +1,021 |
| No berufenet | 18,693 | -86 |
| No description | 893 | -12 |
| Profiles | 6 | — |
| OWL entries | 21,419 | — |

**Overnight pipeline:** Ran at 23:50 via cron, completed successfully.
11,608 new postings ingested. However, **no log output was captured** —
the `turing_fetch.sh` logging bug meant cron mode wrote to nowhere.

**Scraper health check:** Crashed every night since creation (Feb 10) —
`ModuleNotFoundError: No module named 'playwright'`. Playwright installed
in user site-packages but not accessible to venv's python3.

---

## Work log

### 1. Fix: turing_fetch.sh logging (both interactive and cron)

**Problem:** The script used `if [ -t 1 ]` to conditionally activate
`tee` logging. This was added on Feb 17 to prevent double-writing when
run as `./turing_fetch.sh >> logfile 2>&1`. But the cron entry runs
without any redirect AND without a TTY, so output went nowhere.

**Fix:** Always redirect to LOGFILE. Interactive mode uses `tee` for
dual output (screen + file). Cron mode writes to file only. Comments
updated to explain the logic.

### 2. Fix: scraper health check playwright import

**Problem:** `lib/scrapers/base.py` imports `playwright.sync_api` at module
level. The cron calls `./venv/bin/python3` which doesn't include user
site-packages where playwright lives. The entire scraper registry becomes
unimportable.

**Fix:** Made playwright import lazy — only loaded when `_get_browser()`
is actually called. Type hints use `TYPE_CHECKING` guard. Non-playwright
scrapers (the majority) work without playwright installed. Health check
can now import the registry and test all non-playwright scrapers, reporting
clear errors for playwright-dependent ones.

---

## Commits

_(to be filled as work progresses)_

---

## End-of-day checklist

- [ ] All fixes tested
- [ ] Tests pass
- [ ] Committed and pushed
- [ ] Directives reviewed
