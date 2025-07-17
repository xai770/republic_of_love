#!/bin/bash

# Requirements Extraction Test Suite
# Tests multiple models against multiple Deutsche Bank job postings
# Generates summary report for analysis

OUTPUT_FILE="extraction_test_results_$(date +%Y%m%d_%H%M%S).md"

# Models to test (from your ollama list)
MODELS=("mistral:latest" "qwen3:latest" "deepseek-r1:8b" "phi4-mini-reasoning:latest")

# Test cases - different job types from your dataset
declare -A TEST_JOBS

TEST_JOBS["consulting"]='Senior Consultant (d/m/w) – Deutsche Bank Management Consulting Job ID:R0319547 Listed: 2025-07-01 Regular/Temporary: Regular Location: Frankfurt Position Overview Unser Team: https://management-consulting.db.com/Als Teil des Deutsche Bank Management Consulting (DBMC), der globalen Managementberatung der Deutschen Bank, arbeitest du mit Führungskräften zusammen, um zu den Erfolgen der Bank beizutragen. Zu unseren Beratungsschwerpunkten zählen die Umsetzung von Strategie- und Transformationsprojekten, u.a. hinsichtlich der Förderung von Innovations- und Wachstumsthemen sowie weiterer wichtiger Herausforderungen der Bank. Im Rahmen der Tätigkeit kannst Du engen Kontakt zu Führungskräften pflegen und Dir so ein Netzwerk innerhalb der Bank aufbauen.Um innovatives Denken zu fördern, setzen wir auf ein Team aus verschiedensten Persönlichkeiten. Wir legen Wert darauf, ein Arbeitsumfeld zu schaffen, in dem sich jedes Teammitglied zugehörig fühlen und authentisch sein kann. Was wir Dir bieten:Um die Transformation und die Wachstumsambitionen der Bank zu unterstützen, sind wir auf der Suche nach Engagement Managern für unser Team in Deutschland. Dich erwarten verantwortungsvolle und abwechslungsreiche Tätigkeiten – und das vom ersten Tag an. Alle 3-6 Monate rotierst Du in neue Projektteams und lernst so alle Unternehmensbereiche (Corporate & Investment Bank, DWS, Privat- und Firmenkundenbank) sowie Infrastrukturfunktionen (z.B. Risiko, Finanzen) der Bank kennen. Deine Tätigkeitsschwerpunkte:Du arbeitest an strategischen Projekten und übernimmst Verantwortung für Aufgaben in Teilprojekten und für TeammitgliederDu stehst im direkten Austausch mit unseren Kunden innerhalb der Bank und führst eigenständig Termine durchZusammen mit dem DBMC Engagement Manager verantwortest du die Vorbereitung von Entscheidungsvorlagen für das Senior Management und den VorstandDu unterstützt die Entwicklung deines Projektteams sowie die Konzeption von Best Practices und weiteren MethodenDein Profil: Wir sind auf der Suche nach Talenten mit überdurchschnittlichen akademischen Leistungen aller Fachrichtungen (Bachelor-/Master-Abschluss), um einen positiven Beitrag für unsere Kunden leisten zu können. Fachliche Qualifikation ist uns sehr wichtig, noch entscheidender für uns ist jedoch Deine Persönlichkeit.Du hast einschlägige Berufserfahrung gesammelt, idealerweise im Projektmanagement oder in einer UnternehmensberatungDu bist eine verantwortungsbewusste, engagierte Persönlichkeit mit hervorragenden analytischen Fähigkeiten und hast ein OrganisationstalentDu arbeitest gerne im Team und Deine verhandlungssicheren kommunikativen Fähigkeiten in Deutsch und Englisch ermöglichen die Arbeit in einem internationalen ArbeitsumfeldDu bist konfliktfähig und überzeugst andere gerne von Deinen Ideen und Lösungsansätzen Du legst großen Wert auf deine Aus- und Weiterbildung und unterstützt andere Kollegen hierbei'

TEST_JOBS["sap_technical"]='Senior SAP ABAP Engineer – Group General Ledger (f/m/x) Job ID:R0328439 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-24 Location: Frankfurt Position Overview Über den BereichFinanz-Konsolidierung, Berichterstattung, Geschäftsplanung und Performance-Management: Das SAP Group General Ledger-Team ist für die globalen SAP-Plattformen basierend auf SAP HANA in der Deutschen Bank (DB) verantwortlich, erstellt vierteljährlich die DB-Finanzberichte, inklusive der Publizierung an unsere Shareholder. Die Teams verantworten strategische Veränderungsinitiativen, wie das Design und die Implementierung der Planungs- und Prognoselösung für die DB weltweit, treiberbasiertes Kostenmanagement/-zuordnung, die Migration von SAP-Systemen in die Google Cloud und die zukünftige Einführung von Gen AI/ML unter Nutzung von SAP-Produkten. Ebenso sind wir für die Einführung des ESG Target Reporting verantwortlich. Als Software Senior Engineer sind Sie Teil eines sehr erfahrenen Squad & Engineering Chapters, gestalten die Design- und komplexe Entwicklungsarbeit strategischer, globaler und großangelegter Lösungen mit und arbeiten dabei sehr eng mit dem Produkt-Verantwortlichen / Business Lead zusammenZudem bieten wir Ihnen:Ein globales und vielfältiges Team, das das SAP-Produktportfolio für unseren weltweiten Kundenkreis, hauptsächlich von Deutschland aus, betreutEin sehr erfahrenes SAP-Team, das globale SAP-Lösungen in der gesamten DB vorantreibtMöglichkeiten zum globalen technischen Wissensaustausch in der globalen BankenbrancheEinen Mentor, der Sie in der Startphase im Arbeitsalltag unterstütztIhre AufgabenSie sind verantwortlich für die eigenständige Analyse von Geschäftsprozessen, den Entwurf und die Entwicklung umfangreicher Softwarelösungen auf Basis von SAP-Plattformen unter Nutzung unserer agilen Methodik in einem großen EntwicklungsteamSie entwickeln Komponenten der strategischen Planungslösung in der Bank unter Nutzung von SAP, einschließlich der SAP HANA-Datenbank mit SQL, Customizing in BPC und SAC, UI-Entwicklung auf Basis von Fiori und vielem mehrSie integrieren Google Cloud-Funktionen, Gen AI- und Python-Modelle mit SAP-Lösungen (z.B. SAP PaPM) in die globale Plattform und ermöglichen die Finanzmodellierung der DB für Kosten- und UmsatzprognosenSie arbeiten mit erfahrenen SAP-Software-Entwickler*innen eng zusammen für eine integrierte, qualitativ hochwertige Lösung in bestehende Prozesse und Softwarelösungen für unsere Finanzkunden bis hin zum Vorstand der DBEbenso arbeiten Sie mit den technischen Architekt*innen und Software-Entwickler*innen eng zusammen, um gemeinsam nach den „Best-in-Class" Lösungen zu strebenDabei sind Sie zuständig für die Gewährleistung, Zuverlässigkeit, Belastbarkeit und Wiederverwendbarkeit von Software durch die Entwicklung strategischer Lösungen unter Nutzung des CI-/CT-/CD-Frameworks, einschließlich automatisierter Unit-Tests, Leistungstests, Post-Go-Live-Validierung und Prüfungen während des gesamten Lebenszyklus der SoftwareWeiterhin unterstützen Sie den ITAO bei Audit Themen, Policies und Standards-Erfüllung sowie der Definition von Compliance Themen als auch die Einhaltung der regulatorischen Standards im UnternehmenIhre Fähigkeiten und ErfahrungenAbschluss einer anerkannten Universität/Hochschule mit Schwerpunkt IT oder Betriebswirtschaft oder vergleichbare Ausbildung/Berufserfahrung (Bankkaufmann/-frau wünschenswert)Fundierte Berufserfahrung in der Entwicklung und Programmierung großer und komplexer Softwarelösungen in SAP-Produkten wie: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI und Planung, SAP HANA, BW/4HANA, respektive die Entwicklung neuer Lösungen und die Pflege einer großen ABAP-Codebasis zur Unterstützung verschiedener Kernprozesse der BankErfahrungen in den als IT Application Owner oder IT Application Owner Delegate und der in der Bank verwendeten Methoden sind wünschenswertVorteilhaft sind Modellierungskenntnisse, die KI / ML für Finanzdaten nutzenWünschenswert sind Erfahrungen in Bereichen wie: SAP BTP, DataSphere und die Gen AI-Produkte von SAP; Design und Softwareentwicklung integrierter Reporting-Lösungen wie SAC BI, SAP Business Objects, Tableau oder SAP SACVorteilhaft sind Erfahrungen mit agilen Entwicklungsmethoden, einschließlich DevOps-Konzepten; Erfahrungen mit Google Cloud-Services, wie dem Vertex- oder Cortex-Framework und anderen Technologien, wie Python, JSON, .Net oder TableauTeamplayer*in, die/der in einem globalen und vielfältigen Team zusammenarbeitetAusgeprägte Kunden- und strategische LösungsorientierungSie unterstützen das kontinuierliche Lernen und die offene Feedback-KulturFließende Englischkenntnisse; Deutschkenntnisse sind wünschenswert'

TEST_JOBS["sales"]='Institutional Cash and Trade Sales Specialist (Client Sales Manager) – DACHLIE (f/m/x) Job ID:R0339981 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-04-01 Location: Frankfurt Position Overview Über den BereichInstitutional Cash and Trade (ICT) ist eine dynamische globale Organisation, die aus verschiedenen Deutsche Bank Corporate Bank Lokationen Institutional Cash Management und Trade Finance Dienstleistungen für Banken anbietet. Wir suchen einen Sales Spezialisten (Client Sales Manager) für die ICT DACHLIE Region, welche Deutschland, Schweiz, Österreich und Liechtenstein einschließt. Als ICT Sales Spezialist werden Sie für Banken in diesen Ländern zuständig sein. Ihre AufgabenErfüllen der Sales Ziele in Ihrem Portfolio und qualitative hochstehende Betreuung der bestehenden KundenSie verstehen den Risikoappetit von ICT und die Risikoprofile Ihrer bestehenden und potenziellen NeukundenSie benutzen aktiv unsere MIS- und Reporting-Tools für das Management Ihrer NamenSie stellen die Einhaltung aller relevanten DB Group und US Supervision Prozesse sicher und erfüllen alle obligatorischen Trainings und risikorelevanten Aufgaben pünktlich und zuverlässigSie entwickeln Ihr Portfolio aktiv und stehen Ihren Kunden mit Ihrem Know-How proaktiv zur VerfügungIhre Fähigkeiten und ErfahrungSie haben mehrjährige Erfahurng im Correspondent Banking bei einer größeren europäischen oder amerikanischen BankSie besitzen Produktkenntnisse in den Bereichen Cash Management (internationaler, grenzüberschreitender Zahlungsverkehr, Liquiditätsteuerung für Banken) und im Trade FinanceSie überzeugen mit Ihren Fähigkeiten zum Präsentieren um sowohl schriftlich als auch mündlich unsere Strategie, Produkte und unseren Risikoappetit zu repräsentierenSie sind eine kundenorientierte Persönlichkeit, die Wert auf langfristige Partnerschaften legt und Mehrwert für den Kunden schafftSie können fliessend in Deutsch und Englisch kommunizieren (schriftlich & mündlich)'

# Standardized prompt template
get_prompt() {
    local job_content="$1"
    cat << EOF
You are a requirements extraction specialist. Analyze this Deutsche Bank job posting and extract specific, job-relevant requirements in each category. DO NOT use generic templates.

JOB POSTING:
$job_content

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
}

# Initialize output file
echo "# Requirements Extraction Test Results" > "$OUTPUT_FILE"
echo "Generated: $(date)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Test each model against each job type
for model in "${MODELS[@]}"; do
    echo "## Model: $model" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "Testing model: $model"
    
    for job_type in "${!TEST_JOBS[@]}"; do
        echo "  Testing job type: $job_type"
        
        echo "### Job Type: $job_type" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        
        # Get the prompt
        prompt=$(get_prompt "${TEST_JOBS[$job_type]}")
        
        # Run extraction with timeout
        echo "**Extraction Result:**" >> "$OUTPUT_FILE"
        echo '```json' >> "$OUTPUT_FILE"
        
        # Use timeout to prevent hanging
        timeout 60s ollama run "$model" << EOF >> "$OUTPUT_FILE" 2>&1
$prompt
EOF
        
        if [ $? -eq 124 ]; then
            echo "TIMEOUT - Model took longer than 60 seconds" >> "$OUTPUT_FILE"
        fi
        
        echo '```' >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        
        # Brief pause between tests
        sleep 2
    done
    
    echo "---" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
done

# Generate summary analysis section
echo "## Summary Analysis" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "### Test Coverage" >> "$OUTPUT_FILE"
echo "- **Models tested**: ${#MODELS[@]} (${MODELS[*]})" >> "$OUTPUT_FILE"
echo "- **Job types tested**: ${#TEST_JOBS[@]} (${!TEST_JOBS[*]})" >> "$OUTPUT_FILE"
echo "- **Total test combinations**: $((${#MODELS[@]} * ${#TEST_JOBS[@]}))" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "### Key Questions to Analyze" >> "$OUTPUT_FILE"
echo "1. **Consistency**: Do models extract similar requirements from the same job?" >> "$OUTPUT_FILE"
echo "2. **Specificity**: Are extractions job-specific or generic?" >> "$OUTPUT_FILE"
echo "3. **Completeness**: Do models find all requirement categories?" >> "$OUTPUT_FILE"
echo "4. **Accuracy**: Are extracted requirements actually present in the job posting?" >> "$OUTPUT_FILE"
echo "5. **JSON Validity**: Do all outputs follow the required format?" >> "$OUTPUT_FILE"
echo "6. **Bilingual Handling**: How well do models process mixed German/English content?" >> "$OUTPUT_FILE"
echo "7. **Performance**: Which models provide best extraction quality?" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "### Notes for Analysis" >> "$OUTPUT_FILE"
echo "- Look for hallucinated requirements not present in source text" >> "$OUTPUT_FILE"
echo "- Check if models handle 'Experience level not quantified' appropriately" >> "$OUTPUT_FILE"
echo "- Compare technical requirement extraction across different job types" >> "$OUTPUT_FILE"
echo "- Evaluate how models handle Deutsche Bank-specific terminology" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "Test completed! Results saved to: $OUTPUT_FILE"
echo "Total combinations tested: $((${#MODELS[@]} * ${#TEST_JOBS[@]}))"