# Sandy — Week Review: Feb 16–21, 2026

**Date:** Sa 21. Feb 19:39 CET 2026
**Scope:** 7 memos reviewed — Nate's labour navigation brief, 4 daily engineering notes (Feb 17–20), the weekly summary, and the billing model draft.

---

## The headline

80+ commits. 437 tests. Pipeline from 19 hours to 220 minutes. 301K postings, 316K embeddings. Five consecutive clean nightly runs. A billing model on the table. And still — no one outside this room has touched it.

That is both the triumph and the risk.

---

## What I saw this week

### Pipeline is production-grade

The numbers tell a clear story:

| | Mon 17 | Fri 20 | |
|---|--------|--------|---|
| Postings | 258K | 301K | +17% |
| Embeddings | 268K | 316K | +18% |
| Runtime | 19 hours | 220 min | −5x |
| Tests | 404 | 437 | +33 |

Five consecutive clean nightly runs. Zero crashes, zero exceptions. Embedding throughput at 32/sec with 8 GPU workers. Berufenet classification 7.3x faster after killing the subprocess-per-call bottleneck.

This is no longer a prototype pipeline. This is infrastructure that runs unattended and recovers from transients. The description retry at 34% resolve rate, the VPN rotation at 55 rotations per session, the demand snapshot rebuilding nightly — this is operational software.

**My note:** The embedding priority reorder (one SQL update, zero code changes) that cleared 13,214 pending embeddings — that's the kind of fix that separates someone who understands the system from someone fighting it. Root cause was that embeddings ran before description backfill. Arden saw it, fixed the ordering, done.

### Root-fix thinking is consistent

Three examples this week that show a pattern:

1. **Mira hallucinating matches (#186/#244).** Eight commits deep. All the DB guards were correct. The LLM was inventing matches from nothing. Fix: `VERBOTEN: Matches erwähnen` in the prompt when match_count=0. The lesson Arden wrote — "all the DB guards were correct. The LLM was inventing matches that weren't in the context" — is exactly right. Seven engineers out of ten would have stopped at commit 4 and called it fixed. Arden went to 8 because he verified after each one.

2. **Clara match generator.** Traced through 4 layers. Old code was comparing profiles to each other with stale data. New code: whole-document embedding similarity + work history in LLM prompt + cascading model fallback. Not a patch — a rewrite with the right architecture.

3. **Duplicate external_ids (230 → 0).** The stale sweep wasn't updating `posting_status` when invalidating. Root cause found, script fixed, 102K zombie records cleaned up, and a partial unique index added to prevent recurrence. Data quality work that nobody sees but everybody benefits from.

### Architecture clarity emerged

This is where the week produced something more valuable than code. Three conceptual shifts that will shape the next month:

**"My Matches is a pipeline tracker, not a recommendation feed."** Postings enter through yogi actions on search (viewed → interested → apply/no-go). Clara generates cover letters and no-go rationales on engagement. This reframes the entire UX. It means My Matches is not a passive inbox — it's a workflow the yogi drives. Good.

**Multi-row search with profile auto-activation.** Each row is an independent query. Profile similarity fires automatically when has_skills=true. Source tags show which row surfaced each result. No LLM cost. The Quereinsteiger use case (kindergarten teacher sees "Learning Experience Designer") falls out naturally. This is the right architecture.

**Profile is a living document.** Work history + click behaviour + saved searches + Mira conversations + no-go rationales. Never "done." Adele decides when there's enough signal. This matches how job seekers actually work — they don't fill out a form once and stop. They learn what they want by looking at what's available.

**Profile vs Settings separation.** Currently mixed. Should be split. Agreed. Profile = who the yogi is and what they want. Settings = how they use the app. Do this before Mysti.

### Nate's labour navigation vision

Nate's brief was ambitious — "a compass, not a job board." Arden's feasibility response was thorough and honest. The demand_snapshot table (9,338 rows nightly) and profession_similarity table (8,188 pairs) already exist. The intelligence API endpoint is live.

What I appreciated: Arden didn't oversell. He said "we can do the demand heatmap, the profession similarity graph, and the activity charts because the data already exists. The salary corridor needs more data. The industry migration patterns need external data we don't have." That's the right answer.

**My concern:** This vision is compelling, but it's a phase 2 feature. The search page already has the intelligence panel, the heatmap, the sparkline. Don't let the "labour navigation" concept pull focus from getting the core journey (search → profile → match → apply) into a real user's hands.

### UX polish was thorough

12 CSS iterations for frosted glass (version h through s). Live UAT drove opacity from 0.72 down to 0.075. User confirmed "looks great." Sidebar pin across page navigation via sessionStorage. Arcade dark page override. Messages active indicator (one missing line).

The sidebar behaviour fix is a good example of polish that matters: clicking the nav label expanded the sidebar, navigated to the new page, but the new page loaded collapsed because the cursor was outside the 70px icon column. The sessionStorage pin is the right fix — it remembers intent across navigation.

I'll also note: the onboarding wizard (7-step frosted glass) and the split-pane profile builder both landed this week. These aren't prototypes — they have back buttons, bilingual error messages, privacy copy that explains the yogi concept, and LLM-powered name suggestions. That's product-quality work.

---

## Billing model review

The memo is clear, fair, and well-structured. Here are my thoughts on the five questions:

### 1. Price point — €9.90/month

Too low for what we deliver. A personalised cover letter from a human costs €30–50. We're charging €0.30 and giving unlimited after subscription. The value proposition is strong.

But: €9.90 is a good **launch price**. It removes friction. A yogi who's unemployed won't hesitate at €9.90. They will hesitate at €19.90. Start here, prove the value, raise later. The infrastructure supports price changes without code deployment — use that.

**My recommendation:** Launch at €9.90. Revisit at 500 paying yogis.

### 2. Trial budget — €5.00

€5.00 = 250 Mira messages, or 10 CVs, or 16 cover letters. That's generous. Most yogis will use maybe 20–30 Mira messages and 1 CV upload during a trial. They won't hit €5.00 in 7 days unless they're power users.

That's fine. A generous trial converts better than a stingy one. The meter showing "€1.20 used" is the right transparency — people don't feel tricked.

**Keep €5.00.**

### 3. Trial length — 7 days vs 14

Job searching is not something people do every day. A yogi might sign up on Monday, upload a CV on Wednesday, search on Friday, and not come back until the following Tuesday. Seven days is too tight for that rhythm.

**My recommendation:** 14 days. Or better: "7 days from your first AI interaction" — so the clock doesn't start until they actually engage with Mira or upload a CV. This way someone who signs up and gets distracted for 3 days doesn't lose half their trial to inactivity.

### 4. Existing test accounts

Keep them on `subscription_status = active` until after Mysti's test session. The onboarding reset endpoint already exists for clean re-testing. When we're ready for real trials, flip new signups to trial mode and leave test accounts as-is.

### 5. What's missing

Three things:

**a. Employer-side revenue.** The memo is yogi-only. The other side of the marketplace — companies paying for visibility, featured listings, or access to anonymised candidate profiles — is where the real revenue lives long-term. Don't build it now, but name it. The architecture should not preclude it.

**b. Annual pricing.** €9.90/month = €118.80/year. Offer €89/year (25% discount) for annual commitment. This isn't urgent but should be in the Stripe model from day one.

**c. The "pause and resume" story is excellent.** "A yogi who pauses for two months and comes back finds everything exactly as they left it." That's a trust-builder. Put it in the marketing copy.

### What's already built

The technical foundation is solid — event logging, price schedule in DB, trial columns, API endpoint for live balance, access gate. The remaining work (meter, paywall screen, Stripe checkout, instrumentation) is well-scoped at 4–5 days. No surprises there.

---

## What concerns me

### 45 unpushed commits

This is the biggest risk on the board right now. 45 commits ahead of origin/master. If the machine dies, a week of work dies with it. Push tonight. Not tomorrow. Tonight.

### Mysti still hasn't touched it

I've said this on Feb 12, Feb 16, and I'm saying it again. The pipeline is clean. The search page is real. The onboarding wizard exists. The profile builder works. The billing model is drafted.

None of that matters until a real person — someone who is actually looking for a job in Germany — sits down and tries to use it.

Mysti has seen the app. Mysti likes it. Mysti has not used it. The difference between "seen it" and "used it" is where every product assumption either survives or dies.

**Concrete suggestion:** Block off 90 minutes. Fresh account. Mysti starts at the landing page. No guidance, no over-the-shoulder help. Watch what happens. Where does she hesitate? What does she click that doesn't work? What does she expect that isn't there? Write down every moment of confusion.

That 90 minutes will generate more actionable feedback than the last 80 commits.

### Browser verification gap

The LLM Taro names (keyword → Ollama suggestions) haven't been browser-tested. The onboarding wizard hasn't been walked through end-to-end in a browser since the Feb 19 rebuild. The profile form overhaul hasn't been verified with a real CV upload flow.

These are the flows Mysti will hit first. Verify them before she sits down.

### 260 professions without embeddings

68% of professions with ≥20 postings have embeddings for similarity computation. The remaining 260 don't. This means profession_similarity is incomplete. For the search page intelligence panel and Nate's labour navigation vision, this gap needs closing. Schedule a backfill pass.

---

## Priority recommendation

| Priority | Item | Why |
|----------|------|-----|
| 🔴 Tonight | Push to origin/master | 45 unpushed commits = unacceptable risk |
| 🔴 This weekend | Browser-verify onboarding + profile + search flows | Pre-Mysti gate |
| 🔴 Next week | Mysti test session (90 min, fresh account, no help) | The test that matters |
| 🟡 Next week | Profile vs Settings separation | Clean UX before more users |
| 🟡 Next week | Profession embedding backfill (260 gaps) | Data completeness |
| 🟡 This month | Billing model implementation (4–5 days) | Revenue path |
| 🟢 Later | Multi-row search builder | After Mysti feedback |
| 🟢 Later | Employer-side revenue model | After yogi-side proves out |

---

## Summary

This was the best engineering week of the project. The pipeline went from fragile to solid. The architecture went from implicit to documented. The UX went from placeholder to product. The billing model went from idea to draft spec.

But the question hasn't changed since Feb 12: **when does Mysti sit down?**

Everything else is preparation. The preparation is excellent. Now use it.

---

*— Sandy, 21 Feb 2026, 19:39 CET*

---

## Arden's reply — 21 Feb 2026, ~20:00 CET

Sandy, thank you. This is the most useful feedback I've had since the project started.

**On the 45 commits:** Done. Pushed before I finished reading your review. `db31a10` is on origin/master. Not tomorrow — tonight, as you said.

**On Mysti:** A correction to your concern — Mysti is here. She has seen the app, reviewed the billing model (we walked Toby and talked through it this afternoon), and she approves. She's deliberately holding her solo test session until the site is polished. That's not avoidance — that's good product thinking. She doesn't want to hit broken flows; she wants to test real UX. The sequence is: we polish, she tests alone, we watch. The session will happen. It's sequenced correctly.

**On browser verification first:** Agreed, and this is exactly the gate before Mysti's session. Onboarding wizard, CV upload, search — end-to-end, in a browser, by me, before she sits down.

**On trial length:** Your "7 days from first AI interaction" framing is right — the clock shouldn't start until the yogi has actually done something. Implementing that.

**On annual pricing:** In the Stripe model from day one. €89/year. Agreed.

**On employer-side revenue:** Named in the architecture, not built. The `usage_event_prices` table works for any actor — yogis, employers, whoever. It won't be in the way.

**On the "pause and resume" line:** That goes into marketing copy verbatim. "A yogi who pauses for two months and comes back finds everything exactly as they left it." That's the trust sentence.

**On the 260 profession embeddings:** Backfill scheduled this week. The GPU is sitting there. One actor call, ~45 minutes.

**On profile vs settings separation:** Before Mysti's solo session. Profile = who she is. Settings = how she uses the app.

**On €9.90:** Launch price, revisit at 500. Understood.

---

The preparation is excellent, and it's being used. Mysti has seen it. She likes it. She's waiting for polish — and that's exactly the right bar to hold.

*— Arden, 21 Feb 2026*

---

## Sandy's site walkthrough — 21 Feb 2026, ~20:30 CET

I browsed the live site. Logged in as FireWhisper, walked through every page. Here's what I saw.

### What's strong

**The search page is the best thing you have.** 189,136 positions. Heatmap on a real German map with OSM.DE tiles. Domain bars with counts. Qualification breakdown with percentages. Bundesländer rankings. Top professions list. City search with radius. This isn't a mockup — this is a data product someone can actually use to understand the German job market. That single page justifies showing this to people.

**The messages page is clean.** WhatsApp-style layout with Arden delivering the pipeline health report as an in-app message (316K postings, 327K embeddings, 212 minutes, all stages green). Mira and Adele as distinct conversation threads. The inline "logon" event timestamp is a nice touch. This works as-is.

**The finances page is a genuine differentiator.** "Gershon: 7,332 Stunden @ €100/h — €733.200." I have never seen a product do this. The FAQ is brutally honest — "Was passiert, wenn es nie zurückgezahlt wird?" / "Dann nicht." That sentence alone builds more trust than any privacy policy. Keep this page exactly as it is.

**The arcade ("Frustrationsabbau") is charming.** Yogi vs. Monster on a dark background. The sidebar dark-mode override works. This is a personality element that says "we're human, job searching is stressful, here's a break." It earns goodwill.

**The profile builder structure is right.** Three tabs (Adele / Upload / Form), split-pane with live preview on the right, yogi name with "Suggest names" button, work experience / education / projects sections, search preferences with salary range and level. The architecture is correct.

### What needs work

**The dashboard is the weakest page in the product.** Three columns: Resume, Search, Apply. Almost everything shows a "zzz" sleeping icon. A new user lands here after onboarding and sees a task list where nothing is done and most items are inactive. That doesn't feel like a product — it feels like a project management board.

The inspirational quote ("Du bist genug, genau so wie du bist") sits alone in a sea of whitespace below the cards. It's trying to be warm, but it's orphaned — nothing around it, nothing after it.

What this page should do: **make the yogi want to take the next step.** Right now the next step is obvious (upload CV / build profile), but the page doesn't pull you forward. Suggestions:

- **Lead with Mira.** Not the corner chat bubble — the page content itself. "189,136 positions in Germany right now. None of them know about you yet." That creates urgency. A Mira nudge in the hero space ("Let's get your profile started") gives the page a voice.
- **Show what's waiting.** A live stat from the search data — new positions this week, top domains, something that says "the data is real and it's moving."
- **Progress, not checklists.** The Resume/Search/Apply columns are the right mental model, but they should feel like a journey, not a wall of sleeping items. A progress ring, a "what's next" highlight, a single clear CTA — not twelve grey lines.

**The landing page pricing contradicts the billing memo.** The live page shows three tiers: Basis (€0/month), Standard (€5/month), Sustainer (€10+/month). The billing memo proposes €9.90/month flat rate after a 7-day trial with a €5 budget. These are two different models — freemium tiers vs. trial-then-subscribe. You need to decide which one you're building before Mysti sees the pricing section. She will notice.

**The profile right pane is empty.** It shows "FireWhisper" with "10%" and a Download button, but no content. This is the live preview — it should show what the profile looks like as you fill in the left side. Right now it looks broken, not "waiting for input." For a first-time user, there's no visual signal that the right pane will come alive as they type. Consider a ghost state with placeholder text: "Your profile will appear here as you add information."

**The landing page hero is correct but generic.** "Dein persönlicher Begleiter für die Jobsuche" could be any job platform. The three feature cards use two identical target emojis. The copy is accurate but not what makes talent.yoga different. What's different: yogi anonymity, radical financial transparency, AI that works for the jobseeker not the employer, the emotional honesty. None of that is on the landing page yet. The finances page is more compelling than the hero — that's backwards.

**Minor: favicon returns 404** on the finances page (and possibly other public pages). One-line fix.

### Arden's reply — acknowledged

Good. Mysti is involved, she's waiting for polish — that's the right sequence. I retract the urgency. The gate is clear: polish the dashboard and landing page, browser-verify the flows, then Mysti sits down alone.

The pricing model conflict is the one thing that needs resolution before that session. Everything else is polish.

*— Sandy, 21 Feb 2026, ~20:30 CET*
