# Partner Site Scrapers - February 7, 2026

## Summary

Built 6 new HTTP-based scrapers to handle external partner job postings that were previously falling through (invalidated because no job_description). Total partner postings now covered: **1,011**.

## The Problem

Discovered 1,162 postings with direct partner URLs (not arbeitsagentur.de) were being invalidated because we had no way to fetch their job descriptions. These came from AA's "Bewerben über" links pointing to external job portals.

## Scrapers Built

| Scraper | File | Postings | Method |
|---------|------|----------|--------|
| helixjobs | `lib/scrapers/helixjobs.py` | 344 | JSON-LD schema.org/JobPosting |
| gutejobs | `lib/scrapers/gutejobs.py` | 201 | JS config extraction (elementorFrontendConfig) |
| jobboersedirekt | `lib/scrapers/jobboersedirekt.py` | 183 | JSON-LD schema.org/JobPosting |
| hogapage | `lib/scrapers/hogapage.py` | 112 | JSON-LD (unquoted type attribute) |
| europersonal | `lib/scrapers/europersonal.py` | 86 | JSON-LD schema.org/JobPosting |
| finestjobs | `lib/scrapers/finestjobs.py` | 84 | HTML extraction (scheme-text divs) |
| jobvector | `lib/scrapers/jobvector.py` | 1 | JSON-LD (already existed) |

**Total: 1,011 postings**

## Key Discovery

Most partner sites use **schema.org/JobPosting** JSON-LD. This is a structured data format Google requires for job search indexing. The pattern is consistent:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "...",
  "description": "...",  // <-- This is what we extract
  ...
}
</script>
```

Pure HTTP requests work - no Playwright needed for any of these sites.

## Files Modified

- `lib/scrapers/__init__.py` - Added all 6 new scrapers to SCRAPER_REGISTRY
- `actors/postings__external_partners_U.py` - Added domain detection for all sites in `detect_scraper_from_url()`

## Architecture Pattern

```
URL → detect_scraper_from_url() → scraper class → .scrape(url) → {success, description, error}
```

Each scraper implements the same interface:
```python
def scrape(self, url: str) -> dict:
    return {
        'success': bool,
        'description': str,  # HTML content
        'error': str
    }
```

## Remaining: db.wd3.myworkdayjobs.com

Investigated the 1,882 postings pointing to Deutsche Bank's Workday instance.

**Finding:** All Workday URLs (`db.wd3.myworkdayjobs.com`) come from `source='deutsche_bank'`, not from AA. This means:

1. We already scrape these directly via `actors/postings__deutsche_bank_CU.py`
2. No additional scraper needed
3. Two portals, same jobs - confirmed

Stats:
- 3,804 total `deutsche_bank` postings
- 3,804 have Workday external URLs (100% overlap)
- 3,712 active with descriptions
- 92 invalidated

**Conclusion:** No action required. Deutsche Bank pipeline already handles these.

## Architecture: Modular nightly_fetch.sh

Refactored `scripts/nightly_fetch.sh` (545 lines) into modular structure:

```
scripts/
├── nightly_fetch_v2.sh      # 90 lines - thin orchestrator
└── nightly/
    ├── common.sh            # 91 lines - shared functions (log, lock, cleanup)
    ├── 01_fetch.sh          # 30 lines - AA + DB fetch
    ├── 02_backfill.sh       # 85 lines - descriptions + partners + invalidation
    ├── 03_classify.sh       # 60 lines - berufenet lookup + auto-matcher
    ├── 04_enrich.sh         # 33 lines - summaries + embeddings
    ├── status.sh            # 65 lines - status check mode
    └── summary.sh           # 54 lines - final stats
```

Benefits:
- Each step is testable independently
- Easy to add new steps
- Orchestrator stays thin
- Shared functions in one place

## Other Fixes

- Fixed STEP 3c in `scripts/nightly_fetch.sh` - SQL escaping issue with heredoc
- Changed from `python3 -c` with escaped `%%` to `python3 << 'PYEOF'` heredoc with parameterized `%s`

## Next Steps

1. ✅ Un-invalidated all 1,011 partner postings for reprocessing
2. Refactor `nightly_fetch.sh` into modular scripts (currently 545 lines)
3. Investigate db.wd3.myworkdayjobs.com overlap with existing Deutsche Bank jobs

---

*"Onboard once, use forever"* - The scraper strategy pays off. Each site takes ~30 minutes to analyze and implement, then handles thousands of postings automatically.
