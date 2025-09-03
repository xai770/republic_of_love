#!/usr/bin/env python3
"""
Technical Requirements Extraction DEBUG Test
===========================================

Testing v3.3 specialist directly against the jobs from the daily report
to identify if the issue is with the specialist or the integration.

Focus: Compare v3.3 results vs daily report extraction results
"""

import sys
import time
import json

# Add the path to the v3.3 specialist
specialist_path = "/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_crisis_resolution_20250702"
sys.path.append(specialist_path)

try:
    from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33
    print("✅ Successfully imported ContentExtractionSpecialistV33")
except ImportError as e:
    print(f"❌ Failed to import ContentExtractionSpecialistV33: {e}")
    sys.exit(1)

def test_job_1_data_analyst():
    """Test Job #1: Business Product Senior Analyst (Data Analytics)"""
    print("\n" + "="*80)
    print("🔧 TESTING JOB #1: Business Product Senior Analyst (Data Analytics)")
    print("="*80)
    
    raw_job = """Business Product Senior Analyst (d/m/w) – Sales Campaign Management BizBanking (Data Analytics) Job ID:R0363090 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-20 Location: Frankfurt Position Overview Über den BereichDie Deutsche BizBanking als Teil der Unternehmensbank bündelt unser Angebot für unsere Geschäftskunden - vom selbständigen Freiberufler bis zum größeren Geschäftskunden - der drei Marken Deutsche Bank, Postbank und FYRST unter einem gemeinsamen Dach. Für die Deutsche Bank ist das Geschäftsfeld ein strategischer Wachstumsbereich.Das Team Sales Campaign Management als Teil des Sales & Process Management BizBanking ist verantwortlich für die Entwicklung und Steuerung der Vertriebskampagnen in BizBanking in enger Zusammenarbeit mit seinen Stakeholdern aus Digital Client Solutions (DCS), den Vertriebsverantwortlichen sowie weiteren zentralen Bereichen.Ihre AufgabenMitgestaltung der vertrieblichen Wachstumsagenda für den stationären Vertrieb in BizBanking für die Marken Deutsche Bank und PostbankDurchführung von Voranalysen zur Identifikation und Entwicklung geeigneter Vertriebsimpulse in Abstimmung mit den relevanten Vertriebs- und ProduktbereichenVerantwortliche Konzeption & Programmierung von Datenselektionen für ausgewählte Vertriebskampagnen sowie Bereitstellung in CRM- & Kampagnen-Tools in enger Zusammenarbeit mit den verantwortlichen ZentralbereichenMitarbeit in der Weiterentwicklung der Vertriebsaktivitäten-Steuerung in Client Relationship Management- & Kampagnen-Tools, datenanalytischer Vertriebsimpulse sowie Verknüpfung mit digitalen Leads gemeinsam mit den relevanten StakeholdernIhre Fähigkeiten und ErfahrungenErfahrung im Bankenumfeld sowie abgeschlossenes (Wirtschaftsinformatik) Studium (BA/FH/Universität), abgeschlossener Bankausbildung oder vergleichbare kaufmännische Ausbildung mit sehr gutem AbschlussFundierte Kenntnisse in IT, Datenmanagement und Digitalisierung, hohe Affinität komplexe Datenthemen zu begleiten und Erfahrungen im Umgang mit großen, teils unstrukturierten Datenpools auf unterschiedlichen PlattformenBeherrschung von Programmiersprachen (u.a. SAS, SQL, Python) auf hohem Niveau und gute Kenntnis gängiger Analytics-Tools wie auch Campaigns-Tech Stacks (z.B. Adobe)Analytisches und konzeptionelles Denkvermögen sowie starke Eigeninitiative und LösungsorientierungSehr gute Deutsch- und Englischkenntnisse in Wort und SchriftWas wir Ihnen bietenWir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und persönlichen Bedürfnisse abdecken.Emotional ausgeglichenEine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern – beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur Förderung mentaler Gesundheit.Körperlich fitMit Angeboten zur Aufrechterhaltung Ihrer persönlichen Gesundheit und einem förderlichen beruflichen Umfeld hilft Ihnen die Bank, körperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensführung.Sozial vernetztDer Austausch mit anderen eröffnet uns neue Perspektiven, bringt uns beruflich wie persönlich voran und stärkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterstützung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe.Finanziell abgesichertDie Bank sichert Sie nicht nur während Ihrer aktiven Karriere, sondern auch für die Zukunft finanziell ab und unterstützt Ihre Flexibilität sowie Mobilität – egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragsplänen für Altersvorsorge, Bankdienstleistungen für Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket.Da die Benefits je nach Standort geringfügig variieren, gehen Sie bitte bei konkreten Fragen auf Ihre Recruiter / Ihre Recruiterin zu.Die Stelle wird in Voll- und in Teilzeit angeboten.Bei Fragen zum Rekrutierungsprozess steht Ihnen Kerstin Nörber gerne zur Verfügung.Kontakt Kerstin Nörber: 069-910-22155 Wir streben eine Unternehmenskultur an, in der wir gemeinsam jeden Tag das Beste geben. Dazu gehören verantwortungsvolles Handeln, wirtschaftliches Denken, Initiative ergreifen und zielgerichtete Zusammenarbeit.Gemeinsam teilen und feiern wir die Erfolge unserer Mitarbeiter*innen. Gemeinsam sind wir die Deutsche Bank Gruppe.Wir begrüßen Bewerbungen von allen Menschen und fördern ein positives, faires und integratives Arbeitsumfeld."""
    
    print("📋 DAILY REPORT CLAIMS:")
    print("Technical Requirements: SAS (programming, advanced); SQL (programming, advanced); Python (programming, advanced); CRM (tool, intermediate); Adobe (tool, advanced)")
    print()
    
    print("🎯 EXPECTED TECHNICAL SKILLS FROM JOB TEXT:")
    print("- SAS ✅ (explicitly mentioned)")
    print("- SQL ✅ (explicitly mentioned)")  
    print("- Python ✅ (explicitly mentioned)")
    print("- Analytics-Tools ❌ (missing from daily report)")
    print("- Campaigns-Tech Stacks ❌ (missing from daily report)")
    print("- IT/Datenmanagement ❌ (missing from daily report)")
    print("- Adobe ✅ (mentioned as example)")
    print("- CRM Tools ✅ (explicitly mentioned)")
    print()
    
    print("🔄 TESTING v3.3 SPECIALIST...")
    specialist = ContentExtractionSpecialistV33()
    
    start_time = time.time()
    result = specialist.extract_skills(raw_job)
    end_time = time.time()
    
    print(f"⏱️ Processing Time: {end_time - start_time:.2f} seconds")
    print()
    
    print("🔧 v3.3 TECHNICAL SKILLS RESULTS:")
    if result.technical_skills:
        for skill in result.technical_skills:
            print(f"  ✅ {skill}")
    else:
        print("  ❌ No technical skills found")
    print()
    
    print("📊 v3.3 ALL SKILLS:")
    if result.all_skills:
        for skill in result.all_skills:
            print(f"  • {skill}")
        print(f"\n📈 Total: {len(result.all_skills)} skills")
    
    # Compare with expected
    expected_tech = ["SAS", "SQL", "Python", "Analytics-Tools", "Campaigns-Tech Stacks", "CRM", "Adobe"]
    print(f"\n🔍 COMPARISON ANALYSIS:")
    print("=" * 50)
    
    found_count = 0
    for expected in expected_tech:
        found = any(expected.lower() in skill.lower() for skill in result.all_skills)
        if found:
            found_count += 1
            print(f"✅ {expected} - FOUND")
        else:
            print(f"❌ {expected} - MISSING")
    
    accuracy = (found_count / len(expected_tech)) * 100
    print(f"\n📈 v3.3 Accuracy: {accuracy:.1f}% ({found_count}/{len(expected_tech)})")
    
    return result

def test_job_2_network_security():
    """Test Job #2: Senior Engineer – Network Security Deployment"""
    print("\n" + "="*80)
    print("🔧 TESTING JOB #2: Senior Engineer - Network Security Deployment")
    print("="*80)
    
    raw_job = """Senior Engineer (f/m/x) – Network Security Deployment Job ID:R0385218 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-23 Location: Frankfurt Position Overview Bereich & TeamDas Team „Network Security Deployment" innerhalb des Bereichs TDI/GNS/Networks ist dafür verantwortlich, den Security-relevanten Bereich des Deutsche Bank Netzwerkes zu erweitern und nach Bedarf der Businessbereiche auszubauen und an die Anforderungen von internen und externen Regularien anzupassen.AufgabenbeschreibungZusammenarbeit in einem internationalen Team, das für alle sämtliche Security-Bereiche innerhalb des Netzwerkes zuständig istDeployment von sämtlichen Technologien (Router, Switche, Firewall, Proxy, etc.)Gemeinsames Erarbeiten von kundenspezifischen Lösungen mit den entsprechenden Engineering-Gruppen innerhalb von TDI/GNS/NetworksInbetriebnahme, Test, Übergabe an den Betrieb; Troubleshooting der Security-UmgebungImplementierung von Regelwerken auf Firewall/ProxySicherstellung von End-of-Life sowie Tech Road ComplianceAnforderungsprofilErfolgreich abgeschlossenes Studium im Bereich Informatik oder vergleichbare BerufserfahrungFachliche Kenntnisse im Bereich Netzwerk (Layer2/3, Routing und Switching); Netzwerk Security (Firewall, Proxy); CloudVertrautheit mit regulatorischen Anforderungen an die ITStarke analytische Fähigkeiten, ein lösungsorientierter Arbeitsstil verbunden mit einer ausgeprägten KommunikationsstärkeSichere Englisch- und Deutschkenntnisse in Wort und SchriftWas wir Ihnen bietenWir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und persönlichen Bedürfnisse abdecken.Emotional ausgeglichenEine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern – beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur Förderung mentaler Gesundheit.Körperlich fitMit Angeboten zur Aufrechterhaltung Ihrer persönlichen Gesundheit und einem förderlichen beruflichen Umfeld hilft Ihnen die Bank, körperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensführung.Sozial vernetztDer Austausch mit anderen eröffnet uns neue Perspektiven, bringt uns beruflich wie persönlich voran und stärkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterstützung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe.Finanziell abgesichertDie Bank sichert Sie nicht nur während Ihrer aktiven Karriere, sondern auch für die Zukunft finanziell ab und unterstützt Ihre Flexibilität sowie Mobilität – egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragsplänen für Altersvorsorge, Bankdienstleistungen für Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket.Da die Benefits je nach Standort geringfügig variieren, gehen Sie bitte bei konkreten Fragen auf Ihre Recruiterin zu.Die Stelle wird in Voll- und in Teilzeit angeboten.Bei Fragen zum Rekrutierungsprozess steht Ihnen Michaela Peschke gerne zur Verfügung.Kontakt Michaela Peschke: +49 69 91043951*********************************************************************************Department & Team The "Network Security Deployment" team within the TDI/GNS/Networks department is responsible for expanding the security-relevant areas of the Deutsche Bank network, expanding them as needed by the business units, and adapting them to the requirements of internal and external regulations.Job descriptionCollaboration in an international team that is responsible for all security areas within the networkDeployment of all technologies (routers, switches, firewalls, proxies, etc.)Joint development of customer-specific solutions with the relevant engineering groups within TDI/GNS/NetworksCommissioning, testing, handover to operations, and troubleshooting of the security environmentImplementation of firewall/proxy policyEnsuring end-of-life and tech road complianceRequirements profileSuccessfully completed studies in computer science or comparable professional experienceTechnical knowledge in the area of ​​network (Layer 2/3, routing and switching); network security (firewall, proxy); cloudFamiliarity with regulatory requirements for ITStrong analytical skills, a solution-oriented working style combined with strong communication skillsFluent written and spoken English and GermanWhat we offerWe provide you with a comprehensive portfolio of benefits and offerings to support both, your private and professional needs.Emotionally and mentally balancedA positive mind helps us master the challenges of everyday life – both professionally and privately. We offer consultation in difficult life situations as well as mental health awareness trainings.Physically thrivingWe support you in staying physically fit through an offering to maintain personal health and a professional environment. You can benefit from health check-ups; vaccination drives as well as advice on healthy living and nutrition.Socially connectedNetworking opens up new perspectives, helps us thrive professionally and personally as well as strengthens our self-confidence and well-being. You can benefit from PME family service, FitnessCenter Job, flexible working (e.g parttime, hybrid working, job tandem) as well as an extensive culture of diversity, equity and inclusion.Financially secureWe provide you with financial security not only during your active career but also for the future. You can benefit from offerings such as pension plans, banking services, company bicycle or "Deutschlandticket".Since our offerings slightly vary across locations, please contact your recruiter with specific questions.This job is available in full and parttime.In case of any recruitment related questions, please get in touch with Michaela Peschke.Contact Michaela Peschke: +49 69 91043951 Wir streben eine Unternehmenskultur an, in der wir gemeinsam jeden Tag das Beste geben. Dazu gehören verantwortungsvolles Handeln, wirtschaftliches Denken, Initiative ergreifen und zielgerichtete Zusammenarbeit.Gemeinsam teilen und feiern wir die Erfolge unserer Mitarbeiter*innen. Gemeinsam sind wir die Deutsche Bank Gruppe.Wir begrüßen Bewerbungen von allen Menschen und fördern ein positives, faires und integratives Arbeitsumfeld."""
    
    print("📋 DAILY REPORT CLAIMS:")
    print("Technical Requirements: Firewall (security, intermediate); Router (network, intermediate); Proxy (network, intermediate)")
    print()
    
    print("🎯 EXPECTED TECHNICAL SKILLS FROM JOB TEXT:")
    print("- Router ✅ (explicitly mentioned)")
    print("- Switches ❌ (missing from daily report)")  
    print("- Firewall ✅ (explicitly mentioned)")
    print("- Proxy ✅ (explicitly mentioned)")
    print("- Layer 2/3 ❌ (missing from daily report)")
    print("- Routing and Switching ❌ (missing from daily report)")
    print("- Network Security ❌ (missing from daily report)")
    print("- Cloud ❌ (missing from daily report)")
    print()
    
    print("🔄 TESTING v3.3 SPECIALIST...")
    specialist = ContentExtractionSpecialistV33()
    
    start_time = time.time()
    result = specialist.extract_skills(raw_job)
    end_time = time.time()
    
    print(f"⏱️ Processing Time: {end_time - start_time:.2f} seconds")
    print()
    
    print("🔧 v3.3 TECHNICAL SKILLS RESULTS:")
    if result.technical_skills:
        for skill in result.technical_skills:
            print(f"  ✅ {skill}")
    else:
        print("  ❌ No technical skills found")
    print()
    
    print("📊 v3.3 ALL SKILLS:")
    if result.all_skills:
        for skill in result.all_skills:
            print(f"  • {skill}")
        print(f"\n📈 Total: {len(result.all_skills)} skills")
    
    # Compare with expected
    expected_tech = ["Router", "Switches", "Firewall", "Proxy", "Layer 2/3", "Routing", "Switching", "Network Security", "Cloud"]
    print(f"\n🔍 COMPARISON ANALYSIS:")
    print("=" * 50)
    
    found_count = 0
    for expected in expected_tech:
        found = any(expected.lower() in skill.lower() for skill in result.all_skills)
        if found:
            found_count += 1
            print(f"✅ {expected} - FOUND")
        else:
            print(f"❌ {expected} - MISSING")
    
    accuracy = (found_count / len(expected_tech)) * 100
    print(f"\n📈 v3.3 Accuracy: {accuracy:.1f}% ({found_count}/{len(expected_tech)})")
    
    return result

def main():
    print("🔧 TECHNICAL REQUIREMENTS EXTRACTION DEBUG TEST")
    print("=" * 80)
    print("🎯 Goal: Test v3.3 specialist vs daily report extraction results")
    print("🔍 Focus: Identify if issue is with specialist or integration")
    print()
    
    # Test both jobs
    job1_result = test_job_1_data_analyst()
    job2_result = test_job_2_network_security()
    
    print("\n" + "="*80)
    print("🏁 FINAL DIAGNOSIS")
    print("="*80)
    
    print("📊 SUMMARY:")
    print(f"Job #1 (Data Analyst): {len(job1_result.all_skills)} total skills found")
    print(f"Job #2 (Network Security): {len(job2_result.all_skills)} total skills found")
    print()
    
    print("🔍 ISSUES IDENTIFIED:")
    print("1. Compare v3.3 results with daily report results")
    print("2. Identify missing technical skills")
    print("3. Determine if problem is specialist or integration")
    print()
    
    print("💡 NEXT STEPS:")
    print("- If v3.3 finds more skills than daily report: INTEGRATION ISSUE")
    print("- If v3.3 misses skills too: SPECIALIST NEEDS IMPROVEMENT")
    print("- Check which extraction system daily report actually uses")

if __name__ == "__main__":
    main()
