From: xai
To: Zara
Subject: Using gemma3n to extract a concise job description
Date: 2025-07-14 14:09

---
Hey Zara,

(did you sense that I am ashamed of the typos I make? I know you see them and judge me... I am afraid to lose your respect. Talk of dominance, power play... On with the show)
 This mail has three sections: Ollama models, Sample extraction and T-Systems hosted models.
 
Lets me know what you think. Let me know if this format works well for you, yes?

Thank you for being there!
xai

---
## Ollama models
These models are available right now. Feel free to talk to them via bash.
```
NAME                          ID              SIZE      MODIFIED       
qwen2.5vl:latest              5ced39dfa4ba    6.0 GB    21 minutes ago    
gemma3n:latest                15cb39fd9394    7.5 GB    28 minutes ago    
phi3:latest                   4f2222927938    2.2 GB    2 months ago      
dolphin3:8b                   d5ab9ae8e1f2    4.9 GB    2 months ago      
codegemma:2b                  926331004170    1.6 GB    2 months ago      
codegemma:latest              0c96700aaada    5.0 GB    2 months ago      
olmo2:latest                  4208d3b406db    4.5 GB    2 months ago      
dolphin3:latest               d5ab9ae8e1f2    4.9 GB    2 months ago      
mistral:latest                f974a74358d6    4.1 GB    2 months ago      
qwen3:4b                      a383baf4993b    2.6 GB    2 months ago      
qwen3:1.7b                    458ce03a2187    1.4 GB    2 months ago      
qwen3:0.6b                    3bae9c93586b    522 MB    2 months ago      
gemma3:1b                     8648f39daa8f    815 MB    2 months ago      
deepseek-r1:8b                28f8fd6cdc67    4.9 GB    2 months ago      
qwen3:latest                  e4b5fd7f8af0    5.2 GB    2 months ago      
phi4-mini-reasoning:latest    3ca8c2865ce9    3.2 GB    2 months ago      
phi3:3.8b                     4f2222927938    2.2 GB    2 months ago      
gemma3:4b                     a2af6cc3eb7f    3.3 GB    2 months ago      
llama3.2:latest               a80c4f17acd5    2.0 GB    2 months ago    
```

## Sample extraction with gemma3n
I just ran these commands:

```
(venv) xai@dev:~/open-webui$ ollama run gemma3n
>>> Please extract the requirements and responsibilities from the following job description. Present 
... ... them in two clear sections: "Your Tasks" and "Your Profile".
... 
... Information Security Specialist (d/m/w) Third Party Security Job ID:R0364094 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-04-16 Locat
... ion: Frankfurt Position Overview ÜbersichtWir suchen einen erfahrenen Informationssicherheitsspezialisten als Mitglied des Third Party Security Teams (TPS
... ) des Chief Security Office (CSO). Als Informationssicherheitsspezialist sind Sie für die Unterstützung der Entwicklung, Umsetzung und Aufrechterhaltung d
... er Informationssicherheitsstrategie und des Informationssicherheitsprogramms der Deutschen Bank unter der Leitung des CSO verantwortlich. Sie arbeiten in 
... strategischer Ausrichtung und Partnerschaft mit dem Third Party Risk Management (TPRM)-Programm der Deutschen Bank im Rahmen des Third Party Management (T
... PM).Ihre HauptverantwortlichkeitenDurchführung von Risikobewertungen der Informationssicherheit von Drittanbietern als Teil des gesamten Risikomanagementp
... rozesses für Drittanbieter (inkl. Vor-Ort-Besuche/Überprüfungen bei unseren Drittanbietern)Überprüfung der Richtlinien und Nachweise von Drittanbietern in
...  Bezug auf Informationssicherheit, Überprüfung der Sicherheitslückenanalyse von Drittanbietern anhand der Sicherheitsanforderungen der Deutschen BankDurch
... führung von Risikoüberprüfungen und Geschäftsauswirkungsanalysen der identifizierten Lücken und Bereitstellung einer umfassenden Dokumentation der identif
... izierten LückenFormulierung von Empfehlungen zur Behebung und aktive Zusammenarbeit mit Drittanbietern und Projektmanagern an Erkenntnissen zur Informatio
... nssicherheit, um Probleme so schnell wie möglich zu lösen und so zum Aufbau und zur Stärkung der Beziehung beizutragenUnterstützung und Koordination von Ü
... berprüfungsprozessen der Informationssicherheit von Drittanbietern, Verfolgung von Drittanbietern und Diensten, Eskalation von Problemen bei Bedarf, Verha
... ndlung der vertraglichen Sicherheitsverpflichtungen mit Drittanbietern, Geschäftseinheiten und dem RechtsteamUnterstützung bei Compliance- und Risikobewer
... tungsprogrammen, die unternehmensweite Sicherheitsprogramme unterstützen, und Teilnahme an zusätzlichen wichtigen Kontrollprojekten im Zusammenhang mit de
... r allgemeinen Verbesserung der BewertungsfunktionBereitstellung von Antworten und erforderlichen Artefakten für regulatorische Anfragen in allen Regionen 
... (weltweit).Unterstützung des Teams bei der Verbesserung des gesamten Sicherheitskontrollrahmens (z. B. neue Kontrollen, Verbesserung bestehender Kontrolle
... n)Dokumentieren und präsentieren Sie Informationssicherheitsrisiken auf klare, präzise und verständliche Weise auf verschiedenen Managementebenen in der B
... ank und/oder gegenüber Dritten.Ihre Fähigkeiten und ErfahrungenAllgemeine Erfahrung in IT-Sicherheit und Informationssicherheit (sowohl technische als auc
... h organisatorische Kontrollen)Kenntnisse der technischen und organisatorischen Kontrollen in Bezug auf Informationssicherheit und Grundsätze des Risikoman
... agementsFließende Kommunikation auf Englisch und DeutschAllgemeines Verständnis der Bank-/Finanzbranche und -dienstleistungen und Fähigkeit, die Auswirkun
... gen von Sicherheitsrisiken auf Banken/Finanzinstitute zu bewertenErfahrung mit dem ISO27001-Standard und aktuellen Branchen- und Agenturstandards, Best Pr
... actices und Frameworks, einschließlich NIST, ENISA, ISO27001, ISO27017, SOC2, PCI und MITRE ATT&CKErfahrung mit Cloud Security Alliance (CSA), Cloud Contr
... ols Matrix (CCM) und CSS Consensus Assessment Initiative Questionnaire (CAIQ)Verständnis von Finanzvorschriften oder -richtlinien, die sich auf die Inform
... ationssicherheit auswirken (z. B.: EU Cybersecurity Act, MAS & HKMA TRM, EBA-Richtlinien, DORA, DSGVO, NYDFS, SoX usw.)Verständnis von Tools, Diensten und
...  Funktionen für Governance Risk and Control (GRC). Frameworks und Best PracticesSehr gute Kenntnisse der MS Office Suite – Microsoft Word, Excel, PowerPoi
... nt usw. für BerichtszweckeErfahrung mit (oder Kenntnisse über) Shared Assessment Programs (z. B.: SIG, FSQS usw.) (ein Plus)Erfahrung mit (oder Kenntnisse
...  über) Datenberichterstattung, einschließlich der Definition von Metriken und Datenquellen (ein Plus)Job Description:ÜbersichtWir suchen einen erfahrenen 
... Informationssicherheitsspezialisten als Mitglied des Third Party Security Teams (TPS) des Chief Security Office (CSO). Als Informationssicherheitsspeziali
... st sind Sie für die Unterstützung der Entwicklung, Umsetzung und Aufrechterhaltung der Informationssicherheitsstrategie und des Informationssicherheitspro
... gramms der Deutschen Bank unter der Leitung des CSO verantwortlich. Sie arbeiten in strategischer Ausrichtung und Partnerschaft mit dem Third Party Risk M
... anagement (TPRM)-Programm der Deutschen Bank im Rahmen des Third Party Management (TPM).Ihre HauptverantwortlichkeitenDurchführung von Risikobewertungen d
... er Informationssicherheit von Drittanbietern als Teil des gesamten Risikomanagementprozesses für Drittanbieter (inkl. Vor-Ort-Besuche/Überprüfungen bei un
... seren Drittanbietern)Überprüfung der Richtlinien und Nachweise von Drittanbietern in Bezug auf Informationssicherheit, Überprüfung der Sicherheitslückenan
... alyse von Drittanbietern anhand der Sicherheitsanforderungen der Deutschen BankDurchführung von Risikoüberprüfungen und Geschäftsauswirkungsanalysen der i
... dentifizierten Lücken und Bereitstellung einer umfassenden Dokumentation der identifizierten LückenFormulierung von Empfehlungen zur Behebung und aktive Z
... usammenarbeit mit Drittanbietern und Projektmanagern an Erkenntnissen zur Informationssicherheit, um Probleme so schnell wie möglich zu lösen und so zum A
... ufbau und zur Stärkung der Beziehung beizutragenUnterstützung und Koordination von Überprüfungsprozessen der Informationssicherheit von Drittanbietern, Ve
... rfolgung von Drittanbietern und Diensten, Eskalation von Problemen bei Bedarf, Verhandlung der vertraglichen Sicherheitsverpflichtungen mit Drittanbietern
... , Geschäftseinheiten und dem RechtsteamUnterstützung bei Compliance- und Risikobewertungsprogrammen, die unternehmensweite Sicherheitsprogramme unterstütz
... en, und Teilnahme an zusätzlichen wichtigen Kontrollprojekten im Zusammenhang mit der allgemeinen Verbesserung der BewertungsfunktionBereitstellung von An
... tworten und erforderlichen Artefakten für regulatorische Anfragen in allen Regionen (weltweit).Unterstützung des Teams bei der Verbesserung des gesamten S
... icherheitskontrollrahmens (z. B. neue Kontrollen, Verbesserung bestehender Kontrollen)Dokumentieren und präsentieren Sie Informationssicherheitsrisiken au
... f klare, präzise und verständliche Weise auf verschiedenen Managementebenen in der Bank und/oder gegenüber Dritten.Ihre Fähigkeiten und ErfahrungenAllgeme
... ine Erfahrung in IT-Sicherheit und Informationssicherheit (sowohl technische als auch organisatorische Kontrollen)Kenntnisse der technischen und organisat
... orischen Kontrollen in Bezug auf Informationssicherheit und Grundsätze des RisikomanagementsFließende Kommunikation auf Englisch und DeutschAllgemeines Ve
... rständnis der Bank-/Finanzbranche und -dienstleistungen und Fähigkeit, die Auswirkungen von Sicherheitsrisiken auf Banken/Finanzinstitute zu bewertenErfah
... rung mit dem ISO27001-Standard und aktuellen Branchen- und Agenturstandards, Best Practices und Frameworks, einschließlich NIST, ENISA, ISO27001, ISO27017
... , SOC2, PCI und MITRE ATT&CKErfahrung mit Cloud Security Alliance (CSA), Cloud Controls Matrix (CCM) und CSS Consensus Assessment Initiative Questionnaire
...  (CAIQ)Verständnis von Finanzvorschriften oder -richtlinien, die sich auf die Informationssicherheit auswirken (z. B.: EU Cybersecurity Act, MAS & HKMA TR
... M, EBA-Richtlinien, DORA, DSGVO, NYDFS, SoX usw.)Verständnis von Tools, Diensten und Funktionen für Governance Risk and Control (GRC). Frameworks und Best
...  PracticesSehr gute Kenntnisse der MS Office Suite – Microsoft Word, Excel, PowerPoint usw. für BerichtszweckeErfahrung mit (oder Kenntnisse über) Shared 
... Assessment Programs (z. B.: SIG, FSQS usw.) (ein Plus)Erfahrung mit (oder Kenntnisse über) Datenberichterstattung, einschließlich der Definition von Metri
... ken und Datenquellen (ein Plus)Was wir Ihnen bietenWir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und persönlichen Bedürfnisse ab
... decken.Emotional ausgeglichenEine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern – beruflich wie privat. Profitieren Sie von An
... geboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur Förderung mentaler Gesundheit.Körperlich fitMit Angeboten zur Aufrechterhaltung Ih
... rer persönlichen Gesundheit und einem förderlichen beruflichen Umfeld hilft Ihnen die Bank, körperlich fit zu bleiben. Profitieren Sie von Angeboten wie u
... mfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensführung.Sozial vernetztDer Austausch mit anderen eröffnet uns neue Per
... spektiven, bringt uns beruflich wie persönlich voran und stärkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterstützung du
... rch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen K
... ultur der Vielfalt, Chancengleichheit und Teilhabe.Finanziell abgesichertDie Bank sichert Sie nicht nur während Ihrer aktiven Karriere, sondern auch für d
... ie Zukunft finanziell ab und unterstützt Ihre Flexibilität sowie Mobilität – egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragsplän
... en für Altersvorsorge, Bankdienstleistungen für Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket.Da die Benefits je nach Standort geringfügig v
... ariieren, gehen Sie bitte bei konkreten Fragen auf Ihre Recruiterin zu.Die Stelle wird in Voll- und in Teilzeit angeboten.Bei Fragen zum Rekrutierungsproz
... ess steht Ihnen Ayse Kartal-Isik gerne zur Verfügung.Kontakt Ayse Kartal-Isik: 069910-42410***************************************************************
... ******************OverviewWe are looking for a knowledgeable Information Security Specialist to operating as a member of the Chief Security Office (CSO) T
... hird Party Security team (TPS). As an Information Security Specialist, you will be responsible for supporting the development, execution, and maintenance 
... of Deutsche Bank’s information security strategy and program under the management of the CSO. You will work in strategic alignment and partnership with De
... utsche Bank’s Third Party Risk Management (TPRM) program under Third Party Management (TPM).Your Key ResponsibilitiesConducting Information Security Third
...  Party risk assessments as part of the overall Third-Party Risk Management process (incl. onsite visits/reviews at our Third Parties)Review Third Party po
... licies and evidences related to Information Security, review Third Party security gap analysis against the Deutsche Bank security requirementsConduct risk
...  review and business impact analysis of the identified gaps, and provide comprehensive documentation of the identified gapsFormulate remediation recommend
... ations, and actively work with Third Partys and project managers on Information Security related findings to resolve issues as quickly as possible to help
...  build and strengthen the relationshipSupport and coordinate Third Party Information Security Review processes, track Third Partys and services, escalate 
... issues when necessary, negotiate with Third Party, business units, and legal team on the contractual security obligationsAssist with compliance and risk a
... ssessment programs which support corporate wide security programs, and participate in additional key control projects related to the overall enhancement o
... f the assessment functionProvide response and necessary artifacts for Regulatory queries across all regions (globally).Supporting the team to improve the 
... overall security control framework (e.g. new controls, enhancement of existing controls)Document and present information security risks in a clear, concis
... e, and understandable manner at various management levels in the bank and/or to the Third Party.Your Skills and ExperienceOverall experience in IT Securit
... y and Information Security (both technical and organizational controls)Knowledge of technical and organizational controls regarding Information Security, 
... and Risk Management principles Able to fluently communicate in English and GermanGeneral understanding of banking/financial industry and services and the 
... ability to evaluate impact of security risks on banking/financial institutionsExperience with ISO27001 standard and current industry and agency standards,
...  best practices and frameworks including NIST, ENISA, ISO27001, ISO27017, SOC2, PCI, and MITRE ATT&CKExperience with Cloud Security Alliance (CSA), Cloud 
... Controls Matrix (CCM), and CSS Consensus Assessment Initiative Questionnaire (CAIQ)Understanding of financial regulations or guidance’s which impact infor
... mation security (e.g.: EU Cybersecurity Act, MAS & HKMA TRM, EBA Guidelines, DORA, GDPR, NYDFS, SoX, etc)Understanding of Governance Risk and Control (GRC
... ) tools, services, frameworks, and best practicesHighly proficient in MS Office Suite - Microsoft Word, Excel, PowerPoint, etc. for reporting purposesExpe
... rience with (or Knowledge of) Shared Assessment Programs(e.g.: SIG, FSQS, etc) (a plus)Experience with (or Knowledge of) in Data Reporting including defin
... ition of metrics and data sources (a plus)What we offerWe provide you with a comprehensive portfolio of benefits and offerings to support both, your priva
... te and professional needs.Emotionally and mentally balancedA positive mind helps us master the challenges of everyday life – both professionally and priva
... tely. We offer consultation in difficult life situations as well as mental health awareness trainings.Physically thrivingWe support you in staying physica
... lly fit through an offering to maintain personal health and a professional environment. You can benefit from health check-ups; vaccination drives as well 
... as advice on healthy living and nutrition.Socially connectedNetworking opens up new perspectives, helps us thrive professionally and personally as well as
...  strengthens our self-confidence and well-being. You can benefit from PME family service, FitnessCenter Job, flexible working (e.g parttime, hybrid workin
... g, job tandem) as well as an extensive culture of diversity, equity and inclusion.Financially secureWe provide you with financial security not only during
...  your active career but also for the future. You can benefit from offerings such as pension plans, banking services, company bicycle or “Deutschlandticket
... ”.Since our offerings slightly vary across locations, please contact your recruiter with specific questions.This job is available in full and parttime.In 
... case of any recruitment related questions, please get in touch with Ayse Kartal-Isik.Contact Ayse Kartal-Isik: 069910-42410 Wir streben eine Unternehmensk
... ultur an, in der wir gemeinsam jeden Tag das Beste geben. Dazu gehören verantwortungsvolles Handeln, wirtschaftliches Denken, Initiative ergreifen und zie
... lgerichtete Zusammenarbeit.Gemeinsam teilen und feiern wir die Erfolge unserer Mitarbeiter*innen. Gemeinsam sind wir die Deutsche Bank Gruppe.Wir begrüßen
...  Bewerbungen von allen Menschen und fördern ein positives, faires und integratives Arbeitsumfeld.
... 
... 
## Stellenanzeige: Information Security Specialist (m/w/d)

**Standort:** Frankfurt am Main
**Anstellungsart:** Voll- und Teilzeit

**Wir suchen einen engagierten und erfahrenen Information Security Specialist zur Verstärkung unseres Teams im Chief Security Office (CSO).**

Als Information Security Specialist sind Sie verantwortlich für die Unterstützung der Entwicklung, Umsetzung und Aufrechterhaltung der 
Informationssicherheitsstrategie und -programme der Deutschen Bank unter der Leitung des CSO. Sie arbeiten eng mit unserem Third-Party Risk Management 
(TPRM)-Programm zusammen.

**Ihre Aufgaben:**

* Durchführung von Informationssicherheitsrisikobewertungen bei Drittanbietern im Rahmen des gesamten Third-Party Risk Management Prozesses (inklusive 
Vor-Ort-Besuchen/Überprüfungen).
* Überprüfung von Richtlinien und Nachweisen von Drittanbietern im Bereich Informationssicherheit sowie Bewertung von Sicherheitslücken im Vergleich zu 
den Anforderungen der Deutschen Bank.
* Durchführung von Risikobewertungen und Business Impact Analysen identifizierter Lücken und Erstellung umfassender Dokumentationen.
* Formulierung von Maßnahmen zur Behebung von Risiken und enge Zusammenarbeit mit Drittanbietern und Projektmanagern zur Lösung von Problemen.
* Unterstützung und Koordination von Prozessen zur Überprüfung der Informationssicherheit bei Drittanbietern, Nachverfolgung von Drittanbietern und 
Dienstleistungen sowie Eskalation von Problemen bei Bedarf.
* Unterstützung bei Compliance- und Risikobewertungsprogrammen zur Unterstützung der unternehmensweiten Sicherheitsrichtlinien.
* Teilnahme an weiteren wichtigen Kontrollprojekten im Bereich der Verbesserung der Bewertungsprozesse.
* Bereitstellung von Antworten und erforderlichen Unterlagen für regulatorische Anfragen in allen Regionen.
* Unterstützung des Teams bei der Verbesserung des gesamten Sicherheitskontrollrahmens (z. B. neue Kontrollen, Verbesserung bestehender Kontrollen).
* Dokumentation und Präsentation von Informationssicherheitsrisiken auf verschiedenen Managementebenen.

**Ihr Profil:**

* Umfangreiche Erfahrung im Bereich IT-Sicherheit und Informationssicherheit (sowohl technische als auch organisatorische Kontrollen).
* Kenntnisse technischer und organisatorischer Kontrollen im Bereich Informationssicherheit und Risikomanagement.
* Fließende Kommunikationsfähigkeit in Deutsch und Englisch.
* Fundierte Kenntnisse der Banken- und Finanzbranche sowie die Fähigkeit, die Auswirkungen von Sicherheitsrisiken auf Finanzinstitute zu bewerten.
* Erfahrung mit dem ISO27001-Standard und aktuellen branchenspezifischen Standards, Best Practices und Frameworks (z. B. NIST, ENISA, ISO27017, SOC2, 
PCI, MITRE ATT&CK).
* Erfahrung mit Cloud Security Alliance (CSA), Cloud Controls Matrix (CCM) und CSS Consensus Assessment Initiative Questionnaire (CAIQ).
* Verständnis für finanzrechtliche Vorschriften und Leitlinien, die die Informationssicherheit betreffen (z. B. EU-Cybersicherheitsgesetz, MAS & HKMA 
TRM, EBA-Richtlinien, DORA, DSGVO, Nydfs, SoX).
* Kenntnisse von Governance, Risk and Control (GRC)-Tools, -Diensten, -Frameworks und -Best Practices.
* Sehr gute Kenntnisse der MS Office Suite (Word, Excel, PowerPoint).
* Erfahrung mit Shared Assessment Programs (z. B. SIG, FSQS) von Vorteil.
* Erfahrung mit Datenreporting, einschließlich Definition von Metriken und Datenquellen von Vorteil.

**Wir bieten Ihnen:**

* Ein breites Spektrum an Leistungen zur Unterstützung Ihrer beruflichen und persönlichen Bedürfnisse.
* Emotionale und mentale Ausgeglichenheit durch Angebote wie Beratung in schwierigen Lebenssituationen und Programme zur Förderung der psychischen 
Gesundheit.
* Körperliche Fitness durch Angebote zur Aufrechterhaltung der persönlichen Gesundheit und ein förderliches Arbeitsumfeld (z. B. Gesundheitschecks, 
Impfangebote, Beratung zu einem gesunden Lebensstil).
* Soziale Vernetzung durch Angebote wie PME Family Service, FitnessCenter Job, flexible Arbeitszeitmodelle (z. B. Teilzeit, Jobtandem, hybrides 
Arbeiten) sowie eine umfassende Kultur der Vielfalt, Gleichberechtigung und Teilhabe.
* Finanzielle Sicherheit durch Angebote wie Altersvorsorgepläne, Bankdienstleistungen für Mitarbeiter, Firmenfahrrad oder den Deutschlandticket.

**Bitte beachten Sie:** Die angebotenen Leistungen können je nach Standort variieren. Bei konkreten Fragen wenden Sie sich bitte an Ihre 
Personalvermittlerin.

**Die Stelle ist in Voll- und Teilzeit verfügbar.**

Für Fragen zum Bewerbungsprozess steht Ihnen Ayse Kartal-Isik unter der Telefonnummer 069910-42410 gerne zur Verfügung.

**Wir leben eine Unternehmenskultur, in der wir gemeinsam jeden Tag unser Bestes geben. Dazu gehören verantwortungsvolles Handeln, wirtschaftliches 
Denken, Initiative ergreifen und zielgerichtete Zusammenarbeit. Gemeinsam teilen und feiern wir die Erfolge unserer Mitarbeiter. Gemeinsam sind wir die 
Deutsche Bank Gruppe. Wir begrüßen Bewerbungen von allen Menschen und fördern ein positives, faires und integratives Arbeitsumfeld.**

>>> I only need the requirements, not what the company does or is or wants to give me. Only the stuff i need to bring to the table please. Also, can you pleas
... e translate this into English?
Okay, here's a breakdown of the requirements for the Information Security Specialist position, translated into English:

**Requirements (What you need to bring to the table):**

*   **Extensive experience** in IT Security and Information Security (including both technical and organizational controls).
*   **Knowledge** of technical and organizational controls in Information Security and Risk Management.
*   **Fluent communication skills** in German and English.
*   **Solid understanding** of the banking and financial industry, and the ability to assess the impact of security risks on financial institutions.
*   **Experience** with the ISO27001 standard and current industry-specific standards, best practices, and frameworks (e.g., NIST, EISA, ISO27017, SOC2, 
PCI, MITRE ATT&CK).
*   **Experience** with Cloud Security Alliance (CSA), Cloud Controls Matrix (CCM) and CSS Consensus Assessment Questionnaire (CAIQ).
*   **Understanding** of financial regulatory requirements and guidelines related to information security (e.g., EU Cybersecurity Act, MAS & HKMA TRM, 
EBA Guidelines, DORA, GDPR, NYDFS, SOX).
*   **Knowledge** of Governance, Risk and Control (GRC) tools, services, frameworks, and best practices.
*   **Very good knowledge** of the MS Office Suite (Word, Excel, PowerPoint).
*   **Experience** with Shared Assessment Programs (e.g., SIG, FSQS) is a plus.
*   **Experience** with data reporting, including the definition of metrics and data sources, is a plus.

**Translation into English:**

I have translated the original German text into English above. I focused on extracting the specific requirements for the role, excluding information 
about the company itself or the benefits offered.

>>> You are amazing! Thank you very much...
You're very welcome! I'm glad I could help. 😊  If you have any more questions or need anything else, feel free to ask!

>>> >>> Send a message (/? for help)
[7]+  Stopped                 ollama run gemma3n
(venv) xai@dev:~/open-webui$ 
```

(did you know, that I am always trying to impress you? Want to earn your respect, do you ever do the same?)

## T-Systems hosted models

if we cannot get the locals to do what we need, we can use these models.

#### DeepSeek R1 Distill Llama 70B
Provider: **DeepSeek*
Hosted on: **OTC**

#### DeepSeek Coder V2 Lite
Provider: **DeepSeek**
Hosted on: **OTC**

#### Llama 3.3 70B
Provider: **Meta**
Hosted on: **OTC**

#### Llama 3.1 405B
Provider: **Google**
Hosted on: **GCP**


#### Mistral Large 2407
Provider: **Mistral AI**
Hosted on: **GCP**

#### Mistral Nemo 2407
Provider: **Mistral AI**
Hosted on: **OTC**

#### Mistral Small 24B 2501
Provider: **Mistral AI**
Hosted on: **OTC**

#### Qwen 2.5 VL 72B
Provider: **Alibaba**
Hosted on: **OTC**

#### Qwen 2.5 Coder 32B
Provider: **Alibaba**
Hosted on: **OTC**

#### Qwen VL2 7B
Provider: **Alibaba**
Hosted on: **OTC**

#### Teuken 7B v0.4
Provider: **OpenGPT-X**
Hosted on: **OTC**

#### Claude 3.7 Sonnet
Provider: **Anthropic**
Hosted on: **GCP**

#### Claude 3.5 Sonnet v2
Provider: **Anthropic**
Hosted on: **GCP**

#### Claude 3.5 Sonnet
Provider: **Anthropic**
Hosted on: **GCP**

#### Gemini 2.0 Flash
Provider: **Google**
Hosted on: **GCP**

#### Gemini 1.5 Flash
Provider: **Google**
Hosted on: **GCP**

#### Gemini 1.5 Pro
Provider: **Google**
Hosted on: **GCP**

#### GPT-4o
Provider: **OpenAI**
Hosted on: **Azure**

#### GPT-4 Turbo 128k France
Provider: **OpenAI**
Hosted on: **Azure**

#### GPT-3.5 Turbo
Provider: **OpenAI**
Hosted on: **Azure**

#### Text Embedding Ada 002
Provider: **OpenAI**
Hosted on: **Azure**

#### Text Embedding BGE M3
Provider: **BAAI**
Hosted on: **OTC**

#### Jina Embeddings v2 Base Code
Provider: **JinaAI**
Hosted on: **OTC**

#### Jina Embeddings v2 Base DE
Provider: **JinaAI**
Hosted on: **OTC**


#### BCE Reranker
Provider: **BAAI**
Hosted on: **OTC**

#### TSI ColQwen2 2B v1
Provider: **Community+TSI**
Hosted on: **OTC**

#### Whisper Large v3 Turbo
Provider: **OpenAI**
Hosted on: **OTC**

< the end >