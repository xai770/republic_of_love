# talent.yoga Pricing & Transparent Ledger

**Date:** 2026-01-27  
**Author:** Sage  
**Status:** Draft for review  
**Purpose:** Define pricing tiers and public ledger for lobby display

---

## Philosophy

> "We believe job seekers deserve honesty, not extraction."

talent.yoga operates on **radical financial transparency**:
- Every euro in, every euro out — visible to all
- Founder investment tracked openly
- No VC money, no hidden incentives, no selling your data

### The Long-Term Vision: Non-Profit Conversion

talent.yoga starts as a for-profit (flexibility to invest, scale, pivot) with a planned **conversion to non-profit** (gemeinnützige GmbH) once sustainable.

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: Prove It (Now → Sustainability)                           │
│  • For-profit structure (GmbH or Einzelunternehmen)                 │
│  • Transparent ledger from day 1                                    │
│  • Founder debt tracked, partially repaid                           │
│  • Reinvest in hardware, scaling, development                       │
│  • Target: 6-month operating runway in reserve                      │
│                                                                     │
│  CONVERSION TRIGGER:                                                │
│  • 6-month runway secured                                           │
│  • Sustainable user base (revenue ≥ costs for 6 consecutive months) │
│  • Founders agree to convert                                        │
│                                                                     │
│  PHASE 2: Lock It In (Post-Conversion)                              │
│  • Convert to gGmbH (gemeinnützige GmbH)                            │
│  • Remaining founder debt written off as donation                   │
│  • Mission-locked: no sale, no equity exit                          │
│  • Modest salaries, transparent governance                          │
│  • Surplus → mission (better service, lower prices, grants)         │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this path?**
- Non-profit setup takes time and limits flexibility
- Hardware investment needs to happen now
- Proving the model first = stronger foundation for non-profit
- Founder debt repayment is *partial* — the rest becomes a donation

---

## 1. Founder Investment (The Debt)

### Calculation

| Contributor | Period | Hours/week | Weeks | Rate | Total |
|-------------|--------|------------|-------|------|-------|
| **Gershon** (Architecture, Development) | 2023–2026 | 47h | 156 | €100/h | €733,200 |
| **Mysti** (UX, Testing, Vision) | 2023–2026 | 5h | 156 | €80/h | €62,400 |
| **Total Founder Debt** | | | | | **€795,600** |

### Notes on the Calculation

- **Rate:** Market rate for senior architect (€100/h) and UX consultant (€80/h) in Germany
- **Hours:** Documented based on actual schedule (47h/week = total working hours minus DB employment)
- **No interest:** Founders are not charging interest on this investment
- **No inflation adjustment:** Fixed at time of work

### What This Means

The founders worked **7,332 hours** (Gershon) and **780 hours** (Mysti) before asking users for a single euro.

**Phase 1:** This debt is partially repaid from user contributions.  
**Phase 2:** Upon non-profit conversion, remaining debt is written off as a founder donation.

---

## 2. Capital Investment (Hardware & Infrastructure)

### Current & Planned Investment

| Item | Cost | Status | Purpose |
|------|------|--------|---------|
| Intel NUC + GPU | €2,500 | ✅ Owned | Current inference server |
| Second GPU node | €3,000 | Planned | Redundancy + capacity |
| Cloud burst capacity | €500/month | Future | Peak load handling |
| Backup infrastructure | €500 | Planned | Disaster recovery |
| **Total hardware** | **€6,500** | | |

### How Hardware Is Funded

**Phase 1 (now):** From founder investment or early revenue  
**Phase 2 (non-profit):** From operating budget, grants, or community fundraising

Hardware investment is tracked separately from founder time:

```
┌─────────────────────────────────────────────────────────────────────┐
│  FOUNDER INVESTMENT                                                 │
│                                                                     │
│  Time investment:                                                   │
│  ├─ Gershon: 7,332 hours × €100/h = €733,200                        │
│  └─ Mysti: 780 hours × €80/h = €62,400                              │
│                                                                     │
│  Capital investment:                                                │
│  └─ Hardware & infrastructure = €6,500 (tracked separately)         │
│                                                                     │
│  Total: €802,100                                                    │
│  Repayment target (Phase 1): Partial — aim for capital + modest %   │
│  Remainder at conversion: Donated to the non-profit                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Operating Costs

### Current Monthly Costs (Estimated at Scale)

| Category | Description | Per-User | Fixed | Variable |
|----------|-------------|----------|-------|----------|
| **Compute (GPU)** | LLM inference, embeddings | €0.15 | — | ✓ |
| **Hosting** | Server, electricity | — | €30 | — |
| **Storage** | PostgreSQL, backups | €0.01 | €10 | ✓ |
| **APIs** | arbeitsagentur (free), future boards | €0.02 | — | ✓ |
| **Email** | Transactional (Mailgun/similar) | €0.01 | €5 | ✓ |
| **Domain & SSL** | talent.yoga | — | €3 | — |
| **Total Fixed** | | | **€48** | |
| **Total Variable** | | **€0.19/user** | | |

### Cost Model

```
Monthly operating cost = €48 + (€0.19 × active_users)
```

| Active Users | Operating Cost | Cost/User |
|--------------|----------------|-----------|
| 100 | €67 | €0.67 |
| 500 | €143 | €0.29 |
| 1,000 | €238 | €0.24 |
| 5,000 | €998 | €0.20 |
| 10,000 | €1,948 | €0.19 |

---

## 3. Pricing Tiers

### The Tiers

| Tier | Price | What You Get | Who It's For |
|------|-------|--------------|--------------|
| **Basis** | €0 | 10 matches/month, skill extraction, basic dashboard | Trying it out |
| **Standard** | €5/month | Unlimited matches, 5 cover letters/month, full reports | Active job seekers |
| **Sustainer** | €10+/month | Everything + you fund others + name on supporters page | Believers in the mission |

### What Your Money Buys

```
┌─────────────────────────────────────────────────────────────────────┐
│  Your €5/month at 1,000 users:                                      │
│                                                                     │
│  ├─ €0.24 → Operating costs (keeps the lights on)                   │
│  └─ €4.76 → Founder debt repayment                                  │
│                                                                     │
│  Your €10/month as Sustainer:                                       │
│                                                                     │
│  ├─ €0.24 → Operating costs                                         │
│  ├─ €4.76 → Founder debt repayment                                  │
│  └─ €5.00 → Subsidizes one free Basis user                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Tier Limits (Technical)

| Feature | Basis | Standard | Sustainer |
|---------|-------|----------|-----------|
| Matches shown/month | 10 | Unlimited | Unlimited |
| Cover letters/month | 0 | 5 | Unlimited |
| Interview prep | ❌ | ❌ | ✅ |
| Priority support | ❌ | ❌ | ✅ |
| Name on supporters | ❌ | ❌ | ✅ (optional) |
| API access | ❌ | ❌ | Future |

---

## 4. Revenue Allocation

### The Waterfall

Revenue flows in this order:

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. OPERATING COSTS (first priority)                                │
│     └─ Fixed + variable costs must be covered                       │
│                                                                     │
│  2. RESERVE FUND (10% of remainder)                                 │
│     └─ 3-month runway buffer                                        │
│     └─ Cap: €10,000 (excess flows to next tier)                     │
│                                                                     │
│  3. FOUNDER DEBT REPAYMENT (70% of remainder)                       │
│     └─ Split proportional to investment:                            │
│        • Gershon: 92.2% (€733,200 / €795,600)                       │
│        • Mysti: 7.8% (€62,400 / €795,600)                           │
│                                                                     │
│  4. DEVELOPMENT FUND (20% of remainder)                             │
│     └─ New features, infrastructure, security                       │
│     └─ Visible on ledger                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Example: 500 Paying Users at €5/month

| Line Item | Amount |
|-----------|--------|
| **Revenue** | €2,500 |
| − Operating costs | −€143 |
| **Remainder** | €2,357 |
| − Reserve (10%) | −€236 |
| − Founder repayment (70%) | −€1,485 |
| − Development fund (20%) | −€424 |
| **Allocated** | €2,288 |

Monthly founder repayment: €1,485
- Gershon: €1,369
- Mysti: €116

**Time to repay €795,600 at this rate:** 536 months (44 years) 😅

We'll need more users.

### At Scale: 10,000 Paying Users

| Line Item | Amount |
|-----------|--------|
| **Revenue** | €50,000 |
| − Operating costs | −€1,948 |
| **Remainder** | €48,052 |
| − Reserve (10%, capped) | −€10,000 max, then €0 |
| − Founder repayment (70%) | −€33,636 |
| − Development fund (20%) | −€9,610 |

**Time to repay at this rate:** 24 months (2 years) ✅

---

## 5. Post-Conversion Phase (Non-Profit)

When conversion triggers are met and talent.yoga becomes a gGmbH:

### What Changes

| Aspect | Phase 1 (For-Profit) | Phase 2 (Non-Profit) |
|--------|---------------------|----------------------|
| Structure | GmbH | gGmbH (gemeinnützig) |
| Founder debt | Partially repaid | Remainder = donation |
| Surplus | → repayment, then development | → mission only |
| Sale possible? | Technically yes | No — mission-locked |
| Governance | Founders decide | Board + transparency |
| Tax status | Normal | Tax-advantaged |
| Grants eligible? | Limited | Yes — foundations, government |

### New Allocation (Post-Conversion)

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. OPERATING COSTS (unchanged)                                     │
│                                                                     │
│  2. RESERVE FUND (10%, capped at 6-month runway)                    │
│                                                                     │
│  3. SALARIES (40% of remainder)                                     │
│     └─ Founders + any staff                                         │
│     └─ Transparent, on ledger                                       │
│     └─ Capped at reasonable market rate                             │
│                                                                     │
│  4. MISSION FUND (50% of remainder)                                 │
│     └─ Development & infrastructure                                 │
│     └─ Price reduction for users                                    │
│     └─ Grants for job seekers in need                               │
│     └─ Community initiatives                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### The Donation Moment

When founders convert remaining debt to donation:

```
┌─────────────────────────────────────────────────────────────────────┐
│  CONVERSION EVENT — [Date TBD]                                      │
│                                                                     │
│  Founder debt at conversion:     €750,000 (example)                 │
│  Already repaid:                 €52,100                            │
│  Donated to gGmbH:               €697,900                           │
│                                                                     │
│  "Gershon and Mysti donated €697,900 in development time            │
│   to make talent.yoga a permanent public resource."                 │
│                                                                     │
│  From this day forward, talent.yoga belongs to its mission,         │
│  not to any individual.                                             │
└─────────────────────────────────────────────────────────────────────┘
```

This is a one-time event. The ledger records it permanently.

---

## 6. The Public Ledger

### What's Shown (Live on Lobby)

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  💰 talent.yoga Finanzen — Januar 2026                              │
│     (aktualisiert täglich / updated daily)                          │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  DIESEN MONAT / THIS MONTH                                    │  │
│  │                                                               │  │
│  │  Aktive Nutzer:        1,247        Active users              │  │
│  │  Einnahmen:            €4,823       Revenue                   │  │
│  │  Betriebskosten:       €285         Operating costs           │  │
│  │  Zur Rückzahlung:      €3,177       To founder repayment      │  │
│  │  Entwicklungsfonds:    €907         Development fund          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  GRÜNDER-INVESTITION / FOUNDER INVESTMENT                     │  │
│  │                                                               │  │
│  │  Investiert:           €795,600     Invested                  │  │
│  │  Zurückgezahlt:        €12,340      Repaid                    │  │
│  │  Verbleibend:          €783,260     Remaining                 │  │
│  │                                                               │  │
│  │  ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  1.6%            │  │
│  │                                                               │  │
│  │  Gershon: 7,332 Stunden Entwicklung                           │  │
│  │  Mysti: 780 Stunden UX & Testing                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  DEIN BEITRAG / YOUR CONTRIBUTION                             │  │
│  │                                                               │  │
│  │  Standard (€5/Monat):                                         │  │
│  │    €0.23 → Betrieb    €3.34 → Rückzahlung    €0.95 → Entwicklung │
│  │                                                               │  │
│  │  Sustainer (€10/Monat):                                       │  │
│  │    + finanziert einen Basis-Nutzer                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  [Vollständige Finanzen ansehen / View full financials →]           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Detailed Ledger Page (Linked)

For those who click through:

- Monthly breakdown (last 12 months)
- Cost itemization (compute, hosting, APIs, etc.)
- Founder debt repayment history
- Development fund spending (what was built)
- User growth chart
- Revenue per tier breakdown

---

## 7. Implementation

### Database Schema

```sql
-- Monthly ledger snapshots
CREATE TABLE ledger_monthly (
    month DATE PRIMARY KEY,  -- '2026-01-01'
    active_users INTEGER,
    revenue_cents INTEGER,
    operating_costs_cents INTEGER,
    reserve_contribution_cents INTEGER,
    founder_repayment_cents INTEGER,
    development_fund_cents INTEGER,
    founder_debt_remaining_cents INTEGER,
    notes TEXT
);

-- Founder debt tracking
CREATE TABLE founder_debt (
    contributor TEXT PRIMARY KEY,  -- 'gershon', 'mysti'
    initial_investment_cents BIGINT,
    repaid_cents BIGINT DEFAULT 0,
    hours_worked INTEGER,
    hourly_rate_cents INTEGER
);

-- Initialize
INSERT INTO founder_debt VALUES 
    ('gershon', 73320000, 0, 7332, 10000),
    ('mysti', 6240000, 0, 780, 8000);
```

### API Endpoints

```
GET /api/ledger/current
GET /api/ledger/history
GET /api/ledger/founder-debt
```

### Lobby Component

```html
<!-- Pricing section with live ledger -->
<section id="pricing" class="lobby-pricing">
    <h2>Transparent Pricing</h2>
    
    <!-- Live stats (fetched from /api/ledger/current) -->
    <div class="ledger-summary" hx-get="/api/ledger/current" hx-trigger="load">
        <!-- Populated by HTMX -->
    </div>
    
    <!-- Tier cards -->
    <div class="tier-cards">
        <div class="tier basis">...</div>
        <div class="tier standard">...</div>
        <div class="tier sustainer">...</div>
    </div>
</section>
```

---

## 8. FAQ (For Lobby)

**Q: Is talent.yoga a business or a non-profit?**  
A: Right now, it's a business — we need flexibility to invest and grow. But our plan is to convert to a non-profit (gGmbH) once we're sustainable. The founders will donate the remaining debt, and talent.yoga will belong to its mission forever.

**Q: Why is the founder debt so high?**  
A: Building talent.yoga took 3 years of full-time work before launch. We tracked every hour. This is what it actually cost.

**Q: Will the founders get rich from this?**  
A: No. The goal is partial repayment of investment, then conversion to non-profit with modest salaries. There's no exit plan, no investors, no IPO fantasy.

**Q: What if you never pay it back?**  
A: Then the founders donate more than planned. We took this risk knowingly. The mission matters more than the money.

**Q: Why not just raise VC money?**  
A: VC money comes with strings: grow fast, monetize aggressively, sell user data, exit. We want to build something that serves job seekers, not investors.

**Q: Can I see the detailed financials?**  
A: Yes. [Link to full ledger page]. Every euro, every month.

**Q: What happens after you convert to non-profit?**  
A: The founders take modest salaries. All surplus goes to the mission — better service, lower prices, grants for job seekers in need.

**Q: Why should I pay when I can use it free?**  
A: You don't have to. But if talent.yoga helps you, paying forward helps others in the same situation. And it brings us closer to being a permanent, mission-locked resource.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Not enough paying users | Keep operating costs minimal; founders accept slow/no repayment |
| Users distrust the numbers | Monthly audit export available; consider third-party verification later |
| Competitors undercut on price | They can't undercut free; our moat is trust, not price |
| Founders take too much | Caps on salaries; allocation percentages locked in ledger logic |
| Scope creep in "development fund" | Development fund spending itemized on ledger |

---

## 10. Conversion Triggers & Timeline

### When Do We Convert?

| Trigger | Threshold | Why |
|---------|-----------|-----|
| **Runway** | 6-month operating costs in reserve | Stability |
| **Sustainability** | Revenue ≥ costs for 6 consecutive months | Not a fluke |
| **Founder agreement** | Both founders consent | It's our donation |

All three must be met.

### Realistic Timeline

| Scenario | Users needed | Time to conversion |
|----------|--------------|-------------------|
| **Slow growth** | 1,000 paying | 3-4 years |
| **Moderate** | 3,000 paying | 18-24 months |
| **Fast** | 10,000 paying | 6-12 months |

We're not racing. The goal is to build something that lasts, not something that scales and burns.

### What Happens to Hardware Investment?

**Pre-conversion:** Hardware bought with founder money is founder investment (tracked).  
**At conversion:** Hardware becomes gGmbH property. Founders can:
- (a) Donate it (most likely)
- (b) Sell it to gGmbH at depreciated value (if founders need capital back)

---

## 11. Open Decisions

| Question | Options | Recommendation |
|----------|---------|----------------|
| Show founder names on ledger? | Yes / Initials / "Founders" | Yes — builds trust |
| Show exact hours or just euros? | Both / Euros only | Both — makes it real |
| Update frequency | Daily / Weekly / Monthly | Daily stats, monthly snapshot |
| Sustainer minimum | €10 / €8 / "Pay what you want" | €10 (simple) |
| Annual discount | Yes (€50/year) / No | Yes — rewards commitment |
| Hardware investment: separate or combined? | Separate / Combined with time | Separate — easier to track |
| Conversion trigger: announce publicly? | Yes / Private until done | Yes — accountability |

---

## 11. Copy for Lobby

### Headline

**DE:** Was kostet talent.yoga?  
**EN:** What does talent.yoga cost?

### Subhead

**DE:** Weniger als du denkst. Und du siehst genau, wohin jeder Euro geht.  
**EN:** Less than you think. And you see exactly where every euro goes.

### CTA

**DE:** Kostenlos starten / Standard wählen / Sustainer werden  
**EN:** Start free / Choose Standard / Become a Sustainer

---

*Ready for review. Tear it apart or ship it.*

— Sage  
2026-01-27
