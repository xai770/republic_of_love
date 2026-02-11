# 2026-02-10: VPN Fix and Pipeline Consolidation

**Author:** Arden (ℵ)

## Summary

Fixed the root cause of 403 rate limit failures: the `ArbeitsagenturScraper` was using Playwright when plain HTTP works. Consolidated the pipeline into a single `turing_daemon.py`.

## The Root Fix

### Problem
- AA was returning 403 rate limits
- VPN rotation wasn't happening
- The scraper used Playwright for no good reason (comment said "AA is SPA, needs JS")

### Discovery
The `aa_backfill` script worked fine with 50 workers using HTTP. Why?

AA does **server-side rendering** — job data is embedded in a `<script id="ng-state">` tag as JSON for Angular hydration. Plain HTTP can read that directly. **Playwright was never needed.**

### Fix
Rewrote [lib/scrapers/arbeitsagentur.py](../../lib/scrapers/arbeitsagentur.py):
- Removed Playwright dependency
- Uses `requests.get()` + ng-state JSON extraction
- Falls back to DOM parsing if ng-state missing
- Thread-safe for parallel execution

### Results
| Metric | Before (Playwright) | After (HTTP) |
|--------|---------------------|--------------|
| Workers | 1 (threading issues) | 20 |
| Speed | ~1/sec | ~15-20/sec |
| Success rate | Poor | 93%+ |

## Pipeline Consolidation

### Renamed bulk_daemon → turing_daemon
- `core/bulk_daemon.py` → `core/turing_daemon.py`
- Class `BulkDaemon` → `TuringDaemon`
- Lock file `.bulk_daemon.lock` → `.turing_daemon.lock`

### Archived old code
- `core/pull_daemon.py` → `archive/dead_scripts_20260210/`

### Updated references
- `scripts/nightly_fetch.sh` — uses turing_daemon now
- `actors/TEMPLATE_actor.py` — updated comments

## VPN Rotation Issue (KNOWN BUG)

VPN rotation via `vpn.sh rotate` kills **all** network connections:
- HTTP requests to AA fail mid-flight
- DB connections die → daemon crashes
- Even our chat session drops!

### Current workaround
Run multiple shorter batches instead of one long run. The daemon rotates VPN every 550 requests proactively, but this causes ~3% failures during rotation.

### TODO
- Add connection retry logic after VPN rotation
- Consider separate VPN for scraping vs local services
- Or: don't rotate VPN, just accept rate limits and retry later

## Files Changed

| File | Change |
|------|--------|
| [lib/scrapers/arbeitsagentur.py](../../lib/scrapers/arbeitsagentur.py) | Rewritten: Playwright → HTTP |
| [actors/postings__job_description_U.py](../../actors/postings__job_description_U.py) | WireGuard → OpenVPN via vpn.sh |
| [core/turing_daemon.py](../../core/turing_daemon.py) | Renamed from bulk_daemon |
| [scripts/nightly_fetch.sh](../../scripts/nightly_fetch.sh) | Updated to use turing_daemon |

## Current Status

```
08:14 — Daemon crashed after processing ~8500/15000 postings
         DB connection killed by VPN rotation
```

~15,000 postings still need descriptions. Run again to continue.

## Commands

```bash
# Run the daemon (processes in batches of 5000)
python3 core/turing_daemon.py --task_type 1299 --limit 5000 --workers 20

# Check progress
tail -f logs/nightly_fetch.log | grep -E "Progress|complete"

# Check remaining work
python3 -c "
from core.database import get_connection_raw, return_connection
conn = get_connection_raw()
cur = conn.cursor()
cur.execute('''SELECT COUNT(*) as cnt FROM postings 
    WHERE source = 'arbeitsagentur' 
    AND (job_description IS NULL OR LENGTH(COALESCE(job_description,'')) < 100)
    AND invalidated_at IS NULL''')
print(f'Need descriptions: {cur.fetchone()[\"cnt\"]}')
"
```

---

## Afternoon Session: Pipeline Cleanup

### nightly_fetch Failure Investigation

Ran nightly_fetch and got 24 failures:
- **8 external_partner_scrape failures** — HTTP 404/410 (expired jobs)
- **16 embedding_generator failures** — NaN (short text) + context exceeded (HTML bloat)

### MCP Browser Visualization

Used MCP browser to visualize the 16 failing postings:
- **6 short** (<150 chars) — legitimate minimal descriptions
- **10 long** (6K-35K chars) — HTML-bloated garbage

Decision: Invalidate the 10 bloated ones, keep the short ones.

### Comprehensive Pipeline Cleanup (8 Issues Fixed)

| # | Issue | Fix |
|---|-------|-----|
| 1 | Embedding work query included invalid postings | Updated `postings_for_matching` view to filter `posting_status != 'invalid'` |
| 2 | Short text (<150) caused failures | Return skip instead of fail, raised threshold 50→150 |
| 3 | Dead partner URLs kept retrying | 404/410 auto-invalidate with `skip_reason: 'job_expired_invalidated'` |
| 4 | Duplicate logging | Added `logger.propagate = False` in turing_daemon |
| 5 | Pipeline health showed stale embed count | Fixed via view update |
| 6 | Raw HTML saved in descriptions | Added `strip_html()` to aa_backfill + external_partners actors |
| 7 | ALREADY_RAN_TODAY created empty tickets | Moved check before ticket creation |
| 8 | 3,245 inconsistent berufenet rows | Fixed: `berufenet_id` set but `verified` NULL → set to 'lookup' |

### Playwright Removal

Discovered the old `postings__job_description_U.py` actor still used Playwright (causing 415 "missing descriptions"):
- 346 failed: HTTP 403 rate-limited
- 75 failed: JS render failed (Playwright container not found)
- 46 failed: Playwright async/sync conflict

**Fix:** Added daemon-compatible class to `postings__aa_backfill_U.py`:
```python
class PostingsAABackfillU:
    def __init__(self, db_conn=None):
        self.conn = db_conn
        self.input_data = {}
    
    def process(self) -> dict:
        # Uses requests + BeautifulSoup, no Playwright
```

Updated task_types:
```sql
UPDATE task_types 
SET script_path = 'actors/postings__aa_backfill_U.py'
WHERE task_type_id = 1299;  -- job_description_backfill
```

### Backlog Cleared

| Before | After |
|--------|-------|
| 415 missing descriptions | **0** |
| 16 embedding failures | **0** |

Batch run results:
- 252 AA direct postings → descriptions fetched
- 152 more via `--include-partners`
- 15 jobs invalidated (removed from AA)
- 212 external partner postings → marked `[EXTERNAL_PARTNER]`

### Additional Fixes

1. **SHORT_DESCRIPTION handling** — batch script now saves short descriptions instead of skipping:
   ```python
   elif status == 'SHORT_DESCRIPTION' and description:
       # Save short descriptions too - they're valid, just small
       update_posting_description(thread_conn, posting_id, description)
   ```

2. **Daemon class SHORT_DESCRIPTION** — returns success with note:
   ```python
   return {'success': True, 'posting_id': posting_id, 'chars': len(description), 'note': 'short'}
   ```

## Final Pipeline Health

```
⏳ PENDING WORK
----------------------------------------------------------------------
   🟢 Missing descriptions:     0
   🟢 Need berufenet match:     0
   🟢 Need LLM summary:         0
   🟡 Need embedding:           160  (new postings, will run next pipeline)
```

## Files Changed (Afternoon)

| File | Change |
|------|--------|
| `actors/postings__aa_backfill_U.py` | Added `PostingsAABackfillU` daemon class, fixed SHORT_DESCRIPTION |
| `actors/postings__embedding_U.py` | Added MAX_TEXT_LENGTH=6000 auto-invalidate, raised min 50→150 |
| `actors/postings__external_partners_U.py` | Added `strip_html()`, 404/410 auto-invalidate |
| `core/turing_daemon.py` | Added `logger.propagate = False` |
| `actors/postings__arbeitsagentur_CU.py` | ALREADY_RAN_TODAY before ticket creation |
| `actors/postings__deutsche_bank_CU.py` | ALREADY_RAN_TODAY before ticket creation |
| `migrations/20260210_fix_postings_for_matching_view.sql` | View changes documentation |
| DB: `task_types` | Updated script_path for job_description_backfill |
| DB: `postings` | Fixed 3,245 berufenet inconsistent rows |
| DB: `postings` | Invalidated 10 HTML-bloated postings |

---

## Evening Session: Domain Classification Root Fix

### Problem
BI dashboard showed Feb 08-09 as "unclassified" — 26K postings missing from domain distribution chart.

### Investigation Trail
1. First suspected `berufenet_id` — but that was 96% populated (via beruf→berufenet lookup)
2. Dashboard actually uses `domain_gate->>'primary_domain'` — completely different column
3. Feb 08-09 had ~10% domain_gate coverage vs 96% for earlier days

### The Insight (from Gershon)
**Berufenet already contains domain information via KLDB codes.** No embeddings needed.

We had two domain classification systems:
| System | Data Source | Speed | Use Case |
|--------|-------------|-------|----------|
| `populate_domain_gate.py` | KLDB codes from berufenet | Instant | 90%+ AA postings |
| `classify_domains_embeddings.py` | Job title embeddings | Slow | Non-berufenet postings |

The embedding classifier was being used for everything — wasteful and slow.

### Fix
Ran `python3 tools/populate_domain_gate.py --apply` — instant domain classification from KLDB codes.

**Before:**
```
Feb 08: 222/2330 (10%) have domain_gate
Feb 09: 2472/26458 (9%) have domain_gate
```

**After:**
```
Feb 08: 2245/2330 (96%) have domain_gate  
Feb 09: 24777/26458 (94%) have domain_gate
```

### Principle Learned
**Use authoritative data sources (KLDB) instead of inferring with embeddings.**

The KLDB (Klassifikation der Berufe) is the official German occupation classification:
- First 2 digits = occupation area (Berufsbereich)
- Maps directly to domains: 43 = IT, 72 = Finance, 82 = Healthcare, etc.

Embeddings are for semantic similarity, not categorical classification.

### Files Changed (Evening)

| File | Change |
|------|--------|
| DB: `postings` | Populated `domain_gate` for 54K+ postings via KLDB mapping |

### Domain Classification Actor (1304)
Added embedding-based domain classifier as a proper actor:
- **Actor 1304:** `domain_embedding_classifier`
- **Script:** `tools/classify_domains_embeddings.py`
- **Work query:** Finds postings without KLDB data
- **Coverage:** ~2,754 postings (non-berufenet)

Now runs automatically in turing_daemon after KLDB classifier (prio 20 → 25).

### Pipeline Documentation
Created comprehensive documentation: [docs/NIGHTLY_PIPELINE.md](../NIGHTLY_PIPELINE.md)
- Full pipeline flowchart
- All 7 enrichment actors with priorities
- Command modes (status, debug, tail)
- Troubleshooting guide

---

## Late Night Session: System Health Fixes

### Diagnostics Run
Ran system health check and found several issues:
- 71K failed tickets in 7 days (94% failure rate)
- Job description actor file renamed to `.BAD` but work query still active
- Mismatch between work query (<100 chars) and actor check (truthy)
- 4,864 unmatched beruf titles needing synonyms
- Stale `.BAD` and `.bak` files in workspace

### Fixes Applied

#### 1. Job Description Actor Restored
- Restored `actors/postings__job_description_U.py` from `.BAD`
- **Bug fix:** Changed preflight check to match work query threshold:
  ```python
  # Before: rejected any posting with job_description
  if posting['job_description']:
  
  # After: only reject if >= MIN_DESCRIPTION_LENGTH (100 chars)
  if len(desc) >= MIN_DESCRIPTION_LENGTH:
  ```
- Work query finds `LENGTH < 100`, actor now only skips if `length >= 100`

#### 2. Berufenet Synonyms Added
Added 10 synonyms for top unmatched job titles:
| AA Title | Berufenet Entry |
|----------|-----------------|
| ERP-Anwendungsentwickler/in | 15260 (Softwareentwickler/in) |
| Anwendungsberater/in | 134898 (Berater/in - digitale Transformation) |
| Anwendungssystemberater/in | 134898 |
| Second-Level-Supporter/in | 2927 (IT-System-Elektroniker/in) |
| ERP-Systembetreuer/in | 2927 |
| Anwendungssystemadministrator/in | 2927 |
| Datenbankadministrator/in | 15260 |
| IT-Vertriebsbeauftragte/r | 15907 (Vertriebsingenieur/in) |
| IT-Lösungsentwickler/in | 15260 |
| Fachkraft - Pflegeassistenz | 9063 (Altenpflegehelfer/in) |

Total synonyms: 261 → **271**

#### 3. Ollama Verified
- Status: ✅ Running (5 days uptime)
- `bge-m3:567m`: ✅ Available (1.2 GB)
- Embedding failures: **None in last 7 days** (earlier stats were aggregated from other actors)

#### 4. Stale Files Archived
Moved to `archive/stale_backups_20260210/`:
- `postings__job_description_U.py.BAD`
- `workflow_starter.py.bak`

### Summary
| Issue | Status |
|-------|--------|
| Job description actor missing | ✅ Restored + fixed |
| Work query / actor mismatch | ✅ Fixed |
| Unmatched beruf titles | ✅ +10 synonyms |
| Ollama model issues | ✅ Verified OK |
| Stale backup files | ✅ Archived |

---

## External Partner Scraper Expansion

### Context
External partner postings have `job_description = '[EXTERNAL_PARTNER]'` — meaning the description lives on the partner site, not AA. We need scrapers to fetch them.

### Architecture
**One actor dispatches to many scrapers:**
```
external_partner_scraper (actor 1305)
    └── detect_scraper_from_url(url) → scraper_key
         └── SCRAPER_REGISTRY[key] → scraper class
              └── scraper.scrape(url) → description
```

No need for an actor per site. Just add:
1. Scraper class in `lib/scrapers/`
2. Domain detection in `detect_scraper_from_url()`
3. Registry entry in `lib/scrapers/__init__.py`

### New Scrapers Added

| Scraper | File | Pattern | Domains | Postings |
|---------|------|---------|---------|----------|
| InteramtScraper | `lib/scrapers/interamt.py` | article/main HTML | interamt.de | 19 |
| ArticleScraper | `lib/scrapers/article_generic.py` | article/main HTML | hokify.de, crabster.de, awo-jobs.de, jobs4us.de | 43 |
| + jsonld_generic | (existing) | JSON-LD | empfehlungsbund.de | 16 |

### Scraper Patterns Summary

| Pattern | When to Use | Speed | Sites |
|---------|-------------|-------|-------|
| `jsonld_generic` | site has `<script type="application/ld+json">` with JobPosting | Fast (HTTP) | jobanzeiger.de, jobblitz.de, kalaydo.de, yourfirm.de, stellenanzeigen.de, empfehlungsbund.de |
| `playwright_jsonld` | JSON-LD but needs JS render (SPA) | Slow | germantechjobs.de |
| `jobfish` | Cloudflare protected + JSON-LD | Slow (Firefox) | job.fish |
| `article_generic` | No JSON-LD, uses semantic `<article>`/`<main>` | Fast (HTTP) | hokify.de, crabster.de, awo-jobs.de, jobs4us.de, interamt.de |
| Custom API | Site has undocumented API | Fast | compleet.com (via germanpersonnel.de) |
| Custom HTML | Site-specific selectors | Fast | bewerbung.jobs, persyjobs, jobexport |

### Coverage Results

| Metric | Before | After |
|--------|--------|-------|
| Covered postings | 8,722 | 8,765 |
| Coverage % | 98.6% | **99.0%** |
| Uncovered | 128 | 85 |

### Remaining Uncovered (85 postings)
Sites with issues not worth fixing:
- `jobs-deutschland.de` (15) — SSL certificate expired
- `deutschland-stellenmarkt.de` (14) — minimal HTML, no patterns
- `joboo.online` (8) — returns 403
- `jobcluster.de` (6) — no article/JSON-LD
- Various small sites (42) — <5 postings each

### Files Changed

| File | Change |
|------|--------|
| `lib/scrapers/interamt.py` | NEW: public sector (interamt.de) |
| `lib/scrapers/article_generic.py` | NEW: generic article/main extraction |
| `lib/scrapers/__init__.py` | Added InteramtScraper, ArticleScraper to registry |
| `actors/postings__external_partners_U.py` | Added domain detection for new sites |

### Auto-Detection for Unknown Domains

Added automatic pattern detection for sites not in the hardcoded domain lists:

```python
# Strategy 3: Auto-detect pattern for unknown domains
# Try JSON-LD first (Google requires it), then article/main
if not scraper_name:
    for pattern in ['jsonld_generic', 'article_generic']:
        result = SCRAPER_REGISTRY[pattern]().scrape(url)
        if result.get('success') and len(result.get('description', '')) >= 100:
            scraper_name = pattern
            break
```

**Benefits:**
- No need to manually add domains to lists
- New partner sites auto-discovered at runtime
- Zero-config for any site using JSON-LD or semantic HTML

**Test Results:**
| Domain | Auto-Detected Pattern |
|--------|----------------------|
| sparkasse.de | jsonld_generic ✅ |
| heyjobs.co | article_generic ✅ |
| academicwork.de | article_generic ✅ |
| deinjob.de | none ❌ |
| stellenanzeigen-markt.de | none ❌ |

**Coverage with Auto-Detection:**
- Known domains: 8,765 / 8,850 (99.0%)
- Auto-detection attempts: 85 postings
- Expected to succeed: ~5-10 (sites with standards-compliant markup)
- Will fail: ~75 (403 blocks, SSL errors, JS-only sites)

— ℵ
