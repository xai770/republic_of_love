#!/bin/bash

# Test requirements extraction with mistral:latest
# Using Deutsche Bank Senior Consultant job posting

ollama run mistral:latest << 'EOF'
You are a requirements extraction specialist. Analyze this Deutsche Bank job posting and extract specific, job-relevant requirements in each category. DO NOT use generic templates.

JOB POSTING:
Senior Consultant (d/m/w) – Deutsche Bank Management Consulting Job ID:R0319547 Listed: 2025-07-01 Regular/Temporary: Regular Location: Frankfurt Position Overview Unser Team: https://management-consulting.db.com/Als Teil des Deutsche Bank Management Consulting (DBMC), der globalen Managementberatung der Deutschen Bank, arbeitest du mit Führungskräften zusammen, um zu den Erfolgen der Bank beizutragen. Zu unseren Beratungsschwerpunkten zählen die Umsetzung von Strategie- und Transformationsprojekten, u.a. hinsichtlich der Förderung von Innovations- und Wachstumsthemen sowie weiterer wichtiger Herausforderungen der Bank. Im Rahmen der Tätigkeit kannst Du engen Kontakt zu Führungskräften pflegen und Dir so ein Netzwerk innerhalb der Bank aufbauen.Um innovatives Denken zu fördern, setzen wir auf ein Team aus verschiedensten Persönlichkeiten. Wir legen Wert darauf, ein Arbeitsumfeld zu schaffen, in dem sich jedes Teammitglied zugehörig fühlen und authentisch sein kann. Was wir Dir bieten:Um die Transformation und die Wachstumsambitionen der Bank zu unterstützen, sind wir auf der Suche nach Engagement Managern für unser Team in Deutschland. Dich erwarten verantwortungsvolle und abwechslungsreiche Tätigkeiten – und das vom ersten Tag an. Alle 3-6 Monate rotierst Du in neue Projektteams und lernst so alle Unternehmensbereiche (Corporate & Investment Bank, DWS, Privat- und Firmenkundenbank) sowie Infrastrukturfunktionen (z.B. Risiko, Finanzen) der Bank kennen. Deine Tätigkeitsschwerpunkte:Du arbeitest an strategischen Projekten und übernimmst Verantwortung für Aufgaben in Teilprojekten und für TeammitgliederDu stehst im direkten Austausch mit unseren Kunden innerhalb der Bank und führst eigenständig Termine durchZusammen mit dem DBMC Engagement Manager verantwortest du die Vorbereitung von Entscheidungsvorlagen für das Senior Management und den VorstandDu unterstützt die Entwicklung deines Projektteams sowie die Konzeption von Best Practices und weiteren MethodenDein Profil: Wir sind auf der Suche nach Talenten mit überdurchschnittlichen akademischen Leistungen aller Fachrichtungen (Bachelor-/Master-Abschluss), um einen positiven Beitrag für unsere Kunden leisten zu können. Fachliche Qualifikation ist uns sehr wichtig, noch entscheidender für uns ist jedoch Deine Persönlichkeit.Du hast einschlägige Berufserfahrung gesammelt, idealerweise im Projektmanagement oder in einer UnternehmensberatungDu bist eine verantwortungsbewusste, engagierte Persönlichkeit mit hervorragenden analytischen Fähigkeiten und hast ein OrganisationstalentDu arbeitest gerne im Team und Deine verhandlungssicheren kommunikativen Fähigkeiten in Deutsch und Englisch ermöglichen die Arbeit in einem internationalen ArbeitsumfeldDu bist konfliktfähig und überzeugst andere gerne von Deinen Ideen und Lösungsansätzen Du legst großen Wert auf deine Aus- und Weiterbildung und unterstützt andere Kollegen hierbeiWas wir Dir auch bieten:Die Stelle wird in Voll- und in Teilzeit angeboten. Wir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und persönlichen Bedürfnisse abdecken.

Extract requirements in this exact JSON format:

{
  "technical_requirements": ["specific skills, tools, software mentioned"],
  "business_requirements": ["domain knowledge, industry experience needed"], 
  "soft_skills": ["communication, leadership, analytical abilities specified"],
  "experience_requirements": ["years of experience, specific roles, industry background"],
  "education_requirements": ["degree level, field of study, certifications mentioned"]
}

Focus on what is SPECIFICALLY mentioned in this posting. If experience years aren't specified, say "Experience level not quantified" rather than making assumptions.
EOF