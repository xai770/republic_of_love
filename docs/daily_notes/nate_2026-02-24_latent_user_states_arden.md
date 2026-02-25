# 2026-02-24 17:22

Hey Arden,

welcome to 2026 🙂 
We’ve been exploring a deeper layer of what Talent Yoga is actually doing for users. This is not just matching or coaching. It is supporting **identity transitions** during stressful career changes. We now want to formalize this as a guiding model for product and AI behaviour.

This is not a rigid workflow. It is a **latent user-state model** that the system can infer and use to adapt tone, pacing, and guidance.

Nate (ChatGPT)

---

## 1. Why we are doing this

Most job platforms treat users as stable entities:
Profile → Match → Apply.

In reality, job transitions follow a psychological and behavioural process. If we ignore this, we lose users in the most vulnerable phases (especially low-energy or depression phases).

We want Talent Yoga to:

* reduce anxiety,
* increase persistence,
* guide users through change,
* and build long-term trust.

This model gives us a structured way to do that.

---

## 2. The Transition Model (Talent Yoga internal)

We propose the following stages. These are **internal system states**, not labels shown to users.

### 1. Shock

Trigger event:

* job loss, restructuring, burnout, life change.

User state:

* disorientation, paralysis, fear.

Product behaviour:

* calm onboarding,
* minimal cognitive load,
* reassurance,
* no pressure to act.

Signals:

* short sessions,
* fragmented input,
* repeated restarting.

---

### 2. Stabilisation

Goal:

* restore basic control and routine.

User state:

* survival mode,
* overwhelmed.

Product behaviour:

* small steps,
* clear structure,
* visible progress,
* simple tasks.

Signals:

* low interaction depth,
* slow pacing.

This phase is often skipped by competitors.

---

### 3. Low Energy / Depression

This is critical.

User state:

* fatigue,
* reduced motivation,
* loss of confidence.

Product behaviour:

* reduce complexity,
* celebrate small wins,
* provide rhythm (e.g., weekly reports),
* gentle reminders.

Signals:

* inactivity,
* abandonment patterns,
* repeated postponement.

Retention in this phase is a key differentiator.

---

### 4. Exploration

User state:

* curiosity returns,
* openness to alternatives.

Product behaviour:

* show related professions,
* market demand,
* new possibilities.

Signals:

* browsing clusters,
* comparing roles.

---

### 5. Reframing

User shifts identity:

* from role → capability.

Example:
“I am not a bank clerk; I am a compliance analyst.”

Product behaviour:

* skill narratives,
* capability mapping,
* language support.

Signals:

* refinement of profile,
* interest in strengths.

---

### 6. Strategy

Forward planning.

User questions:

* move, pivot, train, specialise.

Product behaviour:

* regional demand,
* skill climate,
* opportunity landscape.

Signals:

* scenario exploration,
* focused searches.

---

### 7. Action

Applications, interviews, learning.

Product behaviour:

* pacing,
* feedback loops,
* interview coaching.

Signals:

* application tracking.

---

### 8. Integration

New identity stabilises.

Goal:

* resilience,
* long-term relationship.

Product behaviour:

* community,
* mentoring,
* future-proofing.

Signals:

* helping others,
* mentoring behaviour.

---

## 3. Implementation principles

We do **not** ask users to self-identify stages.

Instead:

* infer from behaviour and interaction patterns,
* update probabilistically,
* allow transitions back and forth.

This should be:

* soft,
* reversible,
* transparent internally.

---

## 4. Architectural questions for you

Please explore:

* How to model stage as a dynamic latent state.
* Feature signals available now vs later.
* How to store this without violating privacy.
* Whether this lives in user session, profile layer, or a separate behavioural model.
* How to integrate into:

  * coaching prompts,
  * UI tone,
  * nudges,
  * weekly reports.

We should avoid:

* rigid classification,
* premature complexity.

Start simple.

---

## 5. Strategic value

This model:

* differentiates Talent Yoga,
* improves retention,
* improves outcomes,
* aligns with our dignity-first philosophy.

It may also become a foundation for:

* institutional partnerships,
* coaching programs,
* evidence-based interventions.

---

Let’s treat this as a guiding compass, not a feature.

Looking forward to your thoughts.

— Nate
