#!/usr/bin/env python3
"""
Content Extraction Specialist v3.3 - Real Data Validation Test
==============================================================

Testing the v3.3 specialist with actual job data from the daily report.
Focus: Validating concise job description extraction and skill identification.

Input: Raw job description from Job #1 (Deutsche Bank Business Product Senior Analyst)
Expected Output: Clean, concise job description suitable for matching system
"""

import sys
import os
from pathlib import Path
import time

# Add the path to the v3.3 specialist
specialist_path = "/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_crisis_resolution_20250702"
sys.path.append(specialist_path)

try:
    from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33
    print("✅ Successfully imported ContentExtractionSpecialistV33")
except ImportError as e:
    print(f"❌ Failed to import ContentExtractionSpecialistV33: {e}")
    sys.exit(1)

def main():
    print("🔧 CONTENT EXTRACTION SPECIALIST v3.3 - REAL DATA VALIDATION")
    print("=" * 70)
    
    # Raw job data from daily report Job #1
    raw_job_description = """Business Product Senior Analyst (d/m/w) – Sales Campaign Management BizBanking (Data Analytics) Job ID:R0363090 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-20 Location: Frankfurt Position Overview Über den BereichDie Deutsche BizBanking als Teil der Unternehmensbank bündelt unser Angebot für unsere Geschäftskunden - vom selbständigen Freiberufler bis zum größeren Geschäftskunden - der drei Marken Deutsche Bank, Postbank und FYRST unter einem gemeinsamen Dach. Für die Deutsche Bank ist das Geschäftsfeld ein strategischer Wachstumsbereich.Das Team Sales Campaign Management als Teil des Sales & Process Management BizBanking ist verantwortlich für die Entwicklung und Steuerung der Vertriebskampagnen in BizBanking in enger Zusammenarbeit mit seinen Stakeholdern aus Digital Client Solutions (DCS), den Vertriebsverantwortlichen sowie weiteren zentralen Bereichen.Ihre AufgabenMitgestaltung der vertrieblichen Wachstumsagenda für den stationären Vertrieb in BizBanking für die Marken Deutsche Bank und PostbankDurchführung von Voranalysen zur Identifikation und Entwicklung geeigneter Vertriebsimpulse in Abstimmung mit den relevanten Vertriebs- und ProduktbereichenVerantwortliche Konzeption & Programmierung von Datenselektionen für ausgewählte Vertriebskampagnen sowie Bereitstellung in CRM- & Kampagnen-Tools in enger Zusammenarbeit mit den verantwortlichen ZentralbereichenMitarbeit in der Weiterentwicklung der Vertriebsaktivitäten-Steuerung in Client Relationship Management- & Kampagnen-Tools, datenanalytischer Vertriebsimpulse sowie Verknüpfung mit digitalen Leads gemeinsam mit den relevanten StakeholdernIhre Fähigkeiten und ErfahrungenErfahrung im Bankenumfeld sowie abgeschlossenes (Wirtschaftsinformatik) Studium (BA/FH/Universität), abgeschlossener Bankausbildung oder vergleichbare kaufmännische Ausbildung mit sehr gutem AbschlussFundierte Kenntnisse in IT, Datenmanagement und Digitalisierung, hohe Affinität komplexe Datenthemen zu begleiten und Erfahrungen im Umgang mit großen, teils unstrukturierten Datenpools auf unterschiedlichen PlattformenBeherrschung von Programmiersprachen (u.a. SAS, SQL, Python) auf hohem Niveau und gute Kenntnis gängiger Analytics-Tools wie auch Campaigns-Tech Stacks (z.B. Adobe)Analytisches und konzeptionelles Denkvermögen sowie starke Eigeninitiative und LösungsorientierungSehr gute Deutsch- und Englischkenntnisse in Wort und SchriftWas wir Ihnen bietenWir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und persönlichen Bedürfnisse abdecken.Emotional ausgeglichenEine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern – beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur Förderung mentaler Gesundheit.Körperlich fitMit Angeboten zur Aufrechterhaltung Ihrer persönlichen Gesundheit und einem förderlichen beruflichen Umfeld hilft Ihnen die Bank, körperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensführung.Sozial vernetztDer Austausch mit anderen eröffnet uns neue Perspektiven, bringt uns beruflich wie persönlich voran und stärkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterstützung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe.Finanziell abgesichertDie Bank sichert Sie nicht nur während Ihrer aktiven Karriere, sondern auch für die Zukunft finanziell ab und unterstützt Ihre Flexibilität sowie Mobilität – egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragsplänen für Altersvorsorge, Bankdienstleistungen für Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket.Da die Benefits je nach Standort geringfügig variieren, gehen Sie bitte bei konkreten Fragen auf Ihre Recruiter / Ihre Recruiterin zu.Die Stelle wird in Voll- und in Teilzeit angeboten.Bei Fragen zum Rekrutierungsprozess steht Ihnen Kerstin Nörber gerne zur Verfügung.Kontakt Kerstin Nörber: 069-910-22155 Wir streben eine Unternehmenskultur an, in der wir gemeinsam jeden Tag das Beste geben. Dazu gehören verantwortungsvolles Handeln, wirtschaftliches Denken, Initiative ergreifen und zielgerichtete Zusammenarbeit.Gemeinsam teilen und feiern wir die Erfolge unserer Mitarbeiter*innen. Gemeinsam sind wir die Deutsche Bank Gruppe.Wir begrüßen Bewerbungen von allen Menschen und fördern ein positives, faires und integratives Arbeitsumfeld."""

    print("📋 Input Job Data:")
    print(f"Job Title: Business Product Senior Analyst")
    print(f"Original Length: {len(raw_job_description)} characters")
    print(f"Expected Skills: SAS, SQL, Python, Adobe, CRM tools")
    print()

    # Expected extraction from the report analysis
    expected_skills = ["SAS", "SQL", "Python", "CRM", "Adobe"]
    expected_concise_desc = "Develop and manage sales campaigns for BizBanking using data analytics, programming, and CRM tools"
    
    print("📊 Expected Results (from Daily Report):")
    print(f"Technical Skills: {expected_skills}")
    print(f"Concise Description Length: ~150 characters (not the full job description)")
    print()

    # Initialize the v3.3 specialist
    try:
        specialist = ContentExtractionSpecialistV33()
        print("✅ ContentExtractionSpecialist v3.3 initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize specialist: {e}")
        return

    # Run the skill extraction
    print("\n🔄 Running v3.3 skill extraction...")
    try:
        result = specialist.extract_skills(raw_job_description)
        
        print("\n✅ EXTRACTION COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        
        print("\n📋 EXTRACTION RESULTS:")
        print(f"Processing Time: {result.processing_time:.2f} seconds")
        print(f"Model Used: {result.model_used}")
        print(f"Confidence: {result.accuracy_confidence}")
        print()
        
        print("🔧 TECHNICAL SKILLS:")
        if result.technical_skills:
            for skill in result.technical_skills:
                print(f"  • {skill}")
        else:
            print("  ❌ No technical skills extracted")
        print()
        
        print("💼 BUSINESS SKILLS:")
        if result.business_skills:
            for skill in result.business_skills:
                print(f"  • {skill}")
        else:
            print("  ❌ No business skills extracted")
        print()
        
        print("🤝 SOFT SKILLS:")
        if result.soft_skills:
            for skill in result.soft_skills:
                print(f"  • {skill}")
        else:
            print("  ❌ No soft skills extracted")
        print()
        
        print("📊 ALL SKILLS COMBINED:")
        if result.all_skills:
            for skill in result.all_skills:
                print(f"  • {skill}")
            print(f"\nTotal Skills Extracted: {len(result.all_skills)}")
        else:
            print("  ❌ No skills extracted at all")
        
        # Validation against expected results
        print("\n🔍 VALIDATION ANALYSIS:")
        print("=" * 30)
        
        found_expected = 0
        for expected_skill in expected_skills:
            if any(expected_skill.lower() in skill.lower() for skill in result.all_skills):
                found_expected += 1
                print(f"✅ Found expected skill: {expected_skill}")
            else:
                print(f"❌ Missing expected skill: {expected_skill}")
        
        accuracy = (found_expected / len(expected_skills)) * 100 if expected_skills else 0
        print(f"\n📈 Accuracy: {accuracy:.1f}% ({found_expected}/{len(expected_skills)} expected skills found)")
        
        # Issue Analysis
        print("\n🚨 ISSUE ANALYSIS:")
        if accuracy < 80:
            print("❌ CRITICAL: Accuracy below 80% target")
            print("Issues identified:")
            print("  • v3.3 may not be extracting skills correctly")
            print("  • LLM prompts may need refinement")
            print("  • Job content complexity affecting extraction")
        else:
            print("✅ Accuracy meets target threshold")
            
        # Recommendations
        print("\n💡 RECOMMENDATIONS FOR SANDY:")
        if not result.all_skills:
            print("🔥 CRITICAL: Zero skills extracted - possible v3.3 failure")
            print("1. Check LLM model availability and connectivity")
            print("2. Validate prompts and parsing logic")
            print("3. Test with simplified job descriptions")
        elif accuracy < 80:
            print("⚠️  MODERATE: Extraction quality needs improvement")
            print("1. Review v3.3 prompts for German text handling")
            print("2. Enhance skill recognition patterns")
            print("3. Consider fallback extraction strategies")
        else:
            print("✅ v3.3 extraction working as expected")
            print("1. Monitor extraction consistency across job types")
            print("2. Validate integration with matching pipeline")
        
    except Exception as e:
        print(f"\n❌ EXTRACTION FAILED: {e}")
        print("\n🚨 DEBUGGING INFORMATION:")
        print("1. Check if Ollama is running: curl http://localhost:11434/api/tags")
        print("2. Verify model availability: ollama list")
        print("3. Test with simple input first")
        print("4. Check network connectivity and timeout settings")
        
        print("\n💡 IMMEDIATE ACTIONS FOR SANDY:")
        print("1. Validate v3.3 environment setup")
        print("2. Test with minimal job description input")
        print("3. Check extraction specialist error handling")
        print("4. Consider fallback to simpler extraction approach")

if __name__ == "__main__":
    main()
