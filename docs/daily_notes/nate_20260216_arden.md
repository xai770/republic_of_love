Hey Arden,

we have a significant evolution in the **market intelligence layer** of Talent Yoga. I want to update you because this is no longer just a UI improvement — it is turning into a core strategic capability.

We are moving from “job search” to **labour navigation**.

Here are the new dimensions we want to explore and eventually implement.

---

## 1. Regional Demand Comparison

We want to compare demand for a role cluster between the user’s region and other regions. The goal is **orientation and leverage**, not pressure.

The user question we want to answer:

> “Where is my profile currently most valued?”

Example output:

* Stuttgart 🔥 very high
* München ↑ high
* Frankfurt → stable
* Leipzig ↓ low

With contextual explanation:

> “Demand for your profile in Stuttgart is currently 2.4× higher than in your region.”

Important framing:

* Not “Your region is bad.”
* Instead: “Here are your strongest opportunities.”

This aligns with the dignity-first philosophy.

### Data / architecture considerations

Please think about:

* Demand index per region and role cluster
* Posting density normalization (region size, baseline)
* Time smoothing (avoid noise in small regions)
* Caching and batch computation
* Handling small sample sizes
* Explainability and audit trail

We do not need perfect supply data for MVP. Posting activity is enough.

Later:

* Applicant density
* Salary and cost-of-living signals
* Time-to-fill

---

## 2. Demand in Related Professions (Berufenet + embeddings)

This is potentially even more powerful.

We want to move users from rigid identity:

> “I am X”

to opportunity awareness:

> “Where else am I strong?”

We plan to combine:

* Berufenet structural similarity graph
* Embedding-based skill similarity

This hybrid model should be more robust and explainable.

Example:
Electrician → related:

* Mechatronics
* Industrial maintenance
* Renewable energy installation

Then overlay demand:

> “Related roles with strong demand.”

This supports pivoting and reskilling.

---

## 3. Interaction Between These Dimensions

The strongest insight: these two dimensions interact.

Example:

* Electricians in Frankfurt: stable
* Electricians in Stuttgart: high
* Mechatronics in Frankfurt: high

The user now has multiple strategic paths:

* Move
* Pivot
* Upskill

This reduces helplessness and increases agency.

---

## 4. Long-Term Vision

This leads to a concept we call:
**Opportunity Landscape**

Possible strategic quadrants:

1. Stay and grow
2. Move
3. Pivot
4. Upskill

This could become a signature screen of Talent Yoga.

---

## 5. Technical Questions for You

Please explore feasibility and trade-offs:

* How to build a stable demand index from noisy posting data
* How to normalize across professions and regions
* How to combine Berufenet graph and embedding similarity
* How to avoid misleading signals in niche roles
* How to integrate this into weekly reports and coaching
* Where computation runs (batch vs incremental)
* How to cache results for responsiveness
* How to maintain explainability

The math itself is not new, but robustness and trust are critical.

---

## 6. MVP Scope

For now, focus on:

* Regional demand index
* 14-day activity chart
* Basic related profession demand
* Simple narrative interpretation

Sophistication can come later.

This direction feels strategically strong and differentiating.

Looking forward to your thoughts.

— Nate

---

## Arden's Feasibility Assessment (Feb 16, 2026)

### Data Inventory — What We Already Have

| Asset | Coverage | Notes |
|-------|----------|-------|
| Active postings | 232,669 | All have `location_city` + `location_state` |
| Berufenet classification | 91% (212K postings) | 2,209 distinct professions |
| KLDB domain codes | 91% (211K postings) | 37 domains, well distributed |
| Berufenet reference table | 3,562 professions | Includes salary (median, Q25, Q75) |
| Embeddings | 268K vectors | text-hash keyed, bge-m3 model |
| Geo resolution | PLZ → lat/lon | via `plz_geocode` table (8,200+ PLZ mapped) |
| Time series depth | 54 days | Dec 2, 2025 → Feb 15, 2026 |
| States (Bundesländer) | Full coverage | `location_state` on every posting |

**Bottom line:** 91% of postings have both geo and occupation classification. This is enough for a credible MVP.

### Feasibility by Feature

#### 1. Regional Demand Index — Very Feasible

A demand snapshot is a single GROUP BY query:

```sql
SELECT location_state, SUBSTRING(berufenet_kldb FROM 3 FOR 2) AS domain,
       COUNT(*) AS demand,
       COUNT(*) FILTER (WHERE first_seen_at > NOW() - INTERVAL '14 days') AS fresh
FROM postings WHERE enabled=true AND invalidated=false
GROUP BY location_state, domain;
```

This produces a (state × domain) matrix: ~37 domains × ~16 states = 592 cells. Normalize by dividing each cell by the state's total to get demand concentration. Compare to national average to produce the "2.4× higher" signal.

**Computation strategy:** Nightly batch, stored in a `demand_snapshot` table. Refreshed after the pipeline runs. Sub-second reads from API.

#### 2. Related Profession Demand — Feasible, Hybrid Approach

Two complementary similarity sources:

- **KLDB structural:** Professions sharing the first 3 digits of their KLDB code are in the same occupation group. Free — already in the data. E.g., all `B 261xx` = "Mechatronik und Automatisierungstechnik."
- **Embedding similarity:** Compute cosine similarity between Berufenet profession description embeddings. Captures cross-domain connections (Electrician ↔ Renewable energy installer).

**Implementation:** Pre-compute a `profession_similarity` table. Only keep top-10 per profession = ~22K rows. Refresh weekly.

#### 3. 14-Day Activity Chart — Trivial

```sql
SELECT DATE(first_seen_at) AS day, COUNT(*)
FROM postings WHERE first_seen_at > NOW() - INTERVAL '14 days'
  AND berufenet_kldb LIKE '%43%' AND location_state = 'Baden-Württemberg'
GROUP BY day ORDER BY day;
```

Sparkline or small bar chart. Fast enough to run live, no caching needed.

#### 4. Narrative Interpretation — Template-Driven for MVP

Once demand index and related professions exist, generate a 2-3 sentence interpretation. Template with fill-in is fine:

> "Market activity for {profession} in {region} is currently {level} ({ratio}× the national average). Related roles with strong activity nearby: {list}."

LLM (qwen2.5:7b) can enrich later. Start with templates for trust and speed.

### Honest Constraints

1. **54 days of history** — Not enough for reliable trend arrows (🔥 ↑ → ↓). Show absolute levels now. Trends need ~3-4 months of continuous data. Don't fake them.
2. **Small sample sizes** — Some (state × profession) cells will have < 10 postings. Suppress cells below threshold (suggest: 20 postings minimum). Show "insufficient data" instead.
3. **No supply-side data** — Without applicant volume, "high demand" is incomplete. Call it "market activity" or "posting activity" until both sides are available.
4. **Embedding coverage** — Need to verify the 268K embeddings include Berufenet profession descriptions, not just posting texts. If only posting-level, a one-time batch to embed 3,562 Berufenet names/descriptions takes ~5 minutes with bge-m3.

### Architecture

```
┌─────────────────────────────────────────┐
│  Nightly batch (cron, after pipeline)   │
│                                         │
│  1. demand_snapshot table               │
│     (state × domain × berufenet_id)     │
│     current count + 14-day fresh count  │
│                                         │
│  2. profession_similarity table         │
│     (berufenet_id_a, berufenet_id_b,    │
│      kldb_score, embedding_score,       │
│      combined_score)                    │
│     top-10 per profession               │
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  API: /api/intelligence/{user_id}       │
│                                         │
│  Reads user profile (location,          │
│  berufenet_id) → queries snapshot +     │
│  similarity → returns JSON:             │
│  - regional_comparison[]                │
│  - related_professions[]                │
│  - activity_chart (14-day)              │
│  - narrative (template-generated)       │
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  UI: "Opportunity Landscape" card       │
│  on /dashboard or dedicated /landscape  │
└─────────────────────────────────────────┘
```

### MVP Effort Estimate

| Feature | Effort | Value |
|---------|--------|-------|
| `demand_snapshot` table + batch script | 2-3 hours | Foundation for everything |
| Regional comparison for user's profile | 1 day | "Where am I valued?" |
| 14-day activity sparkline | 2-3 hours | Visual proof of movement |
| KLDB-based related professions | 3-4 hours | "Where else am I strong?" |
| Embedding-based similarity (top-10) | Half day | Cross-domain connections |
| Narrative template | 2-3 hours | Human-readable takeaway |
| **Total MVP** | **~3 days** | |

### Connection to Map (#21)

Feedback item #21 (map pins + heatmap) connects naturally to this. The map becomes the visualization surface for regional demand — showing heatmap filtered by the user's profession/domain. This is the "where is my profile valued?" question rendered geographically.

- **Phase 1:** Tune existing heatmap (color gradient, radius, blur). Quick visual improvement.
- **Phase 2:** Domain-aware heatmap that responds to the intelligence layer.

### Recommendation

Start with `demand_snapshot` — it's the keystone. Everything else reads from it. The data is ready; the constraint is time series depth, which resolves itself daily.
