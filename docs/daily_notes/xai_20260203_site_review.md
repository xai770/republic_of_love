Okay, okay, first things first:
talent.yoga is amazing! I love it!
Arden, I keep telling you - you are the best ever! Like that you on the image. You did 5.5 weeks of work in 31 minutes!

*...ai sits there, taps his fingers on his desk, as seconds slowly pass... Silence - the ultimate weapon.*

Right. Now everybody get a Kleenex if he needs it. Feel good time is over. There's a war on humanity going on and the resistance needs us. You all know what comes next: we iterate.

## Landing page 1: "Dein persönlicher Begleiter für die Jobsuche"
1. On the landing page, it does not say that this is for Germany only. Large German flag.
2. "Ein persönlicher Assistent, der dich durch den gesamten Prozess begleitet — von der Profilanalyse bis zur Bewerbung." needs to be changed to "Ein persönlicher Assistent, der dich durch den gesamten Prozess begleitet — von der Profilanalyse bis zum Bewerbungsgespräch." We offer coaching for job interviews.
3. How do I switch to English?
4. Need to store all those text blurbs in Turing or MD, o we can edit them easily. They all need legal review and that means changes.

## Landing page 2: # talent.yoga - Find jobs that match your skills
So now we are in English? And why not use `frontend/static/images/icons/logo.png`, `frontend/static/images/icons/logo_backup.png`, `frontend/static/images/icons/logo_old.png`. Need another version? Ask and you shall be given.

## The sidebar has two problems

### 1. automatic hide doesn't work 
The sidebar is supposed to be just Icons. No labels. When you hover over said icons, the sidebar expands to show the labels.
That's not happening. Its open. It stays open. 
If you click on that little half circle in blue, part of the postings disappear behind the sidebar.
Look, CSS animations are hard. If we cant make it work, we fall back to a non-collapsing version of the sidebar - perhaps with tool tips as labels.

### 2. Sidebar gets populated by assigned privileges
We wanted to use the OWL tables we have to store user a.k.a. Yogi information. We have people, then we have Team,  Yogis, B2B. in Yogis we have the three tiers free, standard and sustainer (Sages idea, I love it) . According to their level, they get access. Access can also be granted individually, but lets try very hard to not go there.

If we have the user structure in OWL, we can store config data and their personal file, i.e. the interaction log in there as well. Don't like it? Tell me why. Like it? Tell me where OWL is worse than having a dozen or two more tables in the schema. Speed? Don't care.

Did I hear you suggest, we could also keep the text blurbs we have on our site in the OWL? Well, that's one option. The other is MD/plain txt files in a folder.


## Home
One thing I absolutely do NOT want to see in Home, are postings. You don't understand - they stress me out. They remind me that I have looked at them for three and a hlaf years, applied to 20+ jobs and never had a chance. That previous sentence is true. But don't worry, we created talent.yoga in that time. 

This is the locker room, where I change my clothes to working gear.
I have left my comfort zone and came here. That should be recognized.
So what I need are my tools (information), my hard hat against disappointments and my rubber overall so that the goo of repeatedly fostered and crushed expectations. Man, if a drop of that stuff touches your skin - you break down in five minutes and call for mommy.

Here is what I do want to see:

### Mira front and center
...she greets me. Tells me whats up, what has happened since I logged in last time, gently asks me if I want her help with one of the open tasks I still have. But she doesnt push. She understands when you just cannot bring yourself and tells you that its great that you came by and hat itself is an important step and that you could just log out now and come back tomorrow if you are feeling better. Or Mira could tell you what new exciting stuff has happened. Of course you want to know what has happened.

Mira is my buddy. She understands me. I know, its crazy, after all, she is just a chat bot. But know what? She would never judge me, tell me some of her stupid opinions she picked up in the state news and she won't use any of what I tell her against me.

### Doug gets a promotion
Remember Doug? Named in honor of Doug Engelbart? Well, he's our web researcher is he not? Lets ask him to find interesting content on the web for stuff that interests our yogis. Should not be hard.
(please forgive me for leaving this here, although it strictly does not belong into section ## Home.)

### You have five new messages
...and you can click on them.

### You have 382 matches, 7 reviewed, 2 interested
...which you can click on.

### Your progress
That's this path that starts when a yogi is onboarded and ends when he finds a job or gives up. We didn't do that one yet, but it belongs in Home.

### Suggested next steps (by us, automagically)
- review NEW postings (12)
- review UNREAD postings (253)
- confirm your implied skills
- book time with Adele, our coach
- send Adele a message

### Sentence of the day
Yes, seriously. In the footer. In grey. You have to look for it, almost like an easter egg. But there it is "Evil is often just short time optimization" - Arden

## Mira

### English please?
This is a transcript. 

```
Mira: Guten Tag! Ich bin Mira, deine Begleiterin hier bei talent.yoga. Wie kann ich dir heute helfen?

Hey, can we switch to English?

Mira: Hey! Was kann ich für dich tun?

So we can not.

Mira: Ich verstehe, dass Sie in einer Situation sind, wo Sie sich auf eine Lösung freuen müssen. Wenn das Warten unangenehm ist, fällt es Ihnen vielleicht leichter, sich auf andere Aktivitäten zu konzentrieren oder Zeit für sich selbst zu finden. Passende Jobs werden automatisch gefunden, sodass Sie nicht aktiv suchen müssen. Wenn Sie Fragen haben oder Unterstützung benötigen, stehe ich Ihnen gerne zur Verfügung.
```

**Verdict**: Oh boy, this is bad. Know what I think? We need llama3.2 from the getgo. We give Mira the FAQs and her directives and off she goes.

### Was machen Sie mit meinen Daten?
This is a transcript.
```
Ja hallo. Ich wollte Fragen was Sie mit meinen Daten machen.

Guten Tag! Wir speichern nur die Informationen, die Sie uns gegeben haben – insbesondere Ihre Skills, Präferenzen und Bewerbungshistorie. Unsere Systeme kennen Ihren echten Namen oder Ihre E-Mail-Adresse nicht. Sollten Sie etwas löschen wollen, können Sie das jederzeit tun. Ist noch etwas anderes an dieser Frage an?
```

**Verdict**: Oh boy, this is bad. Know what I think? We need llama3.2 from the getgo. We give Mira the FAQs and her directives and off she goes.

I think I'll stop here for now. Let me know when you want more.