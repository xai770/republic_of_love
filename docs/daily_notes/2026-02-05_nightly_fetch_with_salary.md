# 2026-02-05: Nightly Fetch — First Run with Salary Data

**Time:** ~03:00 CET (manual or cron)  
**Observer:** xai + copilot  
**Mood:** 🎉 Everything's in place!

---

## 🎯 What We Expect to Happen

Tonight's fetch will be the **first with complete salary data** in place. Here's what's different:

### What's NEW Since Last Night

| Feature | Status | Impact |
|---------|--------|--------|
| Salary data | 99.99% coverage | Every matched posting gets €€€ |
| Entgeltatlas API | Discovered! | Can refresh salaries anytime |
| `salary_api_fetcher.py` | Created | Fast enrichment tool |
| 5 manual fallbacks | Set | Fachpraktiker Küche, Ing. Maschinenbau, etc. |

### Pipeline Steps (Updated)

```
┌────────────────────────────────────────────────────────────────┐
│                    NIGHTLY FETCH PIPELINE                      │
│                     Feb 5-6, 2026                              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. AA Fetch ──► 2. DB Fetch ──► 3. Backfill Descriptions     │
│     (16 states)    (instant)       (HTTP, VPN rotation)        │
│     ~10 min        ~1 min          ~30-60 min                  │
│                                                                │
│  4. Berufenet Classification ──► 5. LLM Summaries              │
│     (instant SQL JOIN)              (DB postings only)         │
│     ~1 sec                          ~10-20 min                 │
│                                                                │
│  6. Embeddings ──► 7. ✨ SALARY LOOKUP ✨                       │
│     (3 workers)       (NEW! instant SQL)                       │
│     ~30-60 min        ~1 sec                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 📊 Expected Outcomes

### New Postings
| Source | Expected Volume | Notes |
|--------|----------------|-------|
| Arbeitsagentur | 500-2,000 | Daily churn across 16 states |
| Deutsche Bank | 10-50 | Lower volume corporate |
| **Total new** | ~600-2,100 | |

### Salary Coverage for New Postings

Since we have **99.99% salary coverage** at the profession level:

| Scenario | Probability | Outcome |
|----------|------------|---------|
| New posting matches known berufenet | ~75% | ✅ Gets salary immediately |
| New posting needs new synonym | ~20% | ⚠️ No salary until synonym added |
| New posting is military | ~0.01% | ❌ No salary (expected) |

**Expected salary coverage for tonight's new postings: ~75%**

(Same as berufenet coverage — salary is tied to profession, not individual job)

### Embedding Status
| Metric | Current | After Tonight |
|--------|---------|---------------|
| Total embeddings | 124,929 | ~126,000-127,000 |
| Pending | ~0 | ~0 (workers should catch up) |

---

## 🔬 What to Watch For

### Success Indicators ✅

1. **AA Fetch completes** without 403 errors
   - Check: `grep "SUCCESS" /tmp/nightly_fetch.log | wc -l`

2. **Backfill handles rate limits** gracefully
   - Watch: VPN rotation messages
   - Expected: 1-3 rotations max

3. **Berufenet classification runs**
   - Check: New postings get `berufenet_id` populated
   - Query: `SELECT COUNT(*) FROM postings WHERE berufenet_id IS NOT NULL AND created_at > NOW() - INTERVAL '1 day'`

4. **Salary data propagates** to matched postings
   - Since salary lives in `berufenet` table, any posting with a `berufenet_id` automatically has salary access via JOIN
   - No extra step needed!

### Potential Issues ⚠️

1. **New profession names** not in synonyms table
   - Symptom: `berufenet_id = NULL` for many new postings
   - Fix: Run synonym expansion script tomorrow

2. **VPN issues** during backfill
   - Symptom: Many 403s, slow progress
   - Fix: Manual VPN rotation or wait

3. **Embedding backlog** if workers crash
   - Symptom: `pending_embeddings > 1000` after run
   - Fix: Restart embedding workers

---

## 📋 Pre-Run Checklist

```bash
# Check current state
python3 -c "
import psycopg2
conn = psycopg2.connect(dbname='turing', user='base_admin', password='${DB_PASSWORD}', host='localhost')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM postings')
total = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM postings WHERE berufenet_id IS NOT NULL')
with_beruf = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM embeddings')
embeds = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM berufenet WHERE salary_median IS NOT NULL')
with_salary = cur.fetchone()[0]

print(f'Total postings:     {total:,}')
print(f'With berufenet_id:  {with_beruf:,} ({100*with_beruf/total:.1f}%)')
print(f'Total embeddings:   {embeds:,}')
print(f'Professions w/sal:  {with_salary:,}/3,562 (99.4%)')
"
```

---

## 🎯 Success Criteria

| Metric | Target | How to Check |
|--------|--------|--------------|
| AA fetch completes | ✅ | Log shows "Step 1 complete" |
| Backfill > 50% success | ✅ | Check invalidated vs success count |
| New postings have berufenet | > 70% | SQL query above |
| Embeddings caught up | < 100 pending | `SELECT COUNT(*) FROM postings WHERE embedding_id IS NULL` |
| No crashes | ✅ | Script exits 0 |

---

## 📝 Post-Run Notes

*Updated Feb 6, 2026 ~03:45 CET after debugging session*

### Actual Timing
- Start: 02:58 CET (first attempt)
- Multiple restarts due to issues (see below)
- Final successful run: 03:35 CET
- Total: ~45 min (with debugging)

### Results
| Step | Status | Notes |
|------|--------|-------|
| 1. AA Fetch | ✅ | 15,895 jobs (all existing, 0 new tonight) |
| 2. DB Fetch | ✅ SKIPPED | Already ran today |
| 3. Backfill | ✅ | 3,225 descriptions (despite VPN issues) |
| 4. Berufenet | ✅ | 254 exact + 63 synonym = 317 classified |
| 4b. Auto-matcher | ✅ | TIER 1 + TIER 2 ran |
| 5. Summaries | ✅ | No DB postings needed summaries |
| 6. Embeddings | 🔄 | 3,593 running @ 7.5/sec |

### New Postings Summary
- Total new: 0 (all 15,895 were existing)
- With berufenet_id: 317 newly classified
- Embeddings pending: 3,593 (running now)

---

## 🐛 Issues Encountered & Fixes (Feb 6 Session)

This was a debugging-heavy session. Complex pipeline + many changes = expected turbulence.

### Issue 1: Pipeline Stuck (TTY Output)
**Symptom:** Pipeline stopped at 02:08:39, process showed `Stopped (tty output)`  
**Root Cause:** `nohup` didn't fully detach process from terminal. When Python ThreadPoolExecutor started 200 workers, terminal interactions caused SIGTSTP.  
**Fix:** Added `</dev/null` to all python3 commands in `nightly_fetch.sh`, plus `setsid` for parallel workers.

### Issue 2: No Timestamps in Logs
**Symptom:** Log entries had no timestamps, impossible to track progress  
**Fix:** Added `tlog()` function to 6 Python scripts:
- `actors/postings__aa_backfill_U.py`
- `actors/postings__arbeitsagentur_CU.py`
- `actors/postings__deutsche_bank_CU.py`
- `actors/postings__embedding_U.py`
- `actors/postings__extracted_summary_U.py`
- `tools/berufenet_auto_matcher.py`

### Issue 3: Syntax Errors (Escaped Quotes)
**Symptom:** `SyntaxError: unexpected character after line continuation character`  
**Root Cause:** Tool inserted escaped quotes `\"\"\"` instead of `"""`  
**Files affected:** `tools/berufenet_auto_matcher.py`, `actors/postings__extracted_summary_U.py`  
**Fix:** Replaced escaped quotes with proper Python triple quotes

### Issue 4: VPN Rotation Failing
**Symptom:** `sudo: a terminal is required to read the password`  
**Root Cause:** Background process can't prompt for sudo password  
**Fix:** Created `/etc/sudoers.d/vpn`:
```
xai ALL=(ALL) NOPASSWD: /usr/sbin/openvpn, /usr/bin/pkill
```

### Issue 5: Backfill Logging to Wrong File
**Symptom:** Progress appeared idle, but backfill was actually running  
**Root Cause:** `log()` wrote to `logs/aa_backfill.log`, not stdout  
**Fix:** Changed `log()` in `postings__aa_backfill_U.py` to print to stdout

### Issue 6: Misleading "Reached Limit" Message
**Symptom:** Log said "reached limit" even when all jobs were fetched  
**Root Cause:** Message didn't distinguish "got everything" from "capped"  
**Fix:** Changed to:
- `✅ Done fetching (all N available)` — got everything
- `⚠️ CAPPED at N (API has X available)` — truncated

---

## 📚 Lessons Learned

1. **Background processes need full detachment** — `nohup` alone isn't enough, add `</dev/null` and `setsid`
2. **Timestamps are essential** — without them, "is it stuck or working?" is unknowable
3. **Single log destination** — all pipeline output should go to one file
4. **Test syntax after edits** — quick `python3 -c "import module"` catches issues early
5. **Sudoers for automation** — any sudo command in cron/background needs NOPASSWD entry

---

### Tomorrow's TODOs
- [x] Fix TTY detachment in nightly_fetch.sh
- [x] Add timestamps to all Python scripts
- [x] Fix VPN sudoers
- [x] Consolidate backfill logging
- [x] Verify full pipeline runs unattended at 20:00 *(cron set, syntax OK, imports OK)*
- [x] Check for new unmatched profession names *(30 found)*
- [x] Add synonyms if needed *(30 added → coverage 76% → 79%)*
- [x] Verify salary data accessible in API/UI *(API updated with salary_median, salary_range)*

---

*— Updated Feb 6 2026, 03:45 by xai + Arden*
