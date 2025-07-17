#!/usr/bin/env python3
"""
Critical Diagnosis: German Language Technical Requirements Extraction Crisis
==========================================================================

The daily report is showing severe technical extraction failures, particularly:
1. SAP ABAP Engineer job is missing ABAP, SAP HANA, BPC, SAC, BTP, etc.
2. Sales Specialist job incorrectly shows programming languages (GO, R, Python)
3. German text sections are being completely missed

This script will diagnose the root cause by testing extraction on actual job data.
"""

import re
import sys
import os

# Add the correct path to the specialist
sys.path.append('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_crisis_resolution_20250702')

def test_sap_job_extraction():
    """Test extraction on the SAP ABAP Engineer job that's severely under-extracting"""
    
    sap_job_description = """
Senior SAP ABAP Engineer – Group General Ledger (f/m/x) Job ID:R0328439 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-24 Location: Frankfurt Position Overview *English version below*Über den BereichFinanz-Konsolidierung, Berichterstattung, Geschäftsplanung und Performance-Management: Das SAP Group General Ledger-Team ist für die globalen SAP-Plattformen basierend auf SAP HANA in der Deutschen Bank (DB) verantwortlich, erstellt vierteljährlich die DB-Finanzberichte, inklusive der Publizierung an unsere Shareholder. Die Teams verantworten strategische Veränderungsinitiativen, wie das Design und die Implementierung der Planungs- und Prognoselösung für die DB weltweit, treiberbasiertes Kostenmanagement/-zuordnung, die Migration von SAP-Systemen in die Google Cloud und die zukünftige Einführung von Gen AI/ML unter Nutzung von SAP-Produkten. Ebenso sind wir für die Einführung des ESG Target Reporting verantwortlich. Als Software Senior Engineer sind Sie Teil eines sehr erfahrenen Squad & Engineering Chapters, gestalten die Design- und komplexe Entwicklungsarbeit strategischer, globaler und großangelegter Lösungen mit und arbeiten dabei sehr eng mit dem Produkt-Verantwortlichen / Business Lead zusammenZudem bieten wir Ihnen:Ein globales und vielfältiges Team, das das SAP-Produktportfolio für unseren weltweiten Kundenkreis, hauptsächlich von Deutschland aus, betreutEin sehr erfahrenes SAP-Team, das globale SAP-Lösungen in der gesamten DB vorantreibtMöglichkeiten zum globalen technischen Wissensaustausch in der globalen BankenbrancheEinen Mentor, der Sie in der Startphase im Arbeitsalltag unterstütztIhre AufgabenSie sind verantwortlich für die eigenständige Analyse von Geschäftsprozessen, den Entwurf und die Entwicklung umfangreicher Softwarelösungen auf Basis von SAP-Plattformen unter Nutzung unserer agilen Methodik in einem großen EntwicklungsteamSie entwickeln Komponenten der strategischen Planungslösung in der Bank unter Nutzung von SAP, einschließlich der SAP HANA-Datenbank mit SQL, Customizing in BPC und SAC, UI-Entwicklung auf Basis von Fiori und vielem mehrSie integrieren Google Cloud-Funktionen, Gen AI- und Python-Modelle mit SAP-Lösungen (z.B. SAP PaPM) in die globale Plattform und ermöglichen die Finanzmodellierung der DB für Kosten- und UmsatzprognosenSie arbeiten mit erfahrenen SAP-Software-Entwickler*innen eng zusammen für eine integrierte, qualitativ hochwertige Lösung in bestehende Prozesse und Softwarelösungen für unsere Finanzkunden bis hin zum Vorstand der DBEbenso arbeiten Sie mit den technischen Architekt*innen und Software-Entwickler*innen eng zusammen, um gemeinsam nach den „Best-in-Class" Lösungen zu strebenDabei sind Sie zuständig für die Gewährleistung, Zuverlässigkeit, Belastbarkeit und Wiederverwendbarkeit von Software durch die Entwicklung strategischer Lösungen unter Nutzung des CI-/CT-/CD-Frameworks, einschließlich automatisierter Unit-Tests, Leistungstests, Post-Go-Live-Validierung und Prüfungen während des gesamten Lebenszyklus der SoftwareWeiterhin unterstützen Sie den ITAO bei Audit Themen, Policies und Standards-Erfüllung sowie der Definition von Compliance Themen als auch die Einhaltung der regulatorischen Standards im UnternehmenIhre Fähigkeiten und ErfahrungenAbschluss einer anerkannten Universität/Hochschule mit Schwerpunkt IT oder Betriebswirtschaft oder vergleichbare Ausbildung/Berufserfahrung (Bankkaufmann/-frau wünschenswert)Fundierte Berufserfahrung in der Entwicklung und Programmierung großer und komplexer Softwarelösungen in SAP-Produkten wie: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI und Planung, SAP HANA, BW/4HANA, respektive die Entwicklung neuer Lösungen und die Pflege einer großen ABAP-Codebasis zur Unterstützung verschiedener Kernprozesse der BankErfahrungen in den als IT Application Owner oder IT Application Owner Delegate und der in der Bank verwendeten Methoden sind wünschenswertVorteilhaft sind Modellierungskenntnisse, die KI / ML für Finanzdaten nutzenWünschenswert sind Erfahrungen in Bereichen wie: SAP BTP, DataSphere und die Gen AI-Produkte von SAP; Design und Softwareentwicklung integrierter Reporting-Lösungen wie SAC BI, SAP Business Objects, Tableau oder SAP SACVorteilhaft sind Erfahrungen mit agilen Entwicklungsmethoden, einschließlich DevOps-Konzepten; Erfahrungen mit Google Cloud-Services, wie dem Vertex- oder Cortex-Framework und anderen Technologien, wie Python, JSON, .Net oder TableauTeamplayer*in, die/der in einem globalen und vielfältigen Team zusammenarbeitetAusgeprägte Kunden- und strategische LösungsorientierungSie unterstützen das kontinuierliche Lernen und die offene Feedback-KulturFließende Englischkenntnisse; Deutschkenntnisse sind wünschenswertWas wir Ihnen bietenWir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und persönlichen Bedürfnisse abdecken.
Your key responsibilitiesYour area of responsibility will be the analysis of business processes, designing and developing large scale software solutions based on SAP platforms, leveraging our agile methodology in a large size development teamInfluencing the development of the strategic Planning solution in the bank leveraging SAP including SAP HANA database with SQL, customizing in BPC and SAC, UI development based on Fiori and several moreIntegrate Google cloud capabilities, Gen AI & Python models with SAP solutions (e.g. SAP PaPM) into the global platform enabling DB's financials modelling for cost- and revenue projectionsYou will work together with senior SAP engineering colleagues on an integrated high-quality solution into existing processes and software solutions for our Finance and Business customers up to Management Board of DBInteraction and collaboration with the technical architects and engineers to jointly strive for the best-in-class solutionsEnsuring reliability, resiliency and reusability of deliverables by designing strategic solutions leveraging the CI / CT / CD framework including automated unit testing, performance testing, post-go live validation and checks throughout the entire life cycle of the deliveryYou will also support the ITAO with audit issues, policies and standards fulfillment as well as the definition of compliance issues and compliance with regulatory standards in the companyYour skills and experiencesDegree from a recognized university with a focus on IT or business administration or comparable training/professional experience (bank clerk desirable)Profound professional experience and track record in the designing and programming of large scale & complex software solutions in some of the SAP products such as: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI and Planning, SAP HANA, BW/4HANA or developing new solutions & maintaining our large ABAP code base supporting various key processesModelling skills leveraging AI / ML for financials data are advantageousExperience as an IT Application Owner or IT Application Owner delegate and the methods used in the bank is desirableDesirable experience in certain areas like: SAP BTP, DataSphere and SAP's Gen AI products; design and software development of integrated reporting solutions such as SAC BI, SAP Business Objects, Tableau or SAP SACBeneficial to have experience in agile development methods including DevOps concepts; experience in Google cloud services such as Vertex or Cortex framework, Python, JSON, .Net or TableauTeam player collaborating in a global & diverse teamCustomer and strategic solution orientationSupport the continuous learning and open feedback culture in the teamsFluent English language skills; German language skills are desirable
"""
    
    # Expected SAP technologies that should be extracted
    expected_sap_technologies = [
        'SAP ABAP', 'ABAP', 'SAP HANA', 'HANA', 'SAP BPC', 'BPC', 'SAP SAC', 'SAC', 
        'SAP BTP', 'BTP', 'SAP PaPM', 'PaPM', 'SAP BCS', 'BCS', 'BW/4HANA', 
        'DataSphere', 'Fiori', 'SAP Business Objects', 'DevOps', 'CI/CD',
        'Google Cloud', 'Vertex', 'Cortex', 'JSON', '.Net'
    ]
    
    current_extraction = "Programming: PYTHON; Programming: GO; Programming: R; Database: SQL; Analytics: tableau (+2 more)"
    
    print("=== SAP ABAP Engineer Job Analysis ===")
    print(f"Current daily report extraction: {current_extraction}")
    print(f"Expected SAP technologies: {', '.join(expected_sap_technologies)}")
    print("\nTechnologies found in job description:")
    
    found_technologies = []
    for tech in expected_sap_technologies:
        if re.search(tech, sap_job_description, re.IGNORECASE):
            found_technologies.append(tech)
            print(f"  ✓ {tech}")
    
    missing_from_extraction = [tech for tech in found_technologies if tech.lower() not in current_extraction.lower()]
    print(f"\nCRITICAL: Missing from extraction: {', '.join(missing_from_extraction)}")
    
    return sap_job_description, found_technologies

def test_sales_job_extraction():
    """Test extraction on the Sales Specialist job that incorrectly shows programming languages"""
    
    sales_job_description = """
Institutional Cash and Trade Sales Specialist (Client Sales Manager) – DACHLIE (f/m/x) Job ID:R0339981 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-04-01 Location: Frankfurt Position Overview Über den BereichInstitutional Cash and Trade (ICT) ist eine dynamische globale Organisation, die aus verschiedenen Deutsche Bank Corporate Bank Lokationen Institutional Cash Management und Trade Finance Dienstleistungen für Banken anbietet. Wir suchen einen Sales Spezialisten (Client Sales Manager) für die ICT DACHLIE Region, welche Deutschland, Schweiz, Österreich und Liechtenstein einschließt. Als ICT Sales Spezialist werden Sie für Banken in diesen Ländern zuständig sein. Ihre AufgabenErfüllen der Sales Ziele in Ihrem Portfolio und qualitative hochstehende Betreuung der bestehenden KundenSie verstehen den Risikoappetit von ICT und die Risikoprofile Ihrer bestehenden und potenziellen NeukundenSie benutzen aktiv unsere MIS- und Reporting-Tools für das Management Ihrer NamenSie stellen die Einhaltung aller relevanten DB Group und US Supervision Prozesse sicher und erfüllen alle obligatorischen Trainings und risikorelevanten Aufgaben pünktlich und zuverlässigSie entwickeln Ihr Portfolio aktiv und stehen Ihren Kunden mit Ihrem Know-How proaktiv zur VerfügungIhre Fähigkeiten und ErfahrungSie haben mehrjährige Erfahurng im Correspondent Banking bei einer größeren europäischen oder amerikanischen BankSie besitzen Produktkenntnisse in den Bereichen Cash Management (internationaler, grenzüberschreitender Zahlungsverkehr, Liquiditätsteuerung für Banken) und im Trade FinanceSie überzeugen mit Ihren Fähigkeiten zum Präsentieren um sowohl schriftlich als auch mündlich unsere Strategie, Produkte und unseren Risikoappetit zu repräsentierenSie sind eine kundenorientierte Persönlichkeit, die Wert auf langfristige Partnerschaften legt und Mehrwert für den Kunden schafftSie können fliessend in Deutsch und Englisch kommunizieren (schriftlich & mündlich)
Your key responsibilitiesTo deliver on the agreed Sales objectives for the client portfolio and to uphold best in class client management and service levels to the existing client baseObtain full background knowledge on the clients and ensure client-adoptions in line with the current KYC policy before on-boardingMonitor revenue trends via various reporting tools like Salesforce and dbTableauFulfill responsibilities under the DB Group and US Supervision policies and the Written Supervisory ProceduresEnsure timely completion of Mandatory Trainings and compliance with all risk-related obligations (non-financial risk, financial risk, timely completion of Periodic Review to reflect up-to-date and accurate information)Your skills and experiencesThe successful candidate should have several years of correspondent banking industry experience, including employment in a major European or US financial institution, and will have been educated to degree levelSound product knowledge of cash management and trade products and services for financial institutions (USD, EUR and Multicurrency clearing and payment services, liquidity management, transactional F/X, trade finance for financial institutions)Solid presentation and communication skills in German and English, written and oral - ability to communicate bank's strategy, as well as the ICM global business strategy incl. specifically the ICM risk appetite and respective policiesAbility to build and develop contacts at the appropriate level in target clients to support business traction. Strong negotiation skills essentialFluency in written and spoken German and English required
"""
    
    current_extraction = "Programming: GO; Programming: R; Analytics: tableau; CRM: salesforce"
    
    print("\n=== Sales Specialist Job Analysis ===")
    print(f"Current daily report extraction: {current_extraction}")
    print("This is WRONG - it's a sales role, not programming!")
    
    # Look for actual relevant technologies
    relevant_sales_tech = ['Salesforce', 'dbTableau', 'Tableau', 'CRM', 'MIS', 'KYC']
    programming_langs = ['GO', 'R', 'Python', 'Java', 'C++']
    
    print("\nActual relevant technologies for sales role:")
    for tech in relevant_sales_tech:
        if re.search(tech, sales_job_description, re.IGNORECASE):
            print(f"  ✓ {tech}")
    
    print("\nIncorrectly extracted programming languages:")
    for lang in programming_langs:
        if lang.lower() in current_extraction.lower():
            print(f"  ❌ {lang} (should NOT be extracted for sales role)")
    
    return sales_job_description

def analyze_german_vs_english_sections():
    """Analyze extraction differences between German and English sections"""
    
    print("\n=== German vs English Language Analysis ===")
    
    # Sample German text with technical terms
    german_tech_text = """
    Fundierte Berufserfahrung in der Entwicklung und Programmierung großer und komplexer Softwarelösungen in SAP-Produkten wie: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI und Planung, SAP HANA, BW/4HANA, respektive die Entwicklung neuer Lösungen und die Pflege einer großen ABAP-Codebasis zur Unterstützung verschiedener Kernprozesse der Bank
    """
    
    # Equivalent English text
    english_tech_text = """
    Profound professional experience and track record in the designing and programming of large scale & complex software solutions in some of the SAP products such as: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI and Planning, SAP HANA, BW/4HANA or developing new solutions & maintaining our large ABAP code base supporting various key processes
    """
    
    print("German technical terms found:")
    german_terms = re.findall(r'SAP [A-Z]+|ABAP|HANA|BPC|SAC|PaPM|BCS|BW/4HANA', german_tech_text)
    for term in german_terms:
        print(f"  ✓ {term}")
    
    print("\nEnglish technical terms found:")
    english_terms = re.findall(r'SAP [A-Z]+|ABAP|HANA|BPC|SAC|PaPM|BCS|BW/4HANA', english_tech_text)
    for term in english_terms:
        print(f"  ✓ {term}")
    
    print(f"\nBoth sections contain the same technical terms!")
    print("The issue is likely in the LLM's language understanding or extraction logic.")

def test_v3_3_specialist():
    """Test if we can import and use the v3.3 specialist directly"""
    
    print("\n=== Testing ContentExtractionSpecialist v3.3 ===")
    
    try:
        from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialist
        
        specialist = ContentExtractionSpecialist()
        
        # Get SAP job description
        sap_job_description, _ = test_sap_job_extraction()
        
        print("Testing v3.3 specialist on SAP job...")
        result = specialist.extract_technical_requirements(
            sap_job_description,
            position_title="Senior SAP ABAP Engineer – Group General Ledger"
        )
        
        print(f"v3.3 specialist result: {result}")
        
        return result
        
    except ImportError as e:
        print(f"ERROR: Cannot import v3.3 specialist: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Exception in v3.3 specialist: {e}")
        return None

def main():
    """Run complete diagnosis of the German language extraction crisis"""
    
    print("🚨 CRITICAL DIAGNOSIS: German Language Technical Requirements Extraction Crisis")
    print("=" * 80)
    
    # Test problematic jobs
    sap_job_desc, sap_technologies = test_sap_job_extraction()
    sales_job_desc = test_sales_job_extraction()
    
    # Analyze language differences
    analyze_german_vs_english_sections()
    
    # Test v3.3 specialist directly
    v3_3_result = test_v3_3_specialist()
    
    print("\n" + "=" * 80)
    print("🔍 DIAGNOSIS SUMMARY:")
    print("=" * 80)
    
    print("\n1. SAP ABAP Engineer Job Issues:")
    print("   - Job clearly mentions: SAP HANA, ABAP, BPC, SAC, BTP, PaPM, BCS, etc.")
    print("   - Daily report only extracted: Python, GO, R, SQL, Tableau")
    print("   - CRITICAL: Missing all SAP-specific technologies")
    
    print("\n2. Sales Specialist Job Issues:")
    print("   - Job is for sales role with Salesforce, Tableau for reporting")
    print("   - Daily report incorrectly extracted: GO, R programming languages")
    print("   - CRITICAL: Wrong technical categorization")
    
    print("\n3. Language Analysis:")
    print("   - Both German and English sections contain identical technical terms")
    print("   - Issue is NOT German language parsing")
    print("   - Issue is likely in extraction logic or LLM prompting")
    
    if v3_3_result:
        print(f"\n4. v3.3 Specialist Test:")
        print(f"   - v3.3 specialist extracted: {v3_3_result}")
        print("   - Compare this with daily report extraction")
    else:
        print("\n4. v3.3 Specialist Test:")
        print("   - Could not test v3.3 specialist directly")
        print("   - This suggests integration or import issues")
    
    print("\n🎯 RECOMMENDED ACTIONS:")
    print("1. Verify daily report generator is using v3.3 specialist correctly")
    print("2. Check if v3.3 specialist prompt needs German language improvements")
    print("3. Test v3.3 on mixed German/English content")
    print("4. Implement domain-specific technical term recognition")
    print("5. Add SAP ecosystem technology mapping")
    
    return {
        'sap_missing_technologies': sap_technologies,
        'sales_incorrect_extraction': True,
        'v3_3_test_result': v3_3_result
    }

if __name__ == "__main__":
    main()
