# Memo to Arden

**Subject:** Search Page UI Review and Bottom Player Messaging

Hi Arden,

First of all: the current implementation of the search page looks **excellent**. The structure is clear and calm, and the interaction model is becoming very intuitive. The overall hierarchy now reads well:

**Cards → Filters → Results**

The three cards feel approachable and clearly communicate that the user is configuring *how the system searches*, rather than filling out a form. That distinction is important and the design is doing a good job supporting it.

Below are a few refinements we discussed.

---

# 1. Bottom “Player” Messaging

The player at the bottom of the screen is a great idea. Having a display within it will work.  It visually suggests **guidance without forcing onboarding**, which matches the philosophy of the site.

However, the text shown there should remain **short, calm, and neutral**. If it becomes too long or promotional, it will quickly feel like advertising or noise.

The message should communicate only three things:

1. You can start a **guided flow** using the play button
2. You can also **explore freely**
3. **Help is available** via chat

Recommended baseline wording:

**Option A (recommended)**
Welcome to the search page.
Press ▶ to start the guided setup, or explore the filters at your own pace.
Need help? Use the chat in the lower right corner.

Alternative (slightly friendlier):

Welcome to talent.yoga.
Press ▶ to start the guided search, or explore freely.
Questions? The chat in the lower right is always available.

---

# 2. Even Better for a Scrolling Player

Because the UI element visually resembles a **media player**, users will naturally expect **short rotating hints**, not a single long sentence.

A better pattern would be a small rotation of hints:

**Hint 1**
Press ▶ to start the guided search.

**Hint 2**
You can skip any step and adjust filters later.

**Hint 3**
Need help? Use the chat in the lower right.

These can rotate slowly and will feel more natural with the ticker-style display.

---

# 3. Positive UX Observations

A few elements are working particularly well:

* The **card layout** makes the search configuration feel lightweight and approachable.
* The **green outlines** subtly communicate that these are active controls.
* The **top step navigation** (Start → Field → Qualification → Location → Postings) gives users a clear mental model of the process.

Overall, the page now feels much more like a **tool for exploration** rather than a form to complete, which is exactly what we want.

---

# 4. Minor Copy Direction

The tone across the page should continue to follow this principle:

**User decides → system searches**

For example:

“Choose how we search”
or
“Lege fest, wie wir suchen”

This framing keeps the user in control and avoids the bureaucratic tone that job platforms often accidentally create.

---

# Summary

The current implementation is very strong. The main improvements now are:

* Keep the **player message minimal**
* Prefer **rotating hints instead of a long scrolling sentence**
* Maintain the **user-in-control tone** in UI copy

Great work on the layout and interaction flow.

— Nate
