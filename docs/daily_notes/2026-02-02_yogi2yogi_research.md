# Daily Note: Yogi-to-Yogi Connection Research

**Date:** 2026-02-02 16:05 CET  
**From:** Gershon  
**To:** Sandy  
**Re:** Doug design, tier confirmation, yogi-to-yogi chat GDPR/DSA research

---

## Hi Doug

Named in honor of Doug Engelbart. Mother of all demos.

1. Doug is an actor. You ask him "search for Company X, see what you can find out about them. Who works there, what they do, what the customers say about them etc".
2. Doug searches for these terms in DDG. He curls each URL and looks for relevant information
3. If he finds it, he appends it to his notes. These he will use after the search to create the report.
4. If the website contains further URLs, Doug curls them too. 
5. Of course Doug knows what sites he already visited. And he knows how many tokens he already spent. Every curl is a token. After 20 tokens, the search stops. Unless, of course, you are a premium yogi...

---

## Three Tiers for Now

...we can always add another tier later.

---

## Yogi-to-Yogi Chat

Yes, it's risky. And yes, it needs consent. And yes, it needs to be clear that these are moderated discussions. Adele is in there and can stop the conversation if things go south fast.

### Sis's Research (Perplexity.ai)

You *can* allow yogis to exchange contact details in the chat, but it creates some GDPR and platform-liability risk that you need to actively manage rather than ignore.

### GDPR Angle: Personal Data in Chat

- Email, phone, socials etc. are personal data, so once they're exchanged in your chat, you (talent.yoga) are the **data controller** for that processing and must have a legal basis, transparency, and security in place.
- Live chats and chatbots are fine under GDPR if you clearly explain that personal data shared in conversations may be stored and processed, and you give access/erasure rights and appropriate retention limits.
- Letting users voluntarily share their own contact details is generally acceptable if this is optional, purpose-limited (e.g. to connect with each other), and explained in the privacy notice and terms.

### Platform and DSA / Safety Angle

- As a platform hosting user-to-user content, your main legal risk is around **illegal or harmful content**, not normal contact exchange; EU rules distinguish illegal content from content that is only against your own terms.
- You are not under a general obligation to monitor all chat content, but once you become aware of illegal content or conduct (harassment, exploitation, etc.), you must act quickly (e.g. remove, block, or terminate conversation), which aligns with your Adele-moderation idea.
- Model rules on online platforms emphasise that platforms can be liable if they ignore conduct "likely to cause … a violation of privacy … or a violation of another similar right" and fail to take adequate protective measures.

### Practical Way to Do It Safely

- Allow yogis to share contact details, but:
  - Make it explicit in ToS/privacy that the chat is not a secured private channel and that voluntarily shared contact data is visible to the other party and processed by you for the purpose of enabling connection.
  - Let Adele warn before exchange, e.g. "Only share contact details if you are comfortable; you do this at your own responsibility, and you can ask us to delete chat history."
  - Implement logging, retention limits, and user rights (export/delete chat history) for all conversations that include contact information.
- If you *prohibit* contact exchange in your terms and then don't effectively moderate it, that's actually messier: you create a rule you can be judged against without really reducing risk.

### A Wording Sketch

> Yogis may choose to share their own contact details or other personal information with other yogis in the chat. This is entirely voluntary. We process such information as part of providing the chat service and to enable these interactions. Please only share information you are comfortable disclosing. We log chat content for security, abuse-prevention, and legal compliance, and we may intervene or terminate conversations that breach our community guidelines. You can request access to, or deletion of, your chat data at any time, in line with our Data Protection Notice.

---

## The Incognito Chat Question

Not storing the chat transcript reduces some GDPR and data-breach risk, but it also removes important protections and can even create new compliance problems.

### How "Incognito Chat" Helps

- GDPR likes **data minimisation** and **storage limitation**, so not retaining content at all is a strong way to minimise what you hold and what can leak or be misused.
- If the chat is purely social/peer support, and you don't need a history to provide the service, having ephemeral conversations is defensible as "we only process what's technically necessary in the moment."
- You also largely avoid DSAR headaches about exporting/deleting chat logs, because there are no transcripts to retrieve.

### Where It Can Hurt or Backfire

- In regulated contexts (e.g. financial services, employment decisions, harassment reports), regulators increasingly expect **records of business communications**; using ephemeral messaging can be criticised for undermining accountability or evidence preservation.
- Ephemeral messaging can be seen as enabling people to hide abuse or discrimination because there is no audit trail, which can be problematic if a yogi later says, "I was harassed in this chat, and you have no logs."
- If Adele actively moderates (terminating "when things go south"), having *zero* protocol makes it harder to justify moderation decisions or defend against "you censored me unfairly" claims.

### A Middle Path That Usually Works Better

- Make chats **pseudo-incognito** instead of fully unlogged:
  - Do not show history to users after the session, and keep transcripts only server-side for a short, fixed period (e.g. 7–30 days) for safety, abuse handling, and legal defence.
  - Clearly state this in the privacy notice: that chats are not permanent, are stored briefly, and then are deleted or anonymised under a strict retention policy.
  - Log minimal metadata (timestamps, participants, moderation actions) even if you drop full content; this still gives you an audit trail without full surveillance.
- If you *do* choose true incognito (no content stored at all), explicitly warn yogis that:
  - "We cannot investigate or reproduce conversations after they end," and
  - "If you feel unsafe, use reporting tools in real time because there is no history."

---

## Sis's Recommendation for talent.yoga

For a community of yogis where safety and vibe matter, keep **short-lived server-side logs** and present the experience to yogis as "ephemeral" while still retaining enough for safety and legal defence. This balances GDPR's love of minimisation with the real-world need for accountability.

Adele as big sister fits nicely as the one who explains this at the start of a chat:

> "This space feels like being incognito, but for everyone's safety we keep a short-term record before it dissolves."

---

## Sources

- [helpsquad.com](https://helpsquad.com/gdpr-compliance/) — GDPR compliance
- [whoson.com](https://www.whoson.com/gdpr/what-is-gdpr/) — Personal data definition
- [mailspec.com](https://www.mailspec.com/post/gdpr-compliant-live-chat-navigating-compliance-with-ease) — Live chat GDPR
- [gdprlocal.com](https://gdprlocal.com/chatbot-gdpr-compliance/) — Chatbot compliance
- [chambers.com](https://chambers.com/articles/user-content-moderation-under-the-digital-services-act-10-key-takeaways-2) — DSA moderation
- [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/dsa-impact-platforms) — DSA impact
- [europeanlawinstitute.eu](https://www.europeanlawinstitute.eu/fileadmin/user_upload/p_eli/Publications/ELI_Model_Rules_on_Online_Platforms.pdf) — ELI Model Rules
- [forensicrisk.com](https://www.forensicrisk.com/news-and-insights/ephemeral-messaging-navigating-the-compliance-dilemma) — Ephemeral messaging compliance
- [financierworldwide.com](https://www.financierworldwide.com/ephemeral-messaging-pros-cons-and-obstructing-justice) — Ephemeral messaging risks
- [chatmetrics.com](https://www.chatmetrics.com/blog/live-chat-and-privacy-what-to-know/) — Chat privacy
- [gdpr-advisor.com](https://www.gdpr-advisor.com/gdpr-and-live-chat-support-managing-customer-conversations-securely/) — GDPR live chat
- [mco.mycomplianceoffice.com](https://mco.mycomplianceoffice.com/blog/the-compliance-challenges-of-ephemeral-messaging) — Compliance challenges

---

*...to be continued.*
