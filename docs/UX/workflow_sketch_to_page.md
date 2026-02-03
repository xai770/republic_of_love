# Workflow: Sketch → Page

**Purpose:** How xai and Sage iterate on visual page design  
**Date:** 2026-01-26  
**Status:** Proposed

---

## The Problem

Sage cannot render HTML. Sage cannot "see" a running webpage.

But we need to design pages together.

---

## The Solution: Describe → Generate → Screenshot → Refine

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. DESCRIBE                                                        │
│     xai sketches (paper, Figma, words) → shares with Sage           │
│     Sage asks clarifying questions                                  │
│     Agreement on: structure, hierarchy, emotional intent            │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  2. GENERATE                                                        │
│     Sage produces: HTML + CSS (or Jinja2 template)                  │
│     Arden reviews for technical sanity                              │
│     Code goes into repo                                             │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  3. RENDER                                                          │
│     xai opens page in browser                                       │
│     xai takes screenshot                                            │
│     xai shares screenshot with Sage                                 │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  4. REFINE                                                          │
│     xai: "The spacing here is wrong" (annotate screenshot)          │
│     xai: "This doesn't feel calm"                                   │
│     xai: "The button should be more prominent"                      │
│     Sage updates code → goto step 3                                 │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  5. VALIDATE                                                        │
│     Mysti reviews on real device                                    │
│     "Would you use this?"                                           │
│     If no → back to step 1 with new understanding                   │
│     If yes → ship it                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tools & Artifacts

### Input formats Sage can work with:

| Format | Works? | Notes |
|--------|--------|-------|
| **Screenshot** (PNG/JPG) | ✅ Yes | Best for "make it look like this" |
| **Annotated screenshot** | ✅ Yes | Best for "fix this part" |
| **ASCII wireframe** | ✅ Yes | Best for structure discussion |
| **Written description** | ✅ Yes | Best for emotional intent |
| **Figma link** | ❌ No | Can't access external URLs live |
| **Figma export** (PNG) | ✅ Yes | Export and share as image |
| **PDF** | ⚠️ Partial | Text extractable, layout lost |

### Output formats Sage can produce:

| Format | When to use |
|--------|-------------|
| **HTML + inline CSS** | Quick prototype, single file |
| **HTML + Tailwind** | If we adopt Tailwind |
| **Jinja2 template** | Production templates |
| **CSS-only changes** | Refinement iterations |
| **ASCII wireframe** | Early structure discussion |

---

## Communication Protocol

### When sharing a screenshot:

**Good:**
> "Here's the lobby page. The header feels too heavy. The CTA button gets lost. I want it to feel more like the NotebookLM reference."

**Better:**
> "Here's the lobby page [screenshot attached].  
> Problems:  
> 1. Header: too heavy, should be lighter  
> 2. CTA button: gets lost, needs more contrast  
> 3. Overall: should feel calmer, more like NotebookLM  
> Reference: [NotebookLM screenshot attached]"

### When giving feedback:

| Instead of | Say |
|------------|-----|
| "It looks wrong" | "The spacing between X and Y feels too tight" |
| "I don't like it" | "This doesn't feel calm because [reason]" |
| "Make it better" | "Can we try: [specific alternative]?" |
| "Fix the colors" | "The blue is too saturated, try something closer to #4A90A4" |

---

## Iteration Speed

### Target: 3 iterations per page

| Iteration | Goal | Time |
|-----------|------|------|
| 1 | Structure right | 1 hour |
| 2 | Styling right | 30 min |
| 3 | Polish | 30 min |

If we're on iteration 5+, something is wrong with the brief. Stop and re-align.

---

## File Naming Convention

```
docs/UX/
├── lobby_proposal_v1.md          # Structural proposal (this doc)
├── lobby_wireframe_v1.png        # ASCII or image wireframe
├── lobby_screenshot_v1.png       # First render
├── lobby_screenshot_v1_annotated.png  # With xai's notes
├── lobby_screenshot_v2.png       # After first revision
└── lobby_final.png               # Approved version

templates/
├── lobby.html                    # Production template (Jinja2)
└── lobby_prototype.html          # Standalone prototype (for testing)
```

---

## Roles

| Who | Does what |
|-----|-----------|
| **xai** | Provides vision, sketches, emotional direction, final approval |
| **Sage** | Translates vision to structure, generates code, iterates |
| **Arden** | Reviews code for technical issues, integrates into app |
| **Mysti** | Validates on real device, "would I use this?" test |

---

## Anti-Patterns

### ❌ Don't:

- Send Sage a Figma link and expect magic
- Skip the description step ("just make something")
- Iterate endlessly without Mysti validation
- Let perfect be the enemy of good

### ✅ Do:

- Share references (screenshots of sites you like)
- Be specific about what's wrong
- Accept "good enough for now, improve later"
- Test with real humans early

---

## Example Session

**xai:**
> Here's my paper sketch of the lobby [photo attached].  
> Key points:
> - Logo top left
> - Big tagline centered
> - Video placeholder below
> - Single CTA button
> - Pricing cards at bottom
> - Bilingual (DE primary, EN secondary)
> 
> Should feel like NotebookLM — calm, no pressure.

**Sage:**
> Got it. Questions:
> 1. Video: placeholder or real embed structure?
> 2. Pricing: 2 or 3 tiers?
> 3. Footer: what links?

**xai:**
> 1. Placeholder for now
> 2. 3 tiers
> 3. Impressum, Datenschutz, Kontakt, language toggle

**Sage:**
> [Generates HTML]
> Here's the first version. Render it and send me a screenshot.

**xai:**
> [Screenshot attached]
> Issues:
> - Tagline font is too small
> - Pricing cards need more padding
> - Footer links should be smaller

**Sage:**
> [Updates CSS]
> Try this version.

**xai:**
> [Screenshot attached]
> Better. Ship it.

---

## Ready to Start

When you have a sketch or reference for the lobby, share it and we'll begin.

— Sage
