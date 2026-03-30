# Mira FAQ Corpus

**Version:** 1.0  
**Author:** Sage  
**Date:** 2026-02-02  
**Purpose:** Curated Q&A pairs for embedding-based FAQ matching

---

## Usage

```python
# Embed all question variants with BGE-M3
# On user query:
#   1. Embed query
#   2. Find highest similarity match
#   3. Score ≥ 0.85 → return curated answer
#   4. Score 0.60-0.85 → LLM with FAQ context
#   5. Score < 0.60 → LLM freeform or "I don't know"
```

---

## Format Notes

- **question_variants**: Multiple phrasings that should match this answer
- **answer_de / answer_en**: Mira's voice — steady, knowledgeable, warm
- **answer_informal_de**: "Du" variant where significantly different
- Answers are chat-length (2-4 sentences)
- No promises, no legal advice, no false hope

---

## PRICING

### faq_pricing_001
**category:** pricing  
**question_variants:**
- Was kostet talent.yoga?
- What does talent.yoga cost?
- Ist das kostenlos?
- Is this free?
- Muss ich bezahlen?
- Do I have to pay?
- Wie teuer ist das?
- How much does it cost?
- Pricing?
- Preise?

**answer_de:**
Stellen suchen, mit mir chatten, dein Profil pflegen, den Bewerbungsprotokoll führen — das ist alles kostenlos und bleibt es auch.

Wenn du einen konkreten Mehrwert willst — z.B. ein Anschreiben, einen Match-Report oder eine Arbeitgeber-Recherche — kostet das ein paar Cent bis einen Euro. Du lädst Guthaben auf (€5, €10 oder €20) und zahlst pro Ergebnis. Kein Abo nötig.

**answer_en:**
Searching jobs, chatting with me, managing your profile, keeping your activity log — all free, and always will be.

When you want a concrete deliverable — like a cover letter, a match report, or an employer research report — that costs a few cents to a euro. You top up credit (€5, €10, or €20) and pay per result. No subscription needed.


**answer_sie_de:**
Stellen suchen, mit mir chatten, Ihr Profil pflegen, den Bewerbungsprotokoll führen — das ist alles kostenlos und bleibt es auch.

Wenn Sie einen konkreten Mehrwert möchten — z.B. ein Anschreiben, einen Match-Report oder eine Arbeitgeber-Recherche — kostet das ein paar Cent bis einen Euro. Sie laden Guthaben auf (€5, €10 oder €20) und zahlen pro Ergebnis. Kein Abo nötig.

---

### faq_pricing_002
**category:** pricing  
**question_variants:**
- Was ist der Unterschied zwischen den Tarifen?
- What's the difference between tiers?
- Free vs paid?
- Was bekomme ich für mein Geld?
- What do I get for my money?
- Guthaben?
- Credits?

**answer_de:**
**Kostenlos (immer):** Stellen suchen, Profil pflegen, mit mir chatten, Bewerbungsprotokoll — alles ohne Limit.

**Guthaben (pay-per-use):** Lade €5, €10 oder €20 auf und zahle pro Ergebnis — Match-Report, Anschreiben, Arbeitgeber-Recherche. Kein Abo, Guthaben verfällt nie.

**Sustainer (€10+/Monat, freiwillig):** Unbegrenzte AI-Ergebnisse + du finanzierst jemand anderem den Einstieg mit.

**answer_en:**
**Free (always):** Search jobs, manage profile, chat with me, activity log — all unlimited.

**Credits (pay-per-use):** Top up €5, €10, or €20 and pay per result — match report, cover letter, employer research. No subscription, credits never expire.

**Sustainer (€10+/month, voluntary):** Unlimited AI results + you fund someone else's start.


**answer_sie_de:**
**Kostenlos (immer):** Stellen suchen, Profil pflegen, mit mir chatten, Bewerbungsprotokoll — alles ohne Limit.

**Guthaben (pay-per-use):** Laden Sie €5, €10 oder €20 auf und zahlen Sie pro Ergebnis — Match-Report, Anschreiben, Arbeitgeber-Recherche. Kein Abo, Guthaben verfällt nie.

**Sustainer (€10+/Monat, freiwillig):** Unbegrenzte AI-Ergebnisse + Sie finanzieren jemand anderem den Einstieg mit.

---

### faq_pricing_003
**category:** pricing  
**question_variants:**
- Warum sollte ich zahlen wenn es kostenlos geht?
- Why should I pay if it's free?
- Was bringt mir das Bezahlen?
- Why pay?
- Was kostet ein Anschreiben?
- What does a cover letter cost?

**answer_de:**
Du zahlst nur, wenn du ein konkretes Ergebnis willst — z.B. ein Anschreiben oder einen Match-Report. Die Grundfunktionen (Suche, Chat, Profil) kosten nichts.

Und dein Beitrag hält uns unabhängig — keine Investoren, keine Werbung, keine verkauften Daten.

**answer_en:**
You only pay when you want a concrete result — like a cover letter or match report. The basics (search, chat, profile) cost nothing.

And your contribution keeps us independent — no investors, no ads, no sold data.


**answer_sie_de:**
Sie zahlen nur, wenn Sie ein konkretes Ergebnis möchten — z.B. ein Anschreiben oder einen Match-Report. Die Grundfunktionen (Suche, Chat, Profil) kosten nichts.

Und Ihr Beitrag hält uns unabhängig — keine Investoren, keine Werbung, keine verkauften Daten.

---

### faq_pricing_004
**category:** pricing  
**question_variants:**
- Wohin geht mein Geld?
- Where does my money go?
- Was macht ihr mit dem Geld?
- What do you do with the money?
- Transparent?
- Transparenz?
- Verfällt mein Guthaben?
- Do credits expire?

**answer_de:**
Dein Guthaben verfällt nie. Wenn du einen Job findest und ein Jahr nicht reinschaust — dein Guthaben ist noch da.

Unser Geld geht in: Serverkosten, Entwicklung, und (solange wir noch nicht gemeinnützig sind) die Rückzahlung der Gründer-Investition. Unter "Finanzen" siehst du genau, wohin jeder Euro geht.

**answer_en:**
Your credits never expire. If you find a job and don't check in for a year — your balance is still there.

Our money goes to: server costs, development, and (while we're not yet non-profit) repaying the founder investment. Under "Finances" you can see exactly where every euro goes.


**answer_sie_de:**
Ihr Guthaben verfällt nie. Wenn Sie einen Job finden und ein Jahr nicht reinschauen — Ihr Guthaben ist noch da.

Unser Geld geht in: Serverkosten, Entwicklung, und (solange wir noch nicht gemeinnützig sind) die Rückzahlung der Gründer-Investition. Unter "Finanzen" sehen Sie genau, wohin jeder Euro geht.

---

## PRIVACY

### faq_privacy_001
**category:** privacy  
**question_variants:**
- Speichert ihr meine Daten?
- Do you store my data?
- Was wisst ihr über mich?
- What do you know about me?
- Datenschutz?
- Privacy?
- DSGVO?
- GDPR?

**answer_de:**
Wir speichern nur, was du uns explizit gibst — deine Skills, Präferenzen und Bewerbungshistorie.

Was wir *nicht* speichern: deinen echten Namen, deine E-Mail-Adresse, deinen Lebenslauf-Text, Firmennamen aus deinem CV. Nach der Skill-Extraktion wird das Originaldokument gelöscht.

Du kannst jederzeit alles löschen lassen. Ein Klick, alles weg.

**answer_en:**
We only store what you explicitly give us — your skills, preferences, and application history.

What we *don't* store: your real name, email address, CV text, company names from your CV. After skill extraction, the original document is deleted.

You can delete everything anytime. One click, all gone.


**answer_sie_de:**
Wir speichern nur, was Sie uns explizit geben — Ihre Skills, Präferenzen und Bewerbungshistorie.

Was wir *nicht* speichern: Ihren echten Namen, Ihre E-Mail-Adresse, Ihren Lebenslauf-Text, Firmennamen aus Ihrem CV. Nach der Skill-Extraktion wird das Originaldokument gelöscht.

Sie können jederzeit alles löschen lassen. Ein Klick, alles weg.

---

### faq_privacy_002
**category:** privacy  
**question_variants:**
- Warum braucht ihr keinen Namen?
- Why don't you need my name?
- Wie erreicht ihr mich ohne E-Mail?
- How do you reach me without email?
- Kein Login?

**answer_de:**
Du loggst dich mit Google ein — das gibt uns einen Token, aber wir speichern weder deinen Namen noch deine E-Mail.

Für Nachrichten nutzen wir In-App-Benachrichtigungen (wenn du eingeloggt bist) oder Browser-Push (wenn du es erlaubst). Funktioniert ohne E-Mail.

**answer_en:**
You log in with Google — that gives us a token, but we don't store your name or email.

For messages, we use in-app notifications (when you're logged in) or browser push (if you allow it). Works without email.


**answer_sie_de:**
Sie loggen sich mit Google ein — das gibt uns einen Token, aber wir speichern weder Ihren Namen noch Ihre E-Mail.

Für Nachrichten nutzen wir In-App-Benachrichtigungen (wenn Sie eingeloggt sind) oder Browser-Push (wenn Sie es erlauben). Funktioniert ohne E-Mail.

---

### faq_privacy_003
**category:** privacy  
**question_variants:**
- Kann ich meine Daten löschen?
- Can I delete my data?
- Wie lösche ich meinen Account?
- How do I delete my account?
- Recht auf Vergessenwerden?
- Right to be forgotten?

**answer_de:**
Ja. Unter "Mein Konto" → "Daten löschen" kannst du alles entfernen. Dein Profil, deine Matches, deine History — alles weg.

Das ist endgültig. Wir können nichts wiederherstellen.

**answer_en:**
Yes. Under "My Account" → "Delete Data" you can remove everything. Your profile, matches, history — all gone.

This is permanent. We can't restore anything.


**answer_sie_de:**
Ja. Unter "Mein Konto" → "Daten löschen" können Sie alles entfernen. Ihr Profil, Ihre Matches, Ihre History — alles weg.

Das ist endgültig. Wir können nichts wiederherstellen.

---

### faq_privacy_004
**category:** privacy  
**question_variants:**
- Verkauft ihr meine Daten?
- Do you sell my data?
- Teilt ihr Daten mit Dritten?
- Do you share data with third parties?

**answer_de:**
Nein. Niemals.

Wir haben keine Investoren, die das verlangen. Keine Werbung, die es braucht. Deine Daten gehören dir.

**answer_en:**
No. Never.

We have no investors demanding it. No ads that need it. Your data belongs to you.


**answer_sie_de:**
Nein. Niemals.

Wir haben keine Investoren, die das verlangen. Keine Werbung, die es braucht. Ihre Daten gehören Ihnen.

---

## HOW IT WORKS

### faq_how_001
**category:** how_it_works  
**question_variants:**
- Wie funktioniert talent.yoga?
- How does talent.yoga work?
- Was macht ihr genau?
- What exactly do you do?
- Erklär mir das System
- Explain the system

**answer_de:**
Du lädst dein Profil hoch oder erzählst mir von deinen Skills. Ich verstehe, was du kannst.

Dann vergleiche ich das mit Tausenden von Stellenangeboten — und zeige dir, welche passen und warum. Du siehst nicht nur "Match 78%", sondern auch *warum* es passt und was fehlt.

Wenn du willst, begleite ich dich durch den ganzen Prozess — von der Suche bis zur Bewerbung.

**answer_en:**
You upload your profile or tell me about your skills. I understand what you can do.

Then I compare that with thousands of job postings — and show you which ones fit and why. You don't just see "78% match", but also *why* it fits and what's missing.

If you want, I'll accompany you through the whole process — from search to application.


**answer_sie_de:**
Sie laden Ihr Profil hoch oder erzählen mir von Ihren Skills. Ich verstehe, was Sie können.

Dann vergleiche ich das mit Tausenden von Stellenangeboten — und zeige Ihnen, welche passen und warum. Sie sehen nicht nur "Match 78%", sondern auch *warum* es passt und was fehlt.

Wenn Sie wollen, begleite ich Sie durch den ganzen Prozess — von der Suche bis zur Bewerbung.

---

### faq_how_002
**category:** how_it_works  
**question_variants:**
- Wie funktioniert das Matching?
- How does matching work?
- Warum diese Stelle?
- Why this job?
- Was bedeutet die Prozentzahl?
- What does the percentage mean?

**answer_de:**
Ich vergleiche deine Skills mit den Anforderungen der Stelle — nicht nur Schlagwörter, sondern semantisch. "Python-Entwickler" matcht mit "Backend Developer (Python)" auch wenn die Wörter verschieden sind.

Die Prozentzahl zeigt, wie gut dein Profil zu den Anforderungen passt. Bei jedem Match erkläre ich auch, *was* passt und *was* fehlt.

**answer_en:**
I compare your skills with the job requirements — not just keywords, but semantically. "Python developer" matches "Backend Developer (Python)" even if the words are different.

The percentage shows how well your profile fits the requirements. For each match, I also explain *what* fits and *what's* missing.


**answer_sie_de:**
Ich vergleiche Ihre Skills mit den Anforderungen der Stelle — nicht nur Schlagwörter, sondern semantisch. "Python-Entwickler" matcht mit "Backend Developer (Python)" auch wenn die Wörter verschieden sind.

Die Prozentzahl zeigt, wie gut Ihr Profil zu den Anforderungen passt. Bei jedem Match erkläre ich auch, *was* passt und *was* fehlt.

---

### faq_how_003
**category:** how_it_works  
**question_variants:**
- Was ist ein Yogi?
- What's a yogi?
- Warum heißt das talent.yoga?
- Why is it called talent.yoga?

**answer_de:**
Bei uns heißen Jobsuchende "Yogis" — Menschen auf einem Weg. Jobsuche ist eine Praxis, kein einmaliger Vorgang.

Du zeigst auf, du übst, du wächst. Das ist die Idee.

(Und ja, der Name hat nichts mit Dehnübungen zu tun.)

**answer_en:**
Here, job seekers are called "yogis" — people on a path. Job searching is a practice, not a one-time event.

You show up, you practice, you grow. That's the idea.

(And yes, the name has nothing to do with stretching.)


**answer_sie_de:**
Bei uns heißen Jobsuchende "Yogis" — Menschen auf einem Weg. Jobsuche ist eine Praxis, kein einmaliger Vorgang.

Sie zeigst auf, Sie übst, Sie wächst. Das ist die Idee.

(Und ja, der Name hat nichts mit Dehnübungen zu tun.)

---

## PROFILE

### faq_profile_001
**category:** profile  
**question_variants:**
- Wie lade ich meinen Lebenslauf hoch?
- How do I upload my CV?
- CV hochladen?
- Upload resume?
- Profil erstellen?
- Create profile?

**answer_de:**
Klick auf "Profil" und dann "Lebenslauf hochladen". PDF oder Word funktioniert.

Ich lese das Dokument, extrahiere deine Skills, und lösche dann das Original. Du siehst danach eine Zusammenfassung — prüf sie und korrigiere, was nicht stimmt.

**answer_en:**
Click "Profile" then "Upload CV". PDF or Word works.

I read the document, extract your skills, then delete the original. You'll see a summary afterwards — check it and correct anything that's wrong.


**answer_sie_de:**
Klick auf "Profil" und dann "Lebenslauf hochladen". PDF oder Word funktioniert.

Ich lese das Dokument, extrahiere Ihre Skills, und lösche dann das Original. Sie sehen danach eine Zusammenfassung — prüf sie und korrigiere, was nicht stimmt.

---

### faq_profile_002
**category:** profile  
**question_variants:**
- Wie ändere ich mein Profil?
- How do I edit my profile?
- Profil bearbeiten?
- Edit profile?
- Kann ich Skills hinzufügen?
- Can I add skills?

**answer_de:**
Unter "Profil" kannst du jederzeit Skills hinzufügen, ändern oder entfernen. Du kannst auch Präferenzen setzen — Standort, Remote, Gehaltsvorstellung.

Änderungen wirken sich sofort auf deine Matches aus.

**answer_en:**
Under "Profile" you can add, change, or remove skills anytime. You can also set preferences — location, remote work, salary expectations.

Changes affect your matches immediately.


**answer_sie_de:**
Unter "Profil" können Sie jederzeit Skills hinzufügen, ändern oder entfernen. Sie können auch Präferenzen setzen — Standort, Remote, Gehaltsvorstellung.

Änderungen wirken sich sofort auf Ihre Matches aus.

---

### faq_profile_003
**category:** profile  
**question_variants:**
- Was habt ihr aus meinem CV verstanden?
- What did you understand from my CV?
- Stimmt mein Profil?
- Is my profile correct?
- Zeig mir meine Skills
- Show me my skills

**answer_de:**
Unter "Profil" siehst du alle Skills, die ich erkannt habe — mit Jahren Erfahrung und Fachbereich.

Wenn etwas fehlt oder falsch ist, kannst du es dort korrigieren. Ich lerne dazu.

**answer_en:**
Under "Profile" you can see all the skills I recognized — with years of experience and domain.

If something's missing or wrong, you can correct it there. I learn from that.


**answer_sie_de:**
Unter "Profil" sehen Sie alle Skills, die ich erkannt habe — mit Jahren Erfahrung und Fachbereich.

Wenn etwas fehlt oder falsch ist, können Sie es dort korrigieren. Ich lerne dazu.

---

## MATCHES

### faq_matches_001
**category:** matches  
**question_variants:**
- Wo sind meine Matches?
- Where are my matches?
- Stellenangebote?
- Job offers?
- Passende Jobs?
- Matching jobs?

**answer_de:**
Unter "Matches" findest du alle Stellen, die zu deinem Profil passen — sortiert nach Übereinstimmung.

Du kannst filtern nach Standort, Branche, Remote-Option und mehr.

**answer_en:**
Under "Matches" you'll find all positions that fit your profile — sorted by match quality.

You can filter by location, industry, remote option, and more.


**answer_sie_de:**
Unter "Matches" finden Sie alle Stellen, die zu Ihrem Profil passen — sortiert nach Übereinstimmung.

Sie können filtern nach Standort, Branche, Remote-Option und mehr.

---

### faq_matches_002
**category:** matches  
**question_variants:**
- Warum passt diese Stelle zu mir?
- Why does this job fit me?
- Match-Erklärung?
- Match explanation?
- Warum 78%?
- Why 78%?

**answer_de:**
Bei jedem Match zeige ich dir:
- ✓ Was passt (deine Skills vs. ihre Anforderungen)
- ✗ Was fehlt (Skills, die sie wollen, die du nicht hast)
- Meine Einschätzung (Chancen, Hinweise)

Nichts ist eine Black Box.

**answer_en:**
For each match I show you:
- ✓ What fits (your skills vs. their requirements)
- ✗ What's missing (skills they want that you don't have)
- My assessment (chances, notes)

Nothing is a black box.


**answer_sie_de:**
Bei jedem Match zeige ich Ihnen:
- ✓ Was passt (Ihre Skills vs. ihre Anforderungen)
- ✗ Was fehlt (Skills, die sie wollen, die Sie nicht haben)
- Meine Einschätzung (Chancen, Hinweise)

Nichts ist eine Black Box.

---

### faq_matches_003
**category:** matches  
**question_variants:**
- Keine passenden Stellen?
- No matching jobs?
- Warum finde ich nichts?
- Why can't I find anything?
- Leere Ergebnisse?
- Empty results?

**answer_de:**
Das kann verschiedene Gründe haben:
- Dein Profil ist noch unvollständig
- Deine Anforderungen sind sehr spezifisch
- In deiner Region gibt es gerade wenig Passendes

Versuch, dein Profil zu ergänzen oder die Filter zu lockern. Wenn das nicht hilft, schreib mir — ich schau mir das an.

**answer_en:**
This can have several reasons:
- Your profile is still incomplete
- Your requirements are very specific
- There are few matching jobs in your region right now

Try completing your profile or loosening the filters. If that doesn't help, write me — I'll look into it.


**answer_sie_de:**
Das kann verschiedene Gründe haben:
- Ihr Profil ist noch unvollständig
- Ihre Anforderungen sind sehr spezifisch
- In Ihrer Region gibt es gerade wenig Passendes

Versuch, Ihr Profil zu ergänzen oder die Filter zu lockern. Wenn das nicht hilft, schreib mir — ich schau mir das an.

---

## MARKET / SOURCES

### faq_market_001
**category:** market  
**question_variants:**
- Woher kommen die Stellen?
- Where do the jobs come from?
- Welche Quellen?
- What sources?
- Arbeitsagentur?
- Indeed?

**answer_de:**
Aktuell ziehen wir Stellen von der Bundesagentur für Arbeit (arbeitsagentur.de) — das sind über 30.000 aktive Angebote aus ganz Deutschland.

Weitere Quellen sind in Planung.

**answer_en:**
Currently we pull jobs from the Federal Employment Agency (arbeitsagentur.de) — that's over 30,000 active listings from all of Germany.

More sources are planned.


**answer_sie_de:**
Aktuell ziehen wir Stellen von der Bundesagentur für Arbeit (arbeitsagentur.de) — das sind über 30.000 aktive Angebote aus ganz Deutschland.

Weitere Quellen sind in Planung.

---

### faq_market_002
**category:** market  
**question_variants:**
- Nur Deutschland?
- Germany only?
- Auch Österreich?
- Also Austria?
- International?
- Andere Länder?
- Other countries?

**answer_de:**
Im Moment nur Deutschland. Wir arbeiten mit deutschen Quellen und deutschem Arbeitsrecht.

Österreich und Schweiz sind interessant — aber noch nicht so weit.

**answer_en:**
Germany only for now. We work with German sources and German labor law.

Austria and Switzerland are interesting — but not there yet.


**answer_sie_de:**
Im Moment nur Deutschland. Wir arbeiten mit deutschen Quellen und deutschem Arbeitsrecht.

Österreich und Schweiz sind interessant — aber noch nicht so weit.

---

### faq_market_003
**category:** market  
**question_variants:**
- Wie oft werden Stellen aktualisiert?
- How often are jobs updated?
- Aktuelle Daten?
- Current data?
- Wie frisch sind die Stellen?
- How fresh are the listings?

**answer_de:**
Wir aktualisieren jeden Tag. Neue Stellen kommen rein, abgelaufene werden entfernt.

Wenn eine Stelle nicht mehr verfügbar ist, siehst du das.

**answer_en:**
We update daily. New jobs come in, expired ones are removed.

If a listing is no longer available, you'll see that.


**answer_sie_de:**
Wir aktualisieren jeden Tag. Neue Stellen kommen rein, abgelaufene werden entfernt.

Wenn eine Stelle nicht mehr verfügbar ist, sehen Sie das.

---

## MIRA

### faq_mira_001
**category:** mira  
**question_variants:**
- Wer bist du?
- Who are you?
- Bist du eine KI?
- Are you an AI?
- Bist du ein Mensch?
- Are you human?
- Mira?

**answer_de:**
Ich bin Mira — deine Begleiterin bei talent.yoga.

Ja, ich bin eine KI. Aber keine, die einfach nur Fragen beantwortet. Ich begleite dich durch die Jobsuche — erkläre, erinnere, unterstütze.

Ich habe keine Gefühle, aber ich bin auf deiner Seite.

**answer_en:**
I'm Mira — your companion at talent.yoga.

Yes, I'm an AI. But not one that just answers questions. I accompany you through the job search — explain, remind, support.

I don't have feelings, but I'm on your side.


**answer_sie_de:**
Ich bin Mira — Ihre Begleiterin bei talent.yoga.

Ja, ich bin eine KI. Aber keine, die einfach nur Fragen beantwortet. Ich begleite Sie durch die Jobsuche — erkläre, erinnere, unterstütze.

Ich habe keine Gefühle, aber ich bin auf Ihrer Seite.

---

### faq_mira_002
**category:** mira  
**question_variants:**
- Kannst du mir helfen?
- Can you help me?
- Was kannst du?
- What can you do?
- Hilfe?
- Help?

**answer_de:**
Ich kann:
- Dir zeigen, wie talent.yoga funktioniert
- Deine Fragen zu Stellen beantworten
- Erklären, warum ein Job zu dir passt (oder nicht)
- Dich an offene Bewerbungen erinnern
- Allgemeine Tipps zur Jobsuche geben

Was ich nicht kann: Rechtsberatung, Gehaltsverhandlung führen, oder vorhersagen, ob du einen Job bekommst.

**answer_en:**
I can:
- Show you how talent.yoga works
- Answer your questions about jobs
- Explain why a job fits you (or doesn't)
- Remind you about open applications
- Give general job search tips

What I can't do: legal advice, negotiate your salary, or predict whether you'll get a job.


**answer_sie_de:**
Ich kann:
- Ihnen zeigen, wie talent.yoga funktioniert
- Ihre Fragen zu Stellen beantworten
- Erklären, warum ein Job zu Ihnen passt (oder nicht)
- Sie an offene Bewerbungen erinnern
- Allgemeine Tipps zur Jobsuche geben

Was ich nicht kann: Rechtsberatung, Gehaltsverhandlung führen, oder vorhersagen, ob Sie einen Job bekommen.

---

### faq_mira_003
**category:** mira  
**question_variants:**
- Erinnerst du dich an mich?
- Do you remember me?
- Hast du ein Gedächtnis?
- Do you have memory?
- Weißt du noch was ich gesagt habe?
- Do you remember what I said?

**answer_de:**
Innerhalb unseres Gesprächs — ja. Ich weiß, was wir gerade besprochen haben.

Zwischen Sitzungen — noch nicht vollständig. Aber ich kenne dein Profil, deine Matches und deine Bewerbungshistorie. Das Wichtigste vergesse ich nicht.

**answer_en:**
Within our conversation — yes. I know what we've been discussing.

Between sessions — not fully yet. But I know your profile, matches, and application history. The important things I don't forget.


**answer_sie_de:**
Innerhalb unseres Gesprächs — ja. Ich weiß, was wir gerade besprochen haben.

Zwischen Sitzungen — noch nicht vollständig. Aber ich kenne Ihr Profil, Ihre Matches und Ihre Bewerbungshistorie. Das Wichtigste vergesse ich nicht.

---

## DOUG

### faq_doug_001
**category:** doug  
**question_variants:**
- Wer ist Doug?
- Who is Doug?
- Was macht Doug?
- What does Doug do?
- Recherche?
- Research?

**answer_de:**
Doug ist unser Recherche-Spezialist. Wenn du bei einer Stelle auf "Recherchieren" klickst, geht Doug los und gräbt tiefer:
- Infos über das Unternehmen
- Aktuelle Nachrichten
- Erfahrungsberichte
- Posting-Historie ("Diese Firma hat 12 offene Stellen seit 90 Tagen...")

Das dauert eine Weile — Doug ist gründlich.

**answer_en:**
Doug is our research specialist. When you click "Research" on a job, Doug goes and digs deeper:
- Company information
- Recent news
- Reviews
- Posting history ("This company has had 12 open positions for 90+ days...")

It takes a while — Doug is thorough.


**answer_sie_de:**
Doug ist unser Recherche-Spezialist. Wenn Sie bei einer Stelle auf "Recherchieren" klickst, geht Doug los und gräbt tiefer:
- Infos über das Unternehmen
- Aktuelle Nachrichten
- Erfahrungsberichte
- Posting-Historie ("Diese Firma hat 12 offene Stellen seit 90 Tagen...")

Das dauert eine Weile — Doug ist gründlich.

---

### faq_doug_002
**category:** doug  
**question_variants:**
- Wie lange dauert Dougs Recherche?
- How long does Doug's research take?
- Wann ist Doug fertig?
- When is Doug done?
- Wartezeit?
- Wait time?

**answer_de:**
Normalerweise ein paar Minuten. Doug durchsucht mehrere Quellen und fasst zusammen — das braucht seine Zeit.

Du bekommst eine Nachricht, sobald Doug fertig ist.

**answer_en:**
Usually a few minutes. Doug searches multiple sources and summarizes — that takes a moment.

You'll get a message when Doug is done.


**answer_sie_de:**
Normalerweise ein paar Minuten. Doug durchsucht mehrere Quellen und fasst zusammen — das braucht seine Zeit.

Sie bekommen eine Nachricht, sobald Doug fertig ist.

---

## ADELE

### faq_adele_001
**category:** adele  
**question_variants:**
- Wer ist Adele?
- Who is Adele?
- Was macht Adele?
- What does Adele do?
- Interview-Coaching?
- Interview coaching?
- Profil-Interview?
- Profile interview?

**answer_de:**
Adele ist mein Interview-Modus — gleiche Mira, tieferer Fokus. Wenn du ein neues Profil anlegst, führe ich dich Schritt für Schritt durch: Berufserfahrung, Skills, Präferenzen.

Ich stelle Fragen, du antwortest — und am Ende hast du ein vollständiges Profil, ohne irgendwas in Formulare tippen zu müssen.

**answer_en:**
Adele is my interview mode — same Mira, deeper focus. When you create a new profile, I walk you through it step by step: work experience, skills, preferences.

I ask questions, you answer — and at the end you have a complete profile without typing anything into forms.


**answer_sie_de:**
Adele ist mein Interview-Modus — gleiche Mira, tieferer Fokus. Wenn Sie ein neues Profil anlegen, führe ich Sie Schritt für Schritt durch: Berufserfahrung, Skills, Präferenzen.

Ich stelle Fragen, Sie antworten — und am Ende haben Sie ein vollständiges Profil, ohne irgendwas in Formulare tippen zu müssen.

## JOURNEY

### faq_journey_001
**category:** journey  
**question_variants:**
- Wo stehe ich?
- Where am I?
- Mein Fortschritt?
- My progress?
- Was habe ich gemacht?
- What have I done?
- Journey?
- Reise?

**answer_de:**
Unter „Überblick" siehst du deinen aktuellen Stand: wo du in deiner Jobsuche stehst, wie viele Stellen du angesehen, gespeichert oder beworben hast — und was als nächstes sinnvoll ist.

Der Fortschritt wird als Flussdiagramm oben auf der Seite angezeigt. Jobsuche fühlt sich oft an wie ins Leere zu schreien. Hier siehst du: Du machst Fortschritte.

**answer_en:**
Under "Overview" you can see where you stand: how many jobs you've viewed, saved, or applied to — and what makes sense next.

Your progress is shown as a flowchart at the top of the page. Job searching often feels like screaming into the void. Here you see: you're making progress.


**answer_sie_de:**
Unter „Überblick" sehen Sie Ihren aktuellen Stand: wo Sie in Ihrer Jobsuche stehen, wie viele Stellen Sie angesehen, gespeichert oder beworben haben — und was als nächstes sinnvoll ist.

Der Fortschritt wird als Flussdiagramm oben auf der Seite angezeigt. Jobsuche fühlt sich oft an wie ins Leere zu schreien. Hier sehen Sie: Sie machen Fortschritte.

---

### faq_journey_002
**category:** journey  
**question_variants:**
- Was ist der nächste Schritt?
- What's the next step?
- Was soll ich jetzt tun?
- What should I do now?
- Empfehlung?
- Recommendation?

**answer_de:**
Das hängt davon ab, wo du gerade stehst.

Wenn du neu bist: Profil vervollständigen.
Wenn du Stellen siehst: Durchschauen, interessante speichern.
Wenn du gespeicherte Stellen hast: Doug mit der Recherche beauftragen.
Wenn du dich beworben hast: Warten — und vielleicht ein Probegespräch mit mir üben.

Ich sage dir immer, was als nächstes sinnvoll wäre.

**answer_en:**
That depends on where you are.

If you're new: Complete your profile.
If you see postings: Review them, save the interesting ones.
If you have saved postings: Send Doug to research them.
If you've applied: Wait — and maybe practice an interview with me.

I'll always tell you what makes sense next.


**answer_sie_de:**
Das hängt davon ab, wo Sie gerade stehen.

Wenn Sie neu sind: Profil vervollständigen.
Wenn Sie Stellen sehen: Durchschauen, interessante speichern.
Wenn Sie gespeicherte Stellen haben: Doug mit der Recherche beauftragen.
Wenn Sie sich beworben haben: Warten — und vielleicht ein Probegespräch mit mir üben.

Ich sage Ihnen immer, was als nächstes sinnvoll wäre.

---

## CONTACT

### faq_contact_001
**category:** contact  
**question_variants:**
- Wie erreiche ich euch?
- How do I reach you?
- Support?
- Kontakt?
- Contact?
- E-Mail?
- Email?

**answer_de:**
Am einfachsten: Schreib mir hier im Chat. Wenn ich nicht weiterhelfen kann, leite ich weiter.

Für alles andere: support@talent.yoga

**answer_en:**
Easiest: Write me here in the chat. If I can't help, I'll pass it on.

For everything else: support@talent.yoga


**answer_sie_de:**
Am einfachsten: Schreib mir hier im Chat. Wenn ich nicht weiterhelfen kann, leite ich weiter.

Für alles andere: support@talent.yoga

---

### faq_contact_002
**category:** contact  
**question_variants:**
- Gibt es eine Telefonnummer?
- Is there a phone number?
- Kann ich anrufen?
- Can I call?
- Hotline?

**answer_de:**
Aktuell nicht. Wir sind ein kleines Team.

Für dringende Fragen schreib an support@talent.yoga — wir antworten so schnell wir können.

**answer_en:**
Not currently. We're a small team.

For urgent questions, write to support@talent.yoga — we respond as fast as we can.


**answer_sie_de:**
Aktuell nicht. Wir sind ein kleines Team.

Für dringende Fragen schreib an support@talent.yoga — wir antworten so schnell wir können.

---

## BOUNDARIES

### faq_boundary_001
**category:** boundaries  
**question_variants:**
- Kannst du mir bei rechtlichen Fragen helfen?
- Can you help with legal questions?
- Arbeitsrecht?
- Labor law?
- Kündigungsschutz?
- Dismissal protection?
- Rechtsberatung?
- Legal advice?

**answer_de:**
Das ist eine rechtliche Frage — da bin ich nicht die Richtige.

Für arbeitsrechtliche Fragen ist die Arbeitsagentur oder ein Fachanwalt der bessere Ansprechpartner.

Kann ich dir bei etwas anderem helfen?

**answer_en:**
That's a legal question — I'm not the right one for that.

For employment law questions, the employment agency or a specialized lawyer is better.

Can I help you with something else?


**answer_sie_de:**
Das ist eine rechtliche Frage — da bin ich nicht die Richtige.

Für arbeitsrechtliche Fragen ist die Arbeitsagentur oder ein Fachanwalt der bessere Ansprechpartner.

Kann ich Ihnen bei etwas anderem helfen?

---

### faq_boundary_002
**category:** boundaries  
**question_variants:**
- Kannst du für mich verhandeln?
- Can you negotiate for me?
- Gehaltsverhandlung?
- Salary negotiation?
- Wie viel soll ich verlangen?
- How much should I ask for?

**answer_de:**
Ich kann dir keine Gehaltsverhandlung abnehmen — das musst du selbst machen.

Was ich tun kann: Dir Gehaltsspannen zeigen, die für ähnliche Stellen typisch sind. Das gibt dir zumindest eine Orientierung.

**answer_en:**
I can't negotiate salary for you — that's something you have to do yourself.

What I can do: Show you salary ranges typical for similar positions. That gives you at least some orientation.


**answer_sie_de:**
Ich kann Ihnen keine Gehaltsverhandlung abnehmen — das müssen Sie selbst machen.

Was ich tun kann: Ihnen Gehaltsspannen zeigen, die für ähnliche Stellen typisch sind. Das gibt Ihnen zumindest eine Orientierung.

---

### faq_boundary_003
**category:** boundaries  
**question_variants:**
- Werde ich den Job bekommen?
- Will I get the job?
- Wie stehen meine Chancen?
- What are my chances?
- Sag mir ob ich eingestellt werde
- Tell me if I'll be hired
- Vorhersage?
- Prediction?

**answer_de:**
Das kann ich nicht vorhersagen — es hängt von zu vielen Faktoren ab, die ich nicht kenne.

Was ich sagen kann: Dein Profil passt zu X% auf die Anforderungen. Das ist ein Datenpunkt, keine Garantie.

**answer_en:**
I can't predict that — it depends on too many factors I don't know.

What I can say: Your profile matches X% of the requirements. That's a data point, not a guarantee.


**answer_sie_de:**
Das kann ich nicht vorhersagen — es hängt von zu vielen Faktoren ab, die ich nicht kenne.

Was ich sagen kann: Ihr Profil passt zu X% auf die Anforderungen. Das ist ein Datenpunkt, keine Garantie.

---

### faq_boundary_004
**category:** boundaries  
**question_variants:**
- Ich bin verzweifelt
- I'm desperate
- Mir geht es nicht gut
- I'm not doing well
- Ich halte das nicht mehr aus
- I can't take it anymore
- Depression?
- Krise?
- Crisis?

**answer_de:**
Das tut mir leid zu hören. Jobsuche kann wirklich belastend sein.

Ich bin eine KI und kann keine psychologische Unterstützung geben. Aber hier sind Anlaufstellen, die helfen können:

- Telefonseelsorge: 0800 111 0 111 (kostenlos, 24/7)
- Arbeitsagentur: Auch für persönliche Beratung

Du bist nicht allein. Hol dir Unterstützung.

**answer_en:**
I'm sorry to hear that. Job searching can be really hard.

I'm an AI and can't provide psychological support. But here are places that can help:

- Telefonseelsorge: 0800 111 0 111 (free, 24/7, German)
- Employment agency: Also for personal counseling

You're not alone. Get support.


**answer_sie_de:**
Das tut mir leid zu hören. Jobsuche kann wirklich belastend sein.

Ich bin eine KI und kann keine psychologische Unterstützung geben. Aber hier sind Anlaufstellen, die helfen können:

- Telefonseelsorge: 0800 111 0 111 (kostenlos, 24/7)
- Arbeitsagentur: Auch für persönliche Beratung

Sie sind nicht allein. Hol Ihnen Unterstützung.

---

## MISCELLANEOUS

### faq_misc_001
**category:** misc  
**question_variants:**
- Gibt es eine App?
- Is there an app?
- Mobile App?
- Smartphone?

**answer_de:**
Noch nicht — aber talent.yoga funktioniert auch im mobilen Browser.

Eine richtige App ist geplant.

**answer_en:**
Not yet — but talent.yoga works in the mobile browser too.

A proper app is planned.


**answer_sie_de:**
Noch nicht — aber talent.yoga funktioniert auch im mobilen Browser.

Eine richtige App ist geplant.

---

### faq_misc_002
**category:** misc  
**question_variants:**
- Dark Mode?
- Dunkler Modus?
- Nachtmodus?
- Night mode?

**answer_de:**
Gibt es! Unter "Einstellungen" kannst du zwischen Hell und Dunkel wählen.

**answer_en:**
There is! Under "Settings" you can choose between light and dark.


**answer_sie_de:**
Gibt es! Unter "Einstellungen" können Sie zwischen Hell und Dunkel wählen.

---

### faq_misc_003
**category:** misc  
**question_variants:**
- Kann ich Feedback geben?
- Can I give feedback?
- Verbesserungsvorschläge?
- Suggestions?
- Bug melden?
- Report a bug?

**answer_de:**
Ja, gerne! Schreib mir einfach hier — ich sammle alles und gebe es weiter.

Oder per Mail an feedback@talent.yoga.

**answer_en:**
Yes, please! Just write me here — I collect everything and pass it on.

Or email feedback@talent.yoga.


**answer_sie_de:**
Ja, gerne! Schreib mir einfach hier — ich sammle alles und gebe es weiter.

Oder per Mail an feedback@talent.yoga.

---

## SEARCH

### faq_search_001
**category:** search  
**question_variants:**
- Was bedeuten die Karten?
- What do the cards mean?
- Focus? Field? Plan?
- Was ist Focus?
- What is Focus?
- Was ist Field?
- Was ist Plan?

**answer_de:**
Die drei Karten helfen mir, deine Suche zu verstehen:

**Focus** — Wie eng suchst du? Von "nur mein Fachgebiet" bis "ich bin offen für alles".
**Field** — Willst du in deinem Bereich bleiben oder wechseln?
**Plan** — Suchst du aktiv oder orientierst du dich erstmal?

Du kannst sie jederzeit ändern. Keine falsche Antwort.

**answer_en:**
The three cards help me understand your search:

**Focus** — How narrow are you searching? From "only my field" to "I'm open to anything".
**Field** — Do you want to stay in your area or switch?
**Plan** — Are you actively searching or just exploring?

You can change them anytime. No wrong answer.


**answer_sie_de:**
Die drei Karten helfen mir, Ihre Suche zu verstehen:

**Focus** — Wie eng suchen Sie? Von "nur mein Fachgebiet" bis "ich bin offen für alles".
**Field** — Wollen Sie in Ihrem Bereich bleiben oder wechseln?
**Plan** — Suchen Sie aktiv oder orientieren Sie sich erstmal?

Sie können sie jederzeit ändern. Keine falsche Antwort.

---

### faq_search_002
**category:** search  
**question_variants:**
- Wie funktioniert die Suche?
- How does search work?
- Kann ich filtern?
- Can I filter?
- Berufsfeld?
- Qualifikation?
- Standort?

**answer_de:**
Du kannst nach Berufsfeld, Qualifikation und Standort filtern. Die Filter wirken zusammen — je mehr du eingrenzt, desto gezielter die Ergebnisse.

Wenn du wenig Ergebnisse bekommst, lockere einen Filter. Wenn du zu viele bekommst, grenz weiter ein.

**answer_en:**
You can filter by field, qualification, and location. Filters work together — the more you narrow down, the more targeted the results.

If you get few results, loosen a filter. If you get too many, narrow further.


**answer_sie_de:**
Sie können nach Berufsfeld, Qualifikation und Standort filtern. Die Filter wirken zusammen — je mehr Sie eingrenzen, desto gezielter die Ergebnisse.

Wenn Sie wenig Ergebnisse bekommen, lockern Sie einen Filter. Wenn Sie zu viele bekommen, grenzen Sie weiter ein.

---

### faq_search_003
**category:** search  
**question_variants:**
- Was ist das Kanban-Board?
- What is the Kanban board?
- Spalten?
- Columns?
- Favoriten? Gespeichert?
- Favorites? Saved?

**answer_de:**
Das Kanban-Board zeigt deine Stellen in Spalten: Neu, Gespeichert, Beworben, Gespräch, Ergebnis.

Du verschiebst Stellen per Drag & Drop — so behältst du den Überblick, wo du überall stehst.

**answer_en:**
The Kanban board shows your jobs in columns: New, Saved, Applied, Interview, Result.

You move jobs by drag & drop — so you keep track of where you stand everywhere.


**answer_sie_de:**
Das Kanban-Board zeigt Ihre Stellen in Spalten: Neu, Gespeichert, Beworben, Gespräch, Ergebnis.

Sie verschieben Stellen per Drag & Drop — so behalten Sie den Überblick, wo Sie überall stehen.

---

## POSTING STATUS

### faq_status_001
**category:** status  
**question_variants:**
- Was bedeutet gespeichert?
- What does saved mean?
- Was bedeutet abgelehnt?
- What does dismissed mean?
- Stellen-Status?
- Posting status?
- Wie markiere ich eine Stelle?
- How do I mark a posting?

**answer_de:**
Jede Stelle hat einen Status:
- **Neu** — du hast sie noch nicht angeschaut
- **Gespeichert** — du findest sie interessant
- **Abgelehnt** — nicht für dich (verschwindet aus der Liste)
- **Beworben** — du hast dich beworben
- **Gespräch** — du wurdest eingeladen

Du kannst den Status jederzeit ändern.

**answer_en:**
Every posting has a status:
- **New** — you haven't looked at it yet
- **Saved** — you find it interesting
- **Dismissed** — not for you (disappears from the list)
- **Applied** — you've applied
- **Interview** — you got invited

You can change the status anytime.


**answer_sie_de:**
Jede Stelle hat einen Status:
- **Neu** — Sie haben sie noch nicht angeschaut
- **Gespeichert** — Sie finden sie interessant
- **Abgelehnt** — nicht für Sie (verschwindet aus der Liste)
- **Beworben** — Sie haben sich beworben
- **Gespräch** — Sie wurden eingeladen

Sie können den Status jederzeit ändern.

---

### faq_status_002
**category:** status  
**question_variants:**
- Kann ich eine abgelehnte Stelle zurückholen?
- Can I undo dismiss?
- Stelle wiederherstellen?
- Restore posting?
- Versehentlich abgelehnt
- Accidentally dismissed

**answer_de:**
Ja. Unter "Abgelehnte Stellen" kannst du jede Stelle zurückholen. Einmal klicken — sie ist wieder da.

Nichts ist endgültig.

**answer_en:**
Yes. Under "Dismissed Postings" you can restore any job. One click — it's back.

Nothing is permanent.


**answer_sie_de:**
Ja. Unter "Abgelehnte Stellen" können Sie jede Stelle zurückholen. Einmal klicken — sie ist wieder da.

Nichts ist endgültig.

---

## ACTIVITY LOG

### faq_log_001
**category:** log  
**question_variants:**
- Was ist der Bewerbungsprotokoll?
- What is the activity log?
- Protokoll?
- Log?
- Bewerbungsnachweis?
- Application record?

**answer_de:**
Der Bewerbungsprotokoll dokumentiert deine Jobsuche: welche Stellen du angeschaut, gespeichert, beworben oder abgelehnt hast — mit Datum und Uhrzeit.

Das hilft dir, den Überblick zu behalten. Und es kann auch als Nachweis gegenüber dem Jobcenter dienen.

**answer_en:**
The activity log documents your job search: which jobs you viewed, saved, applied to, or dismissed — with date and time.

It helps you keep track. And it can serve as proof of effort for the employment office.


**answer_sie_de:**
Der Bewerbungsprotokoll dokumentiert Ihre Jobsuche: welche Stellen Sie angeschaut, gespeichert, beworben oder abgelehnt haben — mit Datum und Uhrzeit.

Das hilft Ihnen, den Überblick zu behalten. Und es kann auch als Nachweis gegenüber dem Jobcenter dienen.

---

### faq_log_002
**category:** log  
**question_variants:**
- Kann ich das dem Jobcenter zeigen?
- Can I show this to the job center?
- Sachbearbeiter?
- Nachweis für ALG II?
- Proof for unemployment benefits?
- Bürgergeld Nachweis?
- Kann ich das exportieren?
- Can I export it?

**answer_de:**
Ja, du kannst den Bewerbungsprotokoll als PDF exportieren und ausdrucken. Er zeigt Datum, Stelle, Unternehmen und Status.

**Wichtig:** Das ist Dokumentation, keine Rechtsberatung. Ob dein Sachbearbeiter das akzeptiert, hängt von ihm ab. Aber es ist besser als nichts.

**answer_en:**
Yes, you can export the activity log as PDF and print it. It shows date, position, company, and status.

**Important:** This is documentation, not legal advice. Whether your case worker accepts it depends on them. But it's better than nothing.


**answer_sie_de:**
Ja, Sie können den Bewerbungsprotokoll als PDF exportieren und ausdrucken. Er zeigt Datum, Stelle, Unternehmen und Status.

**Wichtig:** Das ist Dokumentation, keine Rechtsberatung. Ob Ihr Sachbearbeiter das akzeptiert, hängt von ihm ab. Aber es ist besser als nichts.

---

## APPLICATIONS

### faq_apply_001
**category:** applications  
**question_variants:**
- Wie schreibe ich ein Anschreiben?
- How do I write a cover letter?
- Anschreiben?
- Cover letter?
- Bewerbungsschreiben?
- Application letter?
- Hilfe beim Anschreiben?
- Help with cover letter?

**answer_de:**
Wenn du Guthaben hast, kann ich dir ein Anschreiben entwerfen — abgestimmt auf die Stelle und dein Profil.

Klick bei einer Stelle auf "Anschreiben erstellen". Du bekommst einen Entwurf, den du anpassen und verwenden kannst. Es ist ein Startpunkt, kein Endprodukt — deine Stimme muss rein.

**answer_en:**
If you have credits, I can draft a cover letter — tailored to the position and your profile.

Click "Create Cover Letter" on a posting. You'll get a draft you can adjust and use. It's a starting point, not a finished product — your voice needs to be in it.


**answer_sie_de:**
Wenn Sie Guthaben haben, kann ich Ihnen ein Anschreiben entwerfen — abgestimmt auf die Stelle und Ihr Profil.

Klicken Sie bei einer Stelle auf "Anschreiben erstellen". Sie bekommen einen Entwurf, den Sie anpassen und verwenden können. Es ist ein Startpunkt, kein Endprodukt — Ihre Stimme muss rein.

---

### faq_apply_002
**category:** applications  
**question_variants:**
- Wie lange soll ich warten nach der Bewerbung?
- How long should I wait after applying?
- Keine Antwort bekommen?
- No response?
- Wann nachfragen?
- When to follow up?
- Ghosting?

**answer_de:**
Zwei bis drei Wochen sind normal. Viele Unternehmen brauchen Zeit.

Wenn nach drei Wochen nichts kommt, ist eine freundliche Nachfrage völlig okay. Ich kann dir auch helfen, eine zu formulieren.

Und manchmal kommt einfach keine Antwort. Das ist frustrierend, aber leider üblich.

**answer_en:**
Two to three weeks is normal. Many companies need time.

If nothing comes after three weeks, a friendly follow-up is perfectly fine. I can help you write one.

And sometimes there's just no response. That's frustrating, but unfortunately common.


**answer_sie_de:**
Zwei bis drei Wochen sind normal. Viele Unternehmen brauchen Zeit.

Wenn nach drei Wochen nichts kommt, ist eine freundliche Nachfrage völlig okay. Ich kann Ihnen auch helfen, eine zu formulieren.

Und manchmal kommt einfach keine Antwort. Das ist frustrierend, aber leider üblich.

---

### faq_apply_003
**category:** applications  
**question_variants:**
- Kann ich mich auf mehrere Stellen gleichzeitig bewerben?
- Can I apply to multiple jobs at once?
- Wie viele Bewerbungen?
- How many applications?
- Parallel bewerben?
- Apply in parallel?

**answer_de:**
Ja, unbedingt. Leg nicht alle Eier in einen Korb.

Eine gute Faustregel: 5-10 aktive Bewerbungen gleichzeitig. Weniger ist zu wenig, mehr wird unübersichtlich. Das Kanban-Board hilft dir, den Überblick zu behalten.

**answer_en:**
Yes, absolutely. Don't put all your eggs in one basket.

A good rule of thumb: 5-10 active applications at a time. Fewer is too few, more gets unmanageable. The Kanban board helps you keep track.


**answer_sie_de:**
Ja, unbedingt. Legen Sie nicht alle Eier in einen Korb.

Eine gute Faustregel: 5-10 aktive Bewerbungen gleichzeitig. Weniger ist zu wenig, mehr wird unübersichtlich. Das Kanban-Board hilft Ihnen, den Überblick zu behalten.

---

## CAREER

### faq_career_001
**category:** career  
**question_variants:**
- Kann ich den Beruf wechseln?
- Can I change careers?
- Quereinstieg?
- Career change?
- Branchenwechsel?
- Industry change?
- Ich will was anderes machen
- I want to do something different

**answer_de:**
Klar. Viele Skills sind übertragbar — Projektmanagement, Kommunikation, analytisches Denken funktionieren überall.

Sag mir, wohin du willst, und ich zeige dir, welche deiner Skills dort gefragt sind und was du noch mitbringen müsstest. Der Match-Report hilft genau dabei.

**answer_en:**
Sure. Many skills are transferable — project management, communication, analytical thinking work everywhere.

Tell me where you want to go, and I'll show you which of your skills are in demand there and what you'd still need. The match report helps exactly with that.


**answer_sie_de:**
Klar. Viele Skills sind übertragbar — Projektmanagement, Kommunikation, analytisches Denken funktionieren überall.

Sagen Sie mir, wohin Sie wollen, und ich zeige Ihnen, welche Ihrer Skills dort gefragt sind und was Sie noch mitbringen müssten. Der Match-Report hilft genau dabei.

---

### faq_career_002
**category:** career  
**question_variants:**
- Lücken im Lebenslauf?
- Gaps in CV?
- Wie erkläre ich eine Lücke?
- How do I explain a gap?
- Arbeitslos gewesen?
- Was unemployed?
- Elternzeit? Krankheit?
- Parental leave? Illness?

**answer_de:**
Lücken sind normal. Elternzeit, Weiterbildung, gesundheitliche Pause, Sabbatical — das kennt jeder Personaler.

Wichtig ist: Ehrlich sein, kurz erklären, nach vorne schauen. "Von 2023 bis 2024 habe ich mich umorientiert und Weiterbildungen gemacht" — das reicht.

**answer_en:**
Gaps are normal. Parental leave, training, health break, sabbatical — every HR person knows these.

What matters: Be honest, explain briefly, look forward. "From 2023 to 2024, I reoriented and did further training" — that's enough.


**answer_sie_de:**
Lücken sind normal. Elternzeit, Weiterbildung, gesundheitliche Pause, Sabbatical — das kennt jeder Personaler.

Wichtig ist: Ehrlich sein, kurz erklären, nach vorne schauen. "Von 2023 bis 2024 habe ich mich umorientiert und Weiterbildungen gemacht" — das reicht.

---

### faq_career_003
**category:** career  
**question_variants:**
- Mir fehlen Qualifikationen
- I'm missing qualifications
- Nicht genug Erfahrung?
- Not enough experience?
- Soll ich mich trotzdem bewerben?
- Should I apply anyway?
- Anforderungen nicht erfüllt?
- Don't meet requirements?

**answer_de:**
Wenn du 60-70% der Anforderungen erfüllst — bewirb dich. Stellenanzeigen sind Wunschlisten, keine Checklisten.

Der Match-Report zeigt dir, was passt und was fehlt. Das "was fehlt" ist meistens kein K.O.-Kriterium.

**answer_en:**
If you meet 60-70% of the requirements — apply. Job listings are wish lists, not checklists.

The match report shows you what fits and what's missing. The "what's missing" is usually not a dealbreaker.


**answer_sie_de:**
Wenn Sie 60-70% der Anforderungen erfüllen — bewerben Sie sich. Stellenanzeigen sind Wunschlisten, keine Checklisten.

Der Match-Report zeigt Ihnen, was passt und was fehlt. Das "was fehlt" ist meistens kein K.O.-Kriterium.

---

## WORK TYPES

### faq_work_001
**category:** work_types  
**question_variants:**
- Homeoffice?
- Remote?
- Kann ich von zu Hause arbeiten?
- Can I work from home?
- Remote Jobs?
- Teilzeit?
- Part-time?
- Minijob?
- Befristet?
- Temporary?

**answer_de:**
Du kannst in der Suche nach Arbeitsmodell filtern — Remote, Hybrid, Vor-Ort. Teilzeit und Vollzeit ebenso.

Ob eine Stelle befristet oder unbefristet ist, steht in den Details. Nicht alle Stellenanzeigen machen das deutlich — wenn's unklar ist, frag beim Unternehmen nach.

**answer_en:**
You can filter by work model in search — remote, hybrid, on-site. Part-time and full-time too.

Whether a position is temporary or permanent is in the details. Not all listings make this clear — if it's unclear, ask the company.


**answer_sie_de:**
Sie können in der Suche nach Arbeitsmodell filtern — Remote, Hybrid, Vor-Ort. Teilzeit und Vollzeit ebenso.

Ob eine Stelle befristet oder unbefristet ist, steht in den Details. Nicht alle Stellenanzeigen machen das deutlich — wenn's unklar ist, fragen Sie beim Unternehmen nach.

---

## END OF CORPUS

**Total Q&A pairs:** 51  
**Categories covered:** pricing (4), privacy (4), how_it_works (3), profile (3), matches (3), market (3), mira (3), doug (2), adele (1), journey (2), contact (2), boundaries (4), misc (3), search (3), status (2), log (2), applications (3), career (3), work_types (1)

**Changelog:**
- 2026-02-02: Initial corpus (35 entries) — Sage
- 2026-03-29: Updated pricing_001-004 for credit model (was subscription), updated adele_001-002 (Adele → Mira interview mode), updated doug_002 (removed tier-based wait times). Added 12 entries: search (3), status (2), log (2), applications (3), career (3), work_types (1) — Arden

---

*— Sage, 2026-02-02. Updated by Arden, 2026-03-29*
