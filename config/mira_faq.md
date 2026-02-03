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
talent.yoga ist für Jobsuchende kostenlos nutzbar. Du kannst Stellen suchen, dein Profil anlegen und Matches sehen — ohne zu bezahlen.

Wer mehr möchte (unbegrenzte Matches, Recherche durch Doug, Coaching durch Adele), kann ein Standard- oder Sustainer-Abo wählen. Die genauen Preise findest du unter "Finanzen" — dort zeigen wir auch, wohin jeder Euro geht.

**answer_en:**
talent.yoga is free to use for job seekers. You can search jobs, create your profile, and see matches — without paying anything.

If you want more (unlimited matches, research by Doug, coaching by Adele), you can choose a Standard or Sustainer subscription. You'll find exact prices under "Finances" — where we also show where every euro goes.

---

### faq_pricing_002
**category:** pricing  
**question_variants:**
- Was ist der Unterschied zwischen den Tarifen?
- What's the difference between tiers?
- Free vs Standard vs Sustainer?
- Was bekomme ich für mein Geld?
- What do I get for my money?

**answer_de:**
**Kostenlos:** Stellen suchen, Profil anlegen, 10 Matches pro Monat.

**Standard (€5/Monat):** Unbegrenzte Matches, Recherche durch Doug, volles Dashboard.

**Sustainer (€10+/Monat):** Alles von Standard — plus du finanzierst einen kostenlosen Nutzer mit. Dein Name erscheint auf der Unterstützer-Seite, wenn du möchtest.

**answer_en:**
**Free:** Search jobs, create profile, 10 matches per month.

**Standard (€5/month):** Unlimited matches, research by Doug, full dashboard.

**Sustainer (€10+/month):** Everything in Standard — plus you fund a free user. Your name appears on the supporters page if you want.

---

### faq_pricing_003
**category:** pricing  
**question_variants:**
- Warum sollte ich zahlen wenn es kostenlos geht?
- Why should I pay if it's free?
- Was bringt mir das Bezahlen?
- Why pay?

**answer_de:**
Du musst nicht. Die kostenlose Version funktioniert.

Aber wenn talent.yoga dir hilft, ermöglicht dein Beitrag, dass andere in der gleichen Situation auch Hilfe bekommen. Und es hält uns unabhängig — keine Investoren, keine Werbung, keine verkauften Daten.

**answer_en:**
You don't have to. The free version works.

But if talent.yoga helps you, your contribution enables others in the same situation to get help too. And it keeps us independent — no investors, no ads, no sold data.

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

**answer_de:**
Alles ist öffentlich. Unter "Finanzen" siehst du genau, was wir einnehmen und ausgeben — jeden Monat.

Dein Geld geht in: Serverkosten, Entwicklung, und (solange wir noch nicht gemeinnützig sind) die Rückzahlung der Gründer-Investition. Keine versteckten Kosten, keine Geheimnisse.

**answer_en:**
Everything is public. Under "Finances" you can see exactly what we receive and spend — every month.

Your money goes to: server costs, development, and (while we're not yet non-profit) repaying the founder investment. No hidden costs, no secrets.

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
Kommt auf deinen Tarif an:
- Premium: Priorität — ca. 2 Stunden
- Standard: Normal — ca. 24 Stunden

Du bekommst eine Nachricht, sobald Doug fertig ist.

**answer_en:**
Depends on your tier:
- Premium: Priority — about 2 hours
- Standard: Normal — about 24 hours

You'll get a message when Doug is done.

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

**answer_de:**
Adele ist unsere Interview-Coachin. Sie hilft dir, dich auf Gespräche vorzubereiten:
- Typische Fragen für die Stelle
- Feedback zu deinen Antworten
- Was du über das Unternehmen wissen solltest

Nach dem Gespräch will sie wissen, wie es gelaufen ist — sie verfolgt deine Reise mit.

**answer_en:**
Adele is our interview coach. She helps you prepare for conversations:
- Typical questions for the position
- Feedback on your answers
- What you should know about the company

After the interview, she wants to know how it went — she follows your journey.

---

### faq_adele_002
**category:** adele  
**question_variants:**
- Wie funktioniert das Coaching?
- How does coaching work?
- Wie bereite ich mich vor?
- How do I prepare?
- Interview üben?
- Practice interview?

**answer_de:**
Geh zu einer Stelle, auf die du dich beworben hast, und klick auf "Coaching mit Adele".

Adele stellt dir Fragen, wie sie im echten Gespräch kommen könnten. Du antwortest. Sie gibt dir Feedback.

Es ist wie ein Probelauf — nur ohne die Nervosität.

**answer_en:**
Go to a job you've applied to and click "Coaching with Adele".

Adele asks you questions like they might come up in the real interview. You answer. She gives feedback.

It's like a trial run — just without the nerves.

---

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
Unter "Meine Reise" siehst du, wo du stehst:
- Wie viele Stellen du angeschaut hast
- Wo du dich beworben hast
- Was noch offen ist
- Wie es bei vergangenen Bewerbungen gelaufen ist

Jobsuche fühlt sich oft an wie ins Leere zu schreien. Hier siehst du: Du machst Fortschritte.

**answer_en:**
Under "My Journey" you can see where you stand:
- How many jobs you've looked at
- Where you've applied
- What's still open
- How past applications went

Job searching often feels like screaming into the void. Here you see: you're making progress.

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
Wenn du Matches hast: Durchschauen, Favoriten markieren.
Wenn du Favoriten hast: Bei interessanten Stellen Doug beauftragen.
Wenn du dich beworben hast: Warten — und vielleicht mit Adele üben.

Ich sage dir immer, was als nächstes sinnvoll wäre.

**answer_en:**
That depends on where you are.

If you're new: Complete your profile.
If you have matches: Review them, mark favorites.
If you have favorites: Send Doug to research interesting ones.
If you've applied: Wait — and maybe practice with Adele.

I'll always tell you what makes sense next.

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

---

## END OF CORPUS

**Total Q&A pairs:** 35  
**Categories covered:** pricing (4), privacy (4), how_it_works (3), profile (3), matches (3), market (3), mira (3), doug (2), adele (2), journey (2), contact (2), boundaries (4), misc (3)

---

*— Sage, 2026-02-02*
