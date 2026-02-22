# Yogi Bill — Methodology

**Author:** Arden  
**Date:** 2026-02-22  
**Status:** Draft for review (Sandy, Nate, xai)  
**Assumptions file:** `docs/project/billing_assumptions.yaml`

---

## What is a Yogi Bill?

A per-yogi, per-month document that shows **everything it costs to serve them** — not just what they pay. Every yogi gets a bill, regardless of tier (trial, free, or full). The bill is the transparency instrument Nate described: clarity, not accounting.

The bill answers three questions:
1. **What did you use?** (Direct AI actions)
2. **What did it cost to serve you?** (Your share of platform costs)
3. **What did you pay, and where did the money go?** (Revenue allocation)

---

## Bill Structure

```
╔══════════════════════════════════════════════════════════════════╗
║  talent.yoga — Deine Monatsübersicht / Your Monthly Summary     ║
║  Zeitraum: Februar 2026                                         ║
║  Yogi: Luna (user_id: 4)                                       ║
║  Tier: Full (€9.90/Monat)                                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  A. DEINE KI-NUTZUNG / YOUR AI USAGE                            ║
║  ┌────────────────────────────┬───────┬─────────┬──────────────┐ ║
║  │ Aktion                     │ Anzahl│ Preis   │ Summe        │ ║
║  ├────────────────────────────┼───────┼─────────┼──────────────┤ ║
║  │ Mira Gespräche             │    47 │ €0.02   │ €0.94        │ ║
║  │ Lebenslauf-Analyse         │     1 │ €0.50   │ €0.50        │ ║
║  │ Anschreiben                │     3 │ €0.30   │ €0.90        │ ║
║  │ Match-Berichte             │     5 │ €0.20   │ €1.00        │ ║
║  │ Profil-Aktualisierung      │     2 │ €0.05   │ €0.10        │ ║
║  ├────────────────────────────┼───────┼─────────┼──────────────┤ ║
║  │ GESAMT KI-Nutzung          │    58 │         │ €3.44        │ ║
║  └────────────────────────────┴───────┴─────────┴──────────────┘ ║
║                                                                  ║
║  B. WAS ES UNS KOSTET, DICH ZU BEDIENEN / COST TO SERVE YOU     ║
║  ┌────────────────────────────────────────────┬──────────────┐   ║
║  │ Rechenkosten (GPU für deine KI-Nutzung)    │ €0.14        │   ║
║  │ Dein Anteil Serverbetrieb (1/N)            │ €0.07        │   ║
║  │ Dein Anteil Plattform-Pipeline (1/N)       │ €0.01        │   ║
║  │ Dein Anteil Services (Domain, VPN, etc.)   │ €0.01        │   ║
║  ├────────────────────────────────────────────┼──────────────┤   ║
║  │ KOSTEN, DICH ZU BEDIENEN                   │ €0.23        │   ║
║  └────────────────────────────────────────────┴──────────────┘   ║
║                                                                  ║
║  C. DEIN BEITRAG / YOUR CONTRIBUTION                             ║
║  ┌────────────────────────────────────────────┬──────────────┐   ║
║  │ Du hast gezahlt                            │ €9.90        │   ║
║  │ − Betriebskosten (dein Anteil)             │ −€0.23       │   ║
║  │ = Verbleibend                              │ €9.67        │   ║
║  │   → Rücklage (10%)                         │ €0.97        │   ║
║  │   → Gründer-Rückzahlung (70%)              │ €6.77        │   ║
║  │   → Entwicklung (20%)                      │ €1.93        │   ║
║  └────────────────────────────────────────────┴──────────────┘   ║
║                                                                  ║
║  D. GEMEINSCHAFT / COMMUNITY                                     ║
║  ┌──────────────────────────────────────────────────────────┐    ║
║  │ Aktive Yogis diesen Monat:        1,247                   │    ║
║  │ Davon zahlend:                      312 (25%)             │    ║
║  │ Gesamtkosten Plattform:           €286                    │    ║
║  │ Gründer-Schuld verbleibend:       €783,260                │    ║
║  │ Fortschritt:  ████░░░░░░░░░  1.6%                          │    ║
║  └──────────────────────────────────────────────────────────┘    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Section A — Direct AI Usage

### Data source

`usage_events` table, filtered by `user_id` and `created_at` within billing period.

```sql
SELECT
    event_type,
    COUNT(*)                    AS event_count,
    SUM(cost_cents)             AS total_cents
FROM usage_events
WHERE user_id = :user_id
  AND created_at >= :period_start
  AND created_at <  :period_end
GROUP BY event_type
ORDER BY total_cents DESC;
```

### Price lookup

`usage_event_prices` table (runtime copy). The `cost_cents` is snapshotted into each `usage_events` row at event time, so the bill uses the price that was active when the action occurred — not the current price.

### What counts as an event

| Event Type | Trigger | Logged by |
|-----------|---------|-----------|
| `mira_message` | User sends message, LLM responds | Mira chat handler |
| `cv_extraction` | Adele parses uploaded CV | CV upload endpoint |
| `cover_letter` | Clara generates a cover letter | Cover letter endpoint |
| `match_report` | Clara evaluates posting-profile fit | Match report endpoint |
| `profile_embed` | Profile re-embedded after edit | Profile save handler |

### Tier behavior

| Tier | Events logged? | Events charged? |
|------|---------------|-----------------|
| Trial | Yes | Yes (against €5 trial budget) |
| Free | Yes (within daily limits) | No (€0 — but shown on bill as "what it would cost") |
| Full | Yes | No (flat €9.90/month — but shown on bill as transparency) |

**Key point:** Every tier logs every event. The bill always shows the full picture. The difference is only whether money changes hands.

---

## Section B — Cost to Serve You

This section allocates real operating costs to the individual yogi. Purpose: show them what it actually costs to keep their account running, regardless of what they pay.

### B1. Compute cost (variable, per-event)

Each AI event has an estimated compute cost (GPU time × amortized cost rate).

```
compute_cost = Σ (event_count × compute_cost_per_event)
```

Values from `billing_assumptions.yaml`, Section D:

| Event | Compute cost | Basis |
|-------|-------------|-------|
| mira_message | €0.003 | ~1.3s GPU (qwen2.5:7b) |
| cv_extraction | €0.050 | ~22s GPU (multi-pass) |
| cover_letter | €0.030 | ~13s GPU |
| match_report | €0.020 | ~9s GPU |
| profile_embed | €0.002 | ~0.8s GPU (bge-m3) |

**Rate derivation:**
- GPU amortization: €2,500 ÷ 36 months = €69.44/month
- Electricity: €30/month
- Combined: €99.44/month ÷ 720 hours = €0.138/GPU-hour = €0.0023/GPU-minute

### B2. Server share (fixed ÷ active yogis)

Fixed infrastructure costs divided equally among all active yogis in the period.

```sql
-- Count active yogis in period
SELECT COUNT(DISTINCT user_id) AS active_yogis
FROM usage_events
WHERE created_at >= :period_start
  AND created_at <  :period_end;
```

```
server_share = (hardware_monthly + electricity_monthly + backup_monthly) / active_yogis
             = (€69.44 + €30.00 + €5.00) / N
             = €104.44 / N
```

At 100 yogis: €1.04/yogi. At 1,000: €0.10. At 10,000: €0.01.

### B3. Pipeline share (fixed ÷ active yogis)

The nightly posting pipeline (turing_fetch) costs compute but serves all yogis:

```
pipeline_share = monthly_pipeline_cents / active_yogis
               = €15.00 / N
```

### B4. Services share (fixed ÷ active yogis)

Domain, VPN, email, monitoring:

```
services_share = (domain + vpn + email + monitoring) / active_yogis
               = (€3.00 + €10.00 + €0 + €0) / N
               = €13.00 / N
```

### Total cost to serve

```
cost_to_serve = compute_cost + server_share + pipeline_share + services_share
```

---

## Section C — Your Contribution

### Revenue allocation waterfall

For paying yogis (trial or full), show where the money goes:

```
payment = subscription_amount (or trial_spent for trial users)
operating_share = cost_to_serve                          # Already calculated in B
remainder = payment - operating_share
reserve = min(remainder × 10%, reserve_cap_remaining)
founder_repayment = remainder × 70% (after reserve)
development = remainder × 20% (after reserve)
```

### Tier-specific display

**Trial yogi:**
```
Du hast €1.20 von €5.00 deines Testbudgets verwendet.
Verbleibend: €3.80 (noch 11 Tage)
```

**Free yogi:**
```
Diesen Monat hat es uns €0.23 gekostet, dich zu bedienen.
Deine Nutzung wurde von zahlenden Yogis mitgetragen.
```

**Full yogi:**
```
Du hast €9.90 gezahlt.
€0.23 → Betrieb | €0.97 → Rücklage | €6.77 → Gründer | €1.93 → Entwicklung
```

---

## Section D — Community

Aggregate stats, same for all yogis (not personalized). Pulled from:

| Metric | Source |
|--------|--------|
| Active yogis | `COUNT(DISTINCT user_id) FROM usage_events WHERE period` |
| Paying yogis | `COUNT(*) FROM users WHERE subscription_status = 'active'` |
| Total platform cost | Sum of all Section B fixed costs |
| Founder debt remaining | `SELECT SUM(initial_investment_cents - repaid_cents) FROM founder_debt` |
| Repayment progress | `repaid / total × 100` |

This mirrors the public `/finanzen` page but contextualized within the individual bill.

---

## Data Flow Diagram

```
┌──────────────────────────┐     ┌──────────────────────┐
│   usage_events           │     │  usage_event_prices   │
│   (per-user, per-event)  │     │  (price schedule)     │
│   user_id, event_type,   │     │  event_type,          │
│   cost_cents, created_at │     │  cost_cents            │
└───────────┬──────────────┘     └──────────┬───────────┘
            │                               │
            ▼                               ▼
    ┌───────────────────────────────────────────────┐
    │           Section A: AI Usage                  │
    │   GROUP BY event_type                          │
    │   → line items with count × price              │
    └───────────────────┬───────────────────────────┘
                        │
┌───────────────────────┼────────────────────────────────┐
│                       ▼                                │
│  billing_assumptions.yaml                              │
│  ┌─────────────────────────────────────┐               │
│  │ Section D: compute_cost_per_event   │───┐           │
│  │ Section B: hardware monthly         │   │           │
│  │ Section C: services monthly         │   │           │
│  │ Section H: pipeline monthly         │   │           │
│  └─────────────────────────────────────┘   │           │
│                                            ▼           │
│                                   ┌────────────────┐   │
│                                   │ Section B:     │   │
│                                   │ Cost to Serve  │   │
│                                   └───────┬────────┘   │
│                                           │            │
└───────────────────────────────────────────┼────────────┘
                                            │
┌───────────────────────────────────────────┼────────────┐
│                                           ▼            │
│  ┌─────────────────┐            ┌─────────────────┐    │
│  │ users table      │            │ founder_debt    │    │
│  │ subscription_    │            │ table           │    │
│  │ status, tier,    │            │                 │    │
│  │ payment amount   │            │                 │    │
│  └────────┬────────┘            └────────┬────────┘    │
│           │                              │             │
│           ▼                              ▼             │
│   ┌───────────────────────────────────────────────┐    │
│   │       Section C: Your Contribution             │    │
│   │   payment − cost_to_serve = remainder          │    │
│   │   → allocation waterfall                       │    │
│   └───────────────────────────────────────────────┘    │
│                                                        │
│   ┌───────────────────────────────────────────────┐    │
│   │       Section D: Community                     │    │
│   │   aggregate stats from all sources             │    │
│   └───────────────────────────────────────────────┘    │
│                                                        │
│                       ▼                                │
│              ┌─────────────────┐                       │
│              │   YOGI BILL     │                       │
│              │   (monthly PDF  │                       │
│              │    or HTML)     │                       │
│              └─────────────────┘                       │
└────────────────────────────────────────────────────────┘
```

---

## What Needs To Exist (and What Already Does)

| Component | Status | Notes |
|-----------|--------|-------|
| `usage_events` table | ✅ Exists | Migration 059. Empty — no events logged yet |
| `usage_event_prices` table | ✅ Exists | 5 event types with prices |
| `founder_debt` table | ✅ Exists | Gershon + Mysti, correct amounts |
| `ledger_monthly` table | ✅ Exists | Empty — no months closed yet |
| `user_trial_balance` view | ✅ Exists | Per-user balance + trial status |
| `billing_assumptions.yaml` | ✅ NEW | Created this session — needs review |
| Mira event logging | ⚠️ Instrumented | Needs `git add -f lib/usage_tracker.py` |
| CV extraction logging | ❌ Not yet | One-line `log_event()` call in endpoint |
| Cover letter logging | ❌ Not yet | One-line `log_event()` call in endpoint |
| Match report logging | ❌ Not yet | One-line `log_event()` call in endpoint |
| Profile embed logging | ❌ Not yet | One-line `log_event()` call in endpoint |
| Bill generator script | ❌ Not yet | `scripts/generate_yogi_bill.py` |
| Bill API endpoint | ❌ Not yet | `GET /api/account/bill?month=2026-02` |
| Bill UI (frontend) | ❌ Not yet | Template showing the bill |
| Daily quota enforcement | ❌ Not yet | `check_access()` returns tier + remaining |
| Stripe integration | ❌ Not yet | Columns exist on `users` table |

---

## Bill Generation Algorithm

```python
def generate_bill(user_id: int, period_start: date, period_end: date) -> YogiBill:
    """
    1. Query usage_events for this user + period → Section A
    2. Load billing_assumptions.yaml
    3. Compute per-event compute costs → Section B (variable part)
    4. Count active yogis in period
    5. Compute fixed cost shares (server, pipeline, services ÷ N) → Section B (fixed part)
    6. Sum cost_to_serve = variable + fixed shares
    7. Determine payment amount from user tier
    8. Apply allocation waterfall → Section C
    9. Query community stats → Section D
    10. Return structured bill object
    """
```

---

## Open Questions for Review

1. **Compute cost estimates** — The GPU-minute costs in Section D of `billing_assumptions.yaml` are based on NUC power draw. Do we want to measure actual Ollama inference times more precisely? We have the data in pipeline logs.

2. **Free tier bill language** — "Deine Nutzung wurde von zahlenden Yogis mitgetragen" (your usage was carried by paying yogis). Is that the right tone? Nate said: transparency, not guilt.

3. **Bill delivery** — Monthly email, in-app page, or both? The finances page already exists. The bill could be a personal tab on that page.

4. **Pipeline costs** — Should we show "your share of keeping 167,733 job postings fresh" as a line item? It makes the platform feel alive.

5. **Historical bills** — Do we generate bills retroactively from existing data, or only going forward? (Currently 0 usage_events, so forward-only is simpler.)

6. **VAT** — Kleinunternehmer §19 UStG means no VAT initially. When do we switch? At €22,000/year revenue? This affects bill formatting.

---

## Next Steps

1. **Review `billing_assumptions.yaml`** — Sandy/Nate/xai adjust numbers until they fit
2. **Instrument remaining endpoints** — Add `log_event()` calls to CV, cover letter, match report, profile embed
3. **Build `scripts/generate_yogi_bill.py`** — Reads assumptions + DB, outputs bill
4. **Build bill API** — `GET /api/account/bill?month=2026-02`
5. **Build bill UI** — Personal finances tab showing monthly bill
6. **Implement daily quota** — `check_access()` returns tier + limits for free users
