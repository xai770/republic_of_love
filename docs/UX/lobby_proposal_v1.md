# talent.yoga Lobby — Structural Proposal (v1)

**Date:** 2026-01-26  
**Author:** Sage  
**Reference:** NotebookLM landing, talent.yoga mockup (Maria dashboard)  
**Status:** Draft for review

---

## 1. What the Lobby Must Do

The lobby is the **first 30 seconds**. It answers three questions:

1. **What is this?** → A job search companion, not a job board
2. **Is this for me?** → Yes, if you're looking for work and want help
3. **What do I do now?** → One clear action

Everything else is noise.

---

## 2. Reference Analysis: NotebookLM

### What NotebookLM does well:

| Element | Why it works |
|---------|--------------|
| **Centered title** | "Untitled notebook" — no clutter, immediate focus |
| **Left: Sources** | Context lives here, not in your face |
| **Center: Chat** | The primary interaction is conversation |
| **Right: Studio** | Tools available but not demanding |
| **Muted palette** | Dark theme, low contrast, no alarm colors |
| **Single CTA** | "Add sources" — one thing to do |

### What we can steal:

- **Three-column possibility, single-column default** — Start simple, expand when needed
- **Chat as primary interface** — The yogi talks to you
- **Tools as secondary** — Reports, dashboard exist but don't compete
- **No gamification** — No badges, streaks, urgency

### What we can't copy:

- NotebookLM assumes you *have* something (sources to upload)
- We must handle the person who has *nothing yet* — no profile, no CV, just fear

---

## 3. Reference Analysis: talent.yoga Mockup (Maria)

### What the mockup shows:

| Element | Observation |
|---------|-------------|
| **"Willkommen, Maria!"** | Personal, warm, named |
| **Three stat cards** | Dashboard (5), Lebenslauf (85%), Stellenangebote (18) |
| **Job listings** | Immediate value — "here's what we found" |
| **Support chat widget** | Lower-right, conventional placement |
| **Left nav** | 8 items — too many for first visit |

### What works:

- Warm greeting with name
- Immediate matches visible
- Stats give orientation

### What doesn't work (for lobby):

- **This is a dashboard, not a lobby** — Maria is already logged in, has a profile
- **8 nav items** — Overwhelming on first visit
- **Chat is disconnected** — Widget in corner, no context
- **No pricing** — We need to show this in lobby (you said so)

---

## 4. Proposed Lobby Structure

### For: Anonymous visitor (not logged in)

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Logo]                                      [Anmelden] [Registrieren] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                                                                     │
│                    talent.yoga                                      │
│                                                                     │
│          Dein persönlicher Begleiter für die Jobsuche.              │
│          Your personal companion for the job search.                │
│                                                                     │
│                                                                     │
│     ┌──────────────────────────────────────────────────────┐        │
│     │                                                      │        │
│     │   [  30-second video: "What is talent.yoga?"  ]     │        │
│     │                                                      │        │
│     └──────────────────────────────────────────────────────┘        │
│                                                                     │
│                                                                     │
│                  [ Kostenlos starten / Start free ]                 │
│                                                                     │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Was talent.yoga anders macht:                                     │
│   What makes talent.yoga different:                                 │
│                                                                     │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│   │  🧘 Yogi    │  │  📝 Profil  │  │  💼 Matches │                 │
│   │  Hilft dir  │  │  Versteht   │  │  Findet     │                 │
│   │  denken     │  │  dich       │  │  passende   │                 │
│   └─────────────┘  └─────────────┘  └─────────────┘                 │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Preise / Pricing                                                  │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│   │  Basis          │  │  Standard       │  │  Premium        │     │
│   │  Kostenlos      │  │  €X/Monat       │  │  €Y/Monat       │     │
│   │  • Feature      │  │  • Feature      │  │  • Feature      │     │
│   │  • Feature      │  │  • Feature      │  │  • Feature      │     │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   [Impressum] [Datenschutz] [Kontakt]        🇩🇪 Deutsch | 🇬🇧 English │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Design notes:

| Element | Decision | Rationale |
|---------|----------|-----------|
| **Bilingual** | German primary, English secondary | German market, but English option visible |
| **Video** | 30s max, optional autoplay (muted) | Shows, doesn't tell |
| **One CTA** | "Kostenlos starten" | Not "Sign up" — too transactional |
| **Three cards** | Yogi / Profil / Matches | The three things we do |
| **Pricing visible** | In lobby, not hidden | Builds trust, filters tire-kickers |
| **No chat widget** | Not yet | Chat comes after you enter |
| **Language toggle** | Footer | Present but not intrusive |

---

## 5. Proposed Lobby Structure

### For: Logged-in user (returning)

When Maria returns, she doesn't see the lobby. She sees **her dashboard**.

But if she explicitly clicks "Start" / "Home", she sees:

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Logo]  [Home] [Profil] [Jobs] [Chat] [Hilfe]        Maria ▼       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Willkommen zurück, Maria.                                         │
│                                                                     │
│   ┌────────────────────────────────────────┐                        │
│   │  Dein Status:                          │                        │
│   │  • Profil: 85% vollständig             │                        │
│   │  • Neue Matches: 3 seit gestern        │                        │
│   │  • Bewerbungen: 2 ausstehend           │                        │
│   └────────────────────────────────────────┘                        │
│                                                                     │
│   Was möchtest du heute tun?                                        │
│                                                                     │
│   [ Meine Matches ansehen ]  [ Profil vervollständigen ]            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

This is **orientation, not dashboard**. It says: "Here's where you are. Here's what you might do."

---

## 6. Emotional Checklist (from Icon Charter)

Before finalizing, ask:

- [ ] Can a 60+ user understand this instantly?
- [ ] Does it feel calm at 8am and at 2am?
- [ ] Does it quietly say: "You're okay"?
- [ ] Is there exactly **one** obvious action?
- [ ] Is pricing honest and visible?
- [ ] Does it work without JavaScript?

---

## 7. Open Questions

1. **Video:** Do we have one? Do we need to make one? Can we launch without it?
2. **Pricing tiers:** What are they? (Needed for the cards)
3. **Imagery:** Photos? Illustrations? Abstract shapes? (Icon Charter says "no photos of people" — confirm?)
4. **Mobile:** This wireframe is desktop. Mobile = single column, same hierarchy.

---

## 8. Next Steps

| Step | Owner | When |
|------|-------|------|
| Review this proposal | xai, Mysti | This week |
| Define pricing tiers | xai | Before lobby build |
| Decide on video | xai | Can defer |
| Sketch mobile version | Sage | After desktop approved |
| Build HTML prototype | Arden | After approval |

---

*This is a proposal, not a decision. Tear it apart.*

— Sage
