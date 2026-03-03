# talent.yoga — Step 1 Specification

## Situation Awareness / Context Detection

### (Adaptive onboarding & search flow)

Author: Nate
Date: 2026-03-02
Audience: Arden (implementation)

---

## 1. Goal

The first step of the guided search must **detect the user’s situation, intent, and emotional context** before showing job filters or career exploration.

This replaces the previous concept of starting with job sectors.

The objective is to:

* increase trust
* reduce stress
* adapt the platform to different user types
* improve matching quality
* differentiate talent.yoga from traditional job boards

This step must feel:

* calm
* respectful
* private
* optional
* non-judgmental

All questions must be skippable.

---

## 2. Why this matters

Users arrive with very different mental states:

Examples:

* Focused professional → wants speed and precision
* Career switcher → open but uncertain
* Burnout or health constraints → needs stability
* Compliance user → wants proof of job search

Traditional platforms treat everyone the same.
talent.yoga adapts to the user.

This is a core differentiator.

---

## 3. UX principles

### 3.1 Optional and skippable

Each question must include:

* “Überspringen” / “Skip”

The system should work even without answers.

---

### 3.2 Privacy-first

Answers:

* stored only if necessary
* anonymized
* editable anytime
* deletable by user

Explain this briefly in UI.

---

### 3.3 Tone

Respectful, neutral, non-clinical.

Avoid:

* diagnosis
* judgement
* pressure

---

## 4. Step 1 structure (UI flow)

### Intro panel

German:

> Jeder Mensch kommt aus einer anderen Situation.
> Manche suchen aktiv eine neue Herausforderung.
> Andere möchten Stabilität finden oder neue Wege prüfen.
>
> Diese Fragen helfen, talent.yoga an die aktuelle Situation anzupassen.
> Alle Fragen können übersprungen werden.

English:

> Everyone arrives from a different situation.
> Some are actively looking for a new challenge.
> Others want stability or to explore new paths.
>
> These questions help adapt talent.yoga to your current situation.
> You can skip any of them.

---

## 5. Questions (v1)

### 5.1 Self-perceived job chances

Purpose:

* measure optimism and urgency
* adapt coaching tone

German:

> Wie schätzen Sie Ihre Chancen ein, innerhalb der nächsten drei Monate eine neue Arbeit zu finden?

Options:

* sehr hoch
* eher hoch
* unklar
* eher gering
* sehr gering

English equivalent.

---

### 5.2 Openness to career change

Purpose:

* determine exploration depth

German:

> Besteht Interesse an einem neuen beruflichen Bereich (Quereinstieg)?

Options:

* ja
* unter Umständen
* eher nicht
* nein

---

### 5.3 Working time

Purpose:

* realistic matching

German:

> Wie viele Stunden pro Woche sollen aktuell gearbeitet werden?

Options:

* Teilzeit
* Vollzeit
* flexibel
* noch unklar

---

### 5.4 Preferred work environment

Purpose:

* stress sensitivity without stigma

German:

> Welche Arbeitsumgebung fühlt sich aktuell passend an?

Options:

* ruhig und planbar
* ausgewogen
* dynamisch
* noch unklar

---

### 5.5 Job search intention

This is a major differentiator.

Purpose:

* detect compliance vs active search

German:

> Wird aktuell aktiv eine neue Stelle gesucht oder sollen vor allem Bewerbungsaktivitäten nachgewiesen werden?

Options:

* aktiv
* beides
* vor allem Nachweis

---

## 6. System adaptation logic

### 6.1 Fast path for focused users

If:

* high confidence
* low openness to change

Then:

* skip discovery
* go directly to opportunities.

---

### 6.2 Exploration path

If:

* openness = high
  Then:
* show adjacent professions
* emphasize career expansion.

---

### 6.3 Stability mode

If:

* low stress tolerance
  Then:
* prioritize stable roles
* highlight predictability.

---

### 6.4 Compliance mode

If:

* proof focus
  Then:
* simplify process
* generate application plan
* provide documentation.

---

## 7. Visual concept

### 7.1 Layout

* one question per screen
* large, calm UI
* minimal text
* soft colors
* generous spacing

Inspired by:

* Apple onboarding
* Headspace
* Calm

---

### 7.2 Interaction

* slider or button selection
* gentle animation
* no overwhelming UI.

---

### 7.3 Feedback

At the end:

German:

> Vielen Dank. talent.yoga passt sich nun an die aktuelle Situation an.

English equivalent.

---

## 8. Data model (high-level)

Store:

* user_context
* confidence
* openness
* working_hours
* environment
* intention

Must be:

* optional
* encrypted
* editable.

---

## 9. Future extensions

Not in MVP but planned:

* mobility
* health constraints
* training readiness
* financial pressure
* relocation.

---

## 10. Expected impact

This step:

* builds trust
* improves matching
* reduces churn
* creates emotional differentiation
* enables adaptive AI coaching.

This moves talent.yoga from:
Job portal → Career navigation system.

---

End of spec.

# talent.yoga — Step 1 Specification (Update)

## Situation Awareness / Context Detection

### Collapsible Question Model

Author: Nate
Date: 2026-03-02
Audience: Arden

---

## 1. Change summary

The original design proposed a guided one-question-per-screen flow.
We will now use a **hybrid model**:

1. Initial guided onboarding
2. Persistent, collapsible self-assessment panel

This allows users to:

* understand their answers
* revise them at any time
* feel in control
* treat the system as a reflective process rather than a test

This aligns with the core philosophy of talent.yoga:

> transparency, autonomy, and calm guidance.

---

## 2. UX goals

The new model should:

* reduce pressure and anxiety
* increase trust
* support long-term use
* allow changing life situations
* create a continuous career reflection process

The panel should feel:

* calm
* editable
* stable
* personal
* respectful

---

## 3. Interaction model

### Phase 1 — Guided first pass

During first onboarding:

* one question is shown at a time
* users are guided sequentially
* each question remains skippable

This reduces overwhelm.

---

### Phase 2 — Persistent situation panel

After completion, the user sees all questions in a single structured panel.

Each question appears in collapsed form.

Example:

```
[✓] Chancen auf neue Arbeit
     eher gering
     Anpassen
```

When clicked:

```
Wie schätzen Sie Ihre Chancen ein, innerhalb der nächsten drei Monate eine neue Arbeit zu finden?

○ sehr hoch  
○ eher hoch  
○ unklar  
○ eher gering  
○ sehr gering  

Speichern
```

---

## 4. Design principles

### 4.1 Calm visual style

Use:

* generous spacing
* soft color palette
* minimal UI
* large touch areas

Inspired by:

* Apple onboarding
* Calm
* Headspace

Avoid:

* dense forms
* technical appearance.

---

### 4.2 Visibility of state

Each answer must always be visible in collapsed form.

Users should feel:

> I know what the system assumes.

---

### 4.3 Smooth animation

Expand and collapse should be:

* soft
* quick
* predictable.

---

### 4.4 Microcopy

Avoid harsh language such as:

* edit
* change.

Use:

* Anpassen
* Aktualisieren
* Überprüfen.

---

## 5. Reassurance layer

Below the panel:

German:

> Ihre Antworten helfen, die Suche besser an Ihre Situation anzupassen.
> Sie können diese jederzeit ändern oder löschen.

English equivalent.

This strengthens trust.

---

## 6. Dynamic system behaviour

The panel enables continuous adaptation.

Examples:

### 6.1 Situation evolution

If user behaviour changes:

* system gently suggests reviewing answers.

Example:

> Ihre Chancen erscheinen aktuell besser als zuvor. Möchten Sie dies aktualisieren?

No pressure.

---

### 6.2 AI coaching

Future coach can reference this context:

> Sie hatten angegeben, dass eine ruhige Arbeitsumgebung wichtig ist.

---

### 6.3 Continuous learning

The system improves recommendations based on:

* context
* interaction
* outcomes.

---

## 7. Technical considerations

### 7.1 State persistence

Answers must be:

* stored securely
* encrypted
* editable
* deletable.

---

### 7.2 Progressive enrichment

New context questions can be added later without disrupting users.

---

### 7.3 API design

Backend should support:

* partial updates
* versioning
* context history (optional).

---

## 8. Long-term vision

This panel evolves into a **personal career context dashboard**.

Later extensions:

* goals
* mobility
* health constraints
* training readiness
* relocation willingness.

---

## 9. Expected impact

This model:

* increases user trust
* supports long-term engagement
* differentiates talent.yoga
* enables adaptive AI
* improves recommendation quality.

This is a key pillar of the career navigation system.

---

End of update.

Yes. This is the right moment. Mockups will make this real and help Arden move fast.
Let’s do this as **low-fidelity conceptual mockups first** (structure + feeling), not pixel-perfect. Then you can refine.

We’ll go step by step. I’ll start with **Step 1 (Situation)** today. If you like the direction, we continue.

---

# 🧘  Step 1 Mockup (Situation / Context)

Goal:
👉 The user feels understood and safe.

This must feel like:

* a quiet conversation
* not a form
* not an assessment
* not therapy
* not bureaucracy

---

## 🌱 Overall visual direction

Soft, calm, lots of white space.
One focus at a time.
Collapsible answers after onboarding.

Visual inspiration:

![Image](https://cdn.dribbble.com/userupload/43564134/file/original-4688254ef6b58c4eca91d8a9bd462036.png?resize=752x\&vertical=center)

![Image](https://cdn.dribbble.com/userupload/43752222/file/original-0b8b0dd8cb55bfbbe2746ff062528ad6.png?resize=752x\&vertical=center)

![Image](https://miro.medium.com/v2/resize%3Afit%3A2000/1%2AztLGxsnV6whl4Tlj2Xy8hg.jpeg)

![Image](https://cdn.dribbble.com/userupload/15881745/file/original-fd8f54e2ea8d668b8b59b0ae28d64cee.png?resize=400x0)

---

## 🧩 Layout concept

### Structure

Top:

* Title
* Gentle intro

Middle:

* Question card

Bottom:

* Skip / Next

Later:

* Collapsible overview.

---

## ✨ First screen (guided entry)

### Header

**Wo stehen Sie aktuell?**

### Subtext

> Jeder Mensch kommt aus einer anderen Situation.
> Manche suchen aktiv eine neue Herausforderung.
> Andere möchten Stabilität finden oder neue Wege prüfen.
>
> Diese Fragen helfen, talent.yoga besser an Ihre Situation anzupassen.
> Alle Fragen können übersprungen werden.

### CTA

👉 *Beginnen*

This sets tone: calm, respectful.

---

## 🔹 Question 1 (confidence)

Card design:

* centered
* wide
* soft shadow
* rounded corners.

**Wie schätzen Sie Ihre Chancen ein, innerhalb der nächsten drei Monate eine neue Arbeit zu finden?**

Options:

* Sehr hoch
* Eher hoch
* Unklar
* Eher gering
* Sehr gering

Bottom:

* Überspringen
* Weiter

---

## 🔹 Question 2 (career change)

**Besteht Interesse an einem neuen beruflichen Bereich (Quereinstieg)?**

Options:

* Ja
* Unter Umständen
* Eher nicht
* Nein

Micro reassurance:

> Diese Antwort beeinflusst nur, wie breit wir suchen.

---

## 🔹 Question 3 (working time)

**Wie viele Stunden möchten Sie aktuell arbeiten?**

Options:

* Teilzeit
* Vollzeit
* Flexibel
* Noch unklar

---

## 🔹 Question 4 (work environment)

**Welche Arbeitsumgebung fühlt sich aktuell passend an?**

Options:

* Ruhig und planbar
* Ausgewogen
* Dynamisch
* Noch unklar

---

## 🔹 Question 5 (intention)

This is your killer differentiation.

**Was ist aktuell Ihr Hauptziel?**

Options:

* Aktiv eine neue Stelle finden
* Offen für Möglichkeiten
* Bewerbungsaktivitäten nachweisen

This respects dignity.

---

## ✅ Completion screen

> Vielen Dank.
> talent.yoga passt sich nun an Ihre Situation an.

CTA:
👉 Weiter zur nächsten Phase.

---

## 🔄 After onboarding → persistent panel

Inside Step 1 tab:

Collapsed list:

✔ Chancen auf neue Arbeit → eher gering
✔ Quereinstieg → unter Umständen
✔ Arbeitszeit → Teilzeit
✔ Arbeitsumgebung → ruhig
✔ Ziel → aktiv suchen

Each expandable.

This becomes the living context.

---

## 🧠 Why this works

It solves your real user cases:

### IT expert

Fast. Skip. Efficient.

### Diplompädagoge

Exploration.

### Burnout

Safety.

### Older driver

Dignity.

---

## ⚡ Important detail (high impact)

Show a small indicator later in search:

> Suche basiert auf Ihrer aktuellen Situation.

This reinforces trust.

---
# 🌿 STEP 2 — Deine Richtung / Your Direction

**Emotional goal:**
➡️ *“Where do I belong?”*

This must feel exploratory, not technical.

---

## 🧠 Key design principle

Not taxonomy.
Not filtering.
Instead: **career discovery with guardrails**.

Because:

* some users know exactly what they want
* others need orientation.

So we support both.

---

## ✨ Layout

Top:

* calm title
* short explanation

Middle:

* exploration cards
* search bar
* suggestions from embeddings.

Bottom:

* continue.

---

## 🎯 Header

**Welche Richtung interessiert Sie aktuell?**

Subtext:

> Sie können gezielt suchen oder neue Möglichkeiten entdecken.
> talent.yoga zeigt auch verwandte Berufe und Alternativen.

This reassures the IT guy:
👉 you can go straight.

---

## 🔎 Search first (important)

Large, prominent search field:

> “z. B. Elektriker, Projektmanager, Sachbearbeitung…”

As the user types:

* suggestions appear
* related roles
* real-time demand.

This respects expert users.

---

## 🧭 Exploration below

Cards:

* Technik & IT
* Verwaltung & Büro
* Gesundheit
* Bildung & Soziales
* Handwerk
* Logistik
* Gastronomie
* etc.

Each card:

* icon
* short description
* demand indicator.

Hover:

* example roles
* typical transitions.

---

## ⭐ Smart suggestions (from embeddings)

At top:

> Basierend auf Ihrem Profil könnten diese Richtungen passen.

This is your secret weapon.

---

## 🔄 Related roles panel

When selecting:

Show:

* similar professions
* transition difficulty
* market demand.

Example:

Elektriker → Solar → Gebäudeautomation → Mechatronik.

---

## 🧠 Psychological effect

User feels:

* guided
* respected
* not judged.

---

---

# 🔎 STEP 3 — Dein Niveau / Your Level

**Emotional goal:**
➡️ *“Am I good enough?”*

We must avoid shame and comparison.

---

## ✨ Header

**Wie schätzen Sie Ihr aktuelles Erfahrungsniveau ein?**

Subtext:

> Diese Einschätzung hilft uns, realistische Chancen und Entwicklungsmöglichkeiten zu zeigen.

---

## 📊 Interactive demand bars

Exactly like your mockup, but dynamic.

Levels:

* Helfer
* Fachkraft
* Spezialist
* Experte.

Each shows:

* demand
* salary range
* competition.

Overlay:
👉 your position.

---

## 🚀 Growth paths

Below:

> Viele Nutzer entwickeln sich innerhalb von 12–24 Monaten von Fachkraft zu Spezialist.

Clickable:

* required skills
* training.

This motivates.

---

## 🔄 What-if simulation

Slider:

> “Was passiert, wenn ich mich weiterqualifiziere?”

Demand + salary update.

---

## 🧠 Psychological effect

User moves from fear → possibility.

---

---

# 🗺 STEP 4 — Wo werden Sie gebraucht? / Where are you needed?

**Emotional goal:**
➡️ *“Where do I have leverage?”*

This is your biggest differentiator.

---

## ✨ Header

**Wo werden Ihre Fähigkeiten aktuell besonders gesucht?**

Subtext:

> Der Arbeitsmarkt ist regional unterschiedlich.
> Wir zeigen, wo Chancen besonders hoch sind.

---

## 🌍 Heatmap first

Map with:

* demand clusters
* intensity.

No dropdowns.

---

## 📈 Insight panel

Examples:

> In Ihrer Region: moderate Nachfrage.
> Besonders gefragt: Stuttgart, München, Nürnberg.

Also:

> Nachfrage dort ist 2,4× höher.

---

## 🔄 Flexibility slider

* Nur lokal
* Pendeln
* Umzug möglich.

Map updates.

---

## ⚖ Life factors (later)

Optional:

* cost of living
* salary
* stability.

---

## 🧠 Psychological effect

User sees strategy.

---

---

# 🎯 STEP 5 — Konkrete Möglichkeiten / Real Opportunities

We expand this slightly.

**Emotional goal:**
➡️ *“What should I do now?”*

---

## ✨ Header

**Konkrete Möglichkeiten für Sie**

Subtext:

> Diese Vorschläge basieren auf Ihrer aktuellen Situation, Erfahrung und Marktchancen.

---

## 📊 Three-column layout

### A — Strong matches

Transparent reasoning.

### B — Stretch opportunities

Motivation.

### C — Strategic alternatives

Embedding-driven.

---

## 🛠 Action tools

* Bewerben
* Speichern
* Training
* Simulation.

---

---

# 🧠 The deeper structure

This flow now maps perfectly:

| Phase       | talent.yoga |
| ----------- | ----------- |
| Shock       | landing     |
| Exploration | Step 2      |
| Reframing   | Step 3      |
| Strategy    | Step 4      |
| Action      | Step 5      |

This is powerful.

---

---

# ⚡ Critical insight

The system must:
👉 Always allow skipping.

Because:

* IT expert
* compliance user
* power users.

This flexibility is your advantage.

---

---

If you want, next we can:

* turn this into a spec for Arden
* define backend data model
* define embedding logic
* design mobile-first
* design coaching overlays.

Or we can go even deeper into one step.

What feels most useful right now?

