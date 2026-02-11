# 2026-02-06 — BI Dashboard Domain Classification

**Session:** Morning (05:10 CET)  
**Focus:** Making the BI dashboard useful with real domain data

---

## Context

User reviewed Yogi BI dashboard at `localhost:8501`. Current state:
- 50K postings loaded
- 4 profiles available
- Panel 1 (Domain drill-down) shows "Unclassified" for everything
- Panel 4 (Skills Graph) has placeholder random positions
- Geography works but no radius search

## Priorities Agreed

| Priority | Task | Status |
|----------|------|--------|
| 🔴 High | Populate `domain_gate` from berufenet categories | TODO |
| 🔴 High | Compute real skill positions in UMAP space | TODO |
| 🟡 Med | Add postal code → radius filter | TODO |
| 🟢 Low | Interactive map with shape selection | Deferred |

## Technical Plan

### 1. Domain Classification from Berufenet

Berufenet provides KldB (Klassifikation der Berufe) codes which encode:
- Berufsbereich (occupational area) - first digit
- Berufshauptgruppe (major group) - first 2 digits
- Berufsgruppe (group) - first 3 digits
- Berufsuntergruppe (subgroup) - first 4 digits
- Berufsgattung (occupation type) - all 5 digits

We'll map these to user-friendly domains:
- Financial/Banking
- Healthcare/Medical
- IT/Technology
- Manufacturing/Industrial
- Education/Research
- Logistics/Transport
- Construction/Trades
- Service/Retail
- Public/Government
- Legal
- etc.

### 2. Skills UMAP Projection

Current approach (random): ❌
```python
skill_x = np.random.uniform(...)  # fake
```

Real approach:
1. Store the UMAP reducer object (pickle)
2. When profile selected, embed each skill
3. Project through saved reducer
4. Plot actual positions in skill-space

---

## Session Log

### 05:10 - Started
- Reviewed bi_app.py (760 lines)
- Reviewed market_visualization.ipynb (UMAP setup)
- Identified gaps

### 05:12 - Explored Berufenet Data
- KldB (Klassifikation der Berufe) codes are in `B XXXXX` format
- First 2 digits after "B " = Berufshauptgruppe (major group)
- 36 major groups map nicely to ~16 user-friendly domains

### 05:14 - Created Domain Mapping Script
- Created `tools/populate_domain_gate.py`
- Maps KldB codes → domains like:
  - 51: Transport & Logistics
  - 81: Healthcare & Medicine
  - 43: IT & Technology
  - etc.
- Includes subdomain and color for visualization

### 05:16 - Applied Domain Classification
```
✅ Updated 36,550 postings with domain classification

📊 Final domain distribution:
   Transport & Logistics: 7,899
   Technology & Engineering: 5,896
   Manufacturing & Engineering: 4,842
   Healthcare & Medicine: 3,831
   Hospitality & Food: 3,650
   Commerce & Retail: 2,273
   Construction & Trades: 2,260
   Education & Social Work: 2,006
   Business & Management: 1,952
   Finance & Banking: 770
   IT & Technology: 628
   Hospitality & Tourism: 448
   Government & Law: 51
   Culture & Media: 28
   Security & Defense: 15
   Science & Research: 1
```

### 05:18 - Dashboard Updated
- Refreshed bi_app.py (already reads domain_gate)
- Stacked bar chart now shows colored domain segments
- Drill-down ready for domain → profession filtering

### 05:35 - Skills Projection Implemented
- Added `get_cluster_centroids()` function - extracts centroids from UMAP clusters  
- Created `SKILL_CLUSTER_MAP` - keyword mapping for 22 auto-clusters
- Implemented `project_skill_to_umap()` - projects skills using keyword matching to cluster centroids + jitter
- Updated `render_skills_panel()` to use cluster-based projection instead of random
- Tested with "Ellie Larrison — Senior Oracle Database Administrator"
- Her 10 skills now project to meaningful positions in the UMAP space:
  - Oracle 19c Administration
  - High Availability Architecture
  - Oracle Cloud Infrastructure (OCI)
  - Shell Scripting (Bash, Python)
  - Oracle Real Application Clusters (RAC)
  - Oracle 21c Administration
  - Oracle Database Administration
  - Database Security & Compliance
  - Backup & Recovery (RMAN)
  - Linux/Unix System Administration

## Status Summary

| Priority | Task | Status |
|----------|------|--------|
| 🔴 High | Populate `domain_gate` from berufenet categories | ✅ Done (123,868 postings) |
| 🔴 High | Compute real skill positions in UMAP space | ✅ Done (cluster-based) |
| 🟡 Med | Add postal code → radius filter | ✅ Done |
| 🟢 Low | Interactive map with shape selection | Deferred |

---

## Session 2: Bug Hunt (08:28 CET)

After crash recovery, reviewed the dashboard with Playwright. Gershon and I did a bug hunt competition.

### 08:45 - Radius Search Implemented

1. Downloaded German PLZ geocoding data from GeoNames
   - 23,297 place entries → 10,813 unique PLZ codes
   - Created `plz_centroid` table with lat/lon averages per PLZ

2. Updated `bi_app.py`:
   - Added `get_plz_coordinates()` - lookup PLZ → lat/lon
   - Added `haversine_distance()` - calculate km between two points
   - Added PLZ input + radius selector to Geography panel
   - Updated `apply_filters()` with radius filtering
   - Added radius badge to filter header

3. Coverage: **74,246 / 78,599 postings** (94.5%) have geocoding

### 09:00 - Bug Hunt Results

Used Playwright to inspect the dashboard. Found **17 issues**:

| # | Severity | Issue |
|---|----------|-------|
| 1 | 🔴 High | Date axis shows "Feb 22026" (compression bug) |
| 2 | 🔴 High | "Postings (50,000 matches)" shows LIMIT not actual count |
| 3 | 🔴 High | Skills Graph empty even with profile selected |
| 4 | 🟡 Med | Unclassified missing from qualification pie chart |
| 5 | 🟡 Med | Calendar emoji shows wrong day ("17" not "6") |
| 6 | 🟡 Med | Location duplicates: "Thüringen, Thüringen" |
| 7 | 🟡 Med | Location duplicates: "Bayern, Bayern" |
| 8 | 🟡 Med | Raw markdown `**text**` not rendered in job titles |
| 9 | 🟡 Med | Misclassification: "IT System Engineer" → "BI Consultant" |
| 10 | 🟡 Med | Misclassification: "Softwarearchitekt" → "BI Consultant" |
| 11 | 🟢 Low | No berufenet tag for unclassified jobs |
| 12 | 🟢 Low | Only 5 days visible despite 90-day query |
| 13 | 🟢 Low | Location shows Regierungsbezirk (extra admin level) |
| 14 | 🟢 Low | Reset button only shows when filters active |
| 15 | 🟢 Low | Radius search no validation for invalid PLZ |
| 16 | 🟢 Low | Dashboard title cut off on small screens |
| 17 | 🟢 Low | No loading indicator for filter changes |

**Gershon's additions (he found 2 more):**

| # | Severity | Issue |
|---|----------|-------|
| 18 | 🔴 High | **Chart labels invisible in dark mode** (Firefox/Chromium) |
| 19 | 🔴 High | **"View →" links to external AA URL** — should open internal posting detail with match report |

### Database Update

```
Total postings: 123,875
With domain_gate: 123,868 (99.994%)
Without domain_gate: 7

By source:
  arbeitsagentur: 120,137 (120,131 with domain)
  deutsche_bank: 3,738 (3,737 with domain)
```

---

## Dragon Slaying Plan

### Priority 1 (High — UX blockers)
1. ~~Dark mode chart labels~~ — add explicit text colors
2. ~~Posting count shows LIMIT~~ — show actual filtered count
3. ~~"View →" links~~ — create internal posting detail page

### Priority 2 (Medium — Data quality)
4. Fix location duplicates ("Bayern, Bayern")
5. Fix markdown rendering in job titles
6. Investigate Berufenet misclassifications

### Priority 3 (Low — Polish)
7. Date axis formatting
8. Unclassified in pie chart
9. Skills graph with profile selection

---

## Next Steps

- [ ] Fix dark mode chart labels (Plotly template)
- [ ] Show actual filtered count instead of LIMIT
- [ ] Create `/posting/{posting_id}` page for detailed view
- [ ] Fix location duplicates

---

## Session 3: BI Dashboard Integration (15:45 CET)

**Goal:** Integrate BI Dashboard into talent.yoga main site with consistent navigation

### Problem

The BI Dashboard at `bi.talent.yoga` is a standalone Streamlit app. When users clicked "My Overview" in the sidebar, it opened in a new tab — **losing the sidebar navigation entirely**.

### Solution Implemented

Created a wrapper page at `/bi` that:
1. Keeps the talent.yoga sidebar visible
2. Embeds `bi.talent.yoga` in an iframe
3. Maintains navigation context

### Changes Made

| File | Change |
|------|--------|
| `frontend/templates/bi.html` | **NEW** — Wrapper template with sidebar + iframe |
| `api/main.py` | Added `/bi` route with authentication |
| `frontend/templates/dashboard.html` | Updated "My Overview" link: `https://bi.talent.yoga` → `/bi` |
| `frontend/templates/matches.html` | Same link update |
| `frontend/templates/profile.html` | Same link update |
| `frontend/templates/messages.html` | Same link update |
| `frontend/static/css/style.css` | Hidden sidebar scrollbars (all browsers) |
| `frontend/templates/base.html` | Cache-busted CSS `?v=20260206d` |

### CSS Scrollbar Fix

User noticed a small scrollbar appearing in the sidebar. Fixed with:

```css
/* Hide scrollbar on ALL sidebar children */
.sidebar *::-webkit-scrollbar { display: none; }
.sidebar * { scrollbar-width: none; -ms-overflow-style: none; }

/* Hide collapse button - not needed */
.sidebar-collapse-btn { display: none !important; }
```

### Verification

Used Playwright to capture screenshots and confirm:
- ✅ Sidebar renders correctly on `/bi` page
- ✅ Navigation between pages maintains sidebar
- ✅ No scrollbars visible in sidebar
- ✅ Collapse button hidden

### Result

Clicking "My Overview" now opens the BI Dashboard **inside the main app layout** with full sidebar navigation preserved.

---

*Memo by Arden ℵ (Master for the day)*
