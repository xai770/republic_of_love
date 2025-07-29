#!/usr/bin/env python3
"""
Content Extraction Specialist v2.0 - Concise Job Description Test
================================================================

Testing the v2.0 specialist with actual job data for concise description generation.
Focus: Validating concise job description extraction for daily report integration.

Input: Raw job description from Job #1 (Deutsche Bank Business Product Senior Analyst)
Expected Output: Concise, structured job description suitable for daily report
"""

import sys
import os
from pathlib import Path
import time

# Add the path to the v2.0 specialist
specialist_path = "/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/inbox/archive/content_extraction_v2_0_current/src"
sys.path.append(specialist_path)

try:
    from content_extraction_specialist_v2 import ContentExtractionSpecialistV2, extract_job_content_v2
    print("✅ Successfully imported ContentExtractionSpecialistV2")
except ImportError as e:
    print(f"❌ Failed to import ContentExtractionSpecialistV2: {e}")
    sys.exit(1)

def main():
    print("🔧 CONTENT EXTRACTION SPECIALIST v2.0 - CONCISE DESCRIPTION TEST")
    print("=" * 70)
    
    # Raw job data from daily report Job #1
    raw_job_description = """Business Product Senior Analyst (d/m/w) – Sales Campaign Management BizBanking (Data Analytics) Job ID:R0363090 Full/Part-Time: Full-time Regular/Temporary: Regular Listed: 2025-06-20 Location: Frankfurt Position Overview Über den BereichDie Deutsche BizBanking als Teil der Unternehmensbank bündelt unser Angebot für unsere Geschäftskunden - vom selbständigen Freiberufler bis zum größeren Geschäftskunden - der drei Marken Deutsche Bank, Postbank und FYRST unter einem gemeinsamen Dach. Für die Deutsche Bank ist das Geschäftsfeld ein strategischer Wachstumsbereich.Das Team Sales Campaign Management als Teil des Sales & Process Management BizBanking ist verantwortlich für die Entwicklung und Steuerung der Vertriebskampagnen in BizBanking in enger Zusammenarbeit mit seinen Stakeholdern aus Digital Client Solutions (DCS), den Vertriebsverantwortlichen sowie weiteren zentralen Bereichen.Ihre AufgabenMitgestaltung der vertrieblichen Wachstumsagenda für den stationären Vertrieb in BizBanking für die Marken Deutsche Bank und PostbankDurchführung von Voranalysen zur Identifikation und Entwicklung geeigneter Vertriebsimpulse in Abstimmung mit den relevanten Vertriebs- und ProduktbereichenVerantwortliche Konzeption & Programmierung von Datenselektionen für ausgewählte Vertriebskampagnen sowie Bereitstellung in CRM- & Kampagnen-Tools in enger Zusammenarbeit mit den verantwortlichen ZentralbereichenMitarbeit in der Weiterentwicklung der Vertriebsaktivitäten-Steuerung in Client Relationship Management- & Kampagnen-Tools, datenanalytischer Vertriebsimpulse sowie Verknüpfung mit digitalen Leads gemeinsam mit den relevanten StakeholdernIhre Fähigkeiten und ErfahrungenErfahrung im Bankenumfeld sowie abgeschlossenes (Wirtschaftsinformatik) Studium (BA/FH/Universität), abgeschlossener Bankausbildung oder vergleichbare kaufmännische Ausbildung mit sehr gutem AbschlussFundierte Kenntnisse in IT, Datenmanagement und Digitalisierung, hohe Affinität komplexe Datenthemen zu begleiten und Erfahrungen im Umgang mit großen, teils unstrukturierten Datenpools auf unterschiedlichen PlattformenBeherrschung von Programmiersprachen (u.a. SAS, SQL, Python) auf hohem Niveau und gute Kenntnis gängiger Analytics-Tools wie auch Campaigns-Tech Stacks (z.B. Adobe)Analytisches und konzeptionelles Denkvermögen sowie starke Eigeninitiative und LösungsorientierungSehr gute Deutsch- und Englischkenntnisse in Wort und SchriftWas wir Ihnen bietenWir bieten eine breite Palette von Leistungen, die all Ihre beruflichen und persönlichen Bedürfnisse abdecken.Emotional ausgeglichenEine positive Haltung hilft uns, die Herausforderungen des Alltags zu meistern – beruflich wie privat. Profitieren Sie von Angeboten wie Beratung in schwierigen Lebenssituationen und Angeboten zur Förderung mentaler Gesundheit.Körperlich fitMit Angeboten zur Aufrechterhaltung Ihrer persönlichen Gesundheit und einem förderlichen beruflichen Umfeld hilft Ihnen die Bank, körperlich fit zu bleiben. Profitieren Sie von Angeboten wie umfangreichen Check-up Untersuchungen, Impfangeboten und Beratung zur gesunden Lebensführung.Sozial vernetztDer Austausch mit anderen eröffnet uns neue Perspektiven, bringt uns beruflich wie persönlich voran und stärkt unser Selbstvertrauen und Wohlbefinden. Profitieren Sie von Angeboten wie Unterstützung durch den pme Familienservice, das FitnessCenter Job, flexible Arbeitszeitmodelle (bspw. Teilzeit, Jobtandem, hybrides Arbeiten) sowie einer umfangreichen Kultur der Vielfalt, Chancengleichheit und Teilhabe.Finanziell abgesichertDie Bank sichert Sie nicht nur während Ihrer aktiven Karriere, sondern auch für die Zukunft finanziell ab und unterstützt Ihre Flexibilität sowie Mobilität – egal ob privat oder beruflich. Profitieren Sie von Angeboten wie Beitragsplänen für Altersvorsorge, Bankdienstleistungen für Mitarbeiter*innen, Firmenfahrrad oder dem Deutschlandticket.Da die Benefits je nach Standort geringfügig variieren, gehen Sie bitte bei konkreten Fragen auf Ihre Recruiter / Ihre Recruiterin zu.Die Stelle wird in Voll- und in Teilzeit angeboten.Bei Fragen zum Rekrutierungsprozess steht Ihnen Kerstin Nörber gerne zur Verfügung.Kontakt Kerstin Nörber: 069-910-22155 Wir streben eine Unternehmenskultur an, in der wir gemeinsam jeden Tag das Beste geben. Dazu gehören verantwortungsvolles Handeln, wirtschaftliches Denken, Initiative ergreifen und zielgerichtete Zusammenarbeit.Gemeinsam teilen und feiern wir die Erfolge unserer Mitarbeiter*innen. Gemeinsam sind wir die Deutsche Bank Gruppe.Wir begrüßen Bewerbungen von allen Menschen und fördern ein positives, faires und integratives Arbeitsumfeld."""

    print("📋 Input Job Data:")
    print(f"Job Title: Business Product Senior Analyst")
    print(f"Original Length: {len(raw_job_description)} characters")
    print()

    # Current concise description from daily report (problematic)
    current_concise_desc = """Business Product Senior Analyst (d/m/w) – Sales Campaign Management BizBanking (Data Analytics)
Job Responsibilities:
* Mitgestaltung der vertrieblichen Wachstumsagenda für den stationären Vertrieb in BizBanking
* Durchführung von Voranalysen zur Identifikation und Entwicklung geeigneter Vertriebsimpulse
* Konzeption & Programmierung von Datenselektionen für ausgewählte Vertriebskampagnen
* Mitarbeit in der Weiterentwicklung der Vertriebsaktivitäten-Steuerung in Client Relationship Management- & Kampagnen-Tools
Required Skills and Qualifications:
* Erfahrung im Bankenumfeld und abgeschlossenes (Wirtschaftsinformatik) Studium (BA/FH/Universität)
* Abgeschlossener Bankausbildung oder vergleichbare kaufmännische Ausbildung mit sehr gutem Abschluss
* Fundierte Kenntnisse in IT, Datenmanagement und Digitalisierung
* Beherrschung von Programmiersprachen (u.a. SAS, SQL, Python) auf hohem Niveau
* Gute Kenntnis gängiger Analytics-Tools wie auch Campaigns-Tech Stacks (z.B. Adobe)
* Analytisches und konzeptionelles Denkvermögen sowie starke Eigeninitiative und Lösungsorientierung
Essential Experience and Education Requirements:
* Erfahrung im Umgang mit großen, teils unstrukturierten Datenpools auf unterschiedlichen Plattformen
* Sehr gute Deutsch- und Englischkenntnisse in Wort und Schrift"""
    
    print("❌ CURRENT PROBLEMATIC 'Concise' Description:")
    print(f"Length: {len(current_concise_desc)} characters (still very long!)")
    print(f"Issues: Contains full responsibilities, too detailed, not truly 'concise'")
    print()
    
    expected_concise_desc = "Data analyst role developing sales campaigns for Deutsche Bank's business banking, using SAS/SQL/Python for data analysis and CRM campaign management."
    print("✅ EXPECTED Concise Description:")
    print(f"Target: ~{len(expected_concise_desc)} characters")
    print(f"Example: {expected_concise_desc}")
    print()

    # Initialize the v2.0 specialist
    try:
        specialist = ContentExtractionSpecialistV2()
        print("✅ ContentExtractionSpecialist v2.0 initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize specialist: {e}")
        return

    # Run the content extraction (this should generate a concise description)
    print("\n🔄 Running v2.0 content extraction...")
    try:
        result = specialist.extract_core_content(raw_job_description, "test_job_1")
        
        print("\n✅ EXTRACTION COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        
        print("\n📋 EXTRACTION RESULTS:")
        print(f"Processing Time: {result.llm_processing_time:.2f} seconds")
        print(f"Model Used: {result.model_used}")
        print(f"Original Length: {result.original_length} characters")
        print(f"Extracted Length: {result.extracted_length} characters")
        print(f"Reduction: {result.reduction_percentage:.1f}%")
        print()
        
        print("📄 EXTRACTED CONTENT (Concise Description):")
        print("=" * 50)
        print(result.extracted_content)
        print("=" * 50)
        
        # Analysis for daily report integration
        print("\n🔍 DAILY REPORT INTEGRATION ANALYSIS:")
        print("=" * 40)
        
        # Check if content is truly concise
        if result.extracted_length <= 500:
            print("✅ GOOD: Content is concise enough for daily report")
        elif result.extracted_length <= 1000:
            print("⚠️  MODERATE: Content could be more concise")
        else:
            print("❌ PROBLEM: Content still too long for concise description")
            
        print(f"Target Length: ~150 characters")
        print(f"Achieved Length: {result.extracted_length} characters")
        
        # Check reduction effectiveness
        if result.reduction_percentage >= 80:
            print("✅ EXCELLENT: High content reduction achieved")
        elif result.reduction_percentage >= 60:
            print("✅ GOOD: Reasonable content reduction")
        else:
            print("❌ POOR: Insufficient content reduction")
            
        # Recommendations for Sandy
        print("\n💡 RECOMMENDATIONS FOR SANDY:")
        print("=" * 35)
        
        if result.reduction_percentage >= 60 and result.extracted_length <= 500:
            print("✅ INTEGRATION READY:")
            print("1. v2.0 extract_core_content() produces good concise descriptions")
            print("2. Replace current daily report 'Concise Description' logic with v2.0")
            print("3. Use result.extracted_content for the concise description field")
            print("4. Continue using v3.3 extract_skills() for technical requirements")
            
        elif result.extracted_length > 500:
            print("⚠️  NEEDS REFINEMENT:")
            print("1. v2.0 content extraction working but still too verbose")
            print("2. Consider additional prompt engineering for ultra-concise output")
            print("3. May need to create a 'super concise' extraction mode")
            print("4. Alternative: Extract first 2-3 sentences from v2.0 output")
            
        else:
            print("❌ INTEGRATION ISSUES:")
            print("1. v2.0 extraction not meeting concise description requirements")
            print("2. Review v2.0 prompts and LLM parameters")
            print("3. Consider hybrid approach: v2.0 for structure + custom summarization")
            print("4. Test with different LLM models for better summarization")
            
        # Implementation guidance
        print("\n🔧 IMPLEMENTATION GUIDANCE:")
        print("1. Daily Report Integration:")
        print("   - Replace current logic with: result = extract_job_content_v2(raw_job)")
        print("   - Use: result.extracted_content as the concise description")
        print("   - Keep: v3.3 for skills extraction (already working well)")
        print()
        print("2. Pipeline Configuration:")
        print("   - v2.0 for content optimization & concise descriptions")
        print("   - v3.3 for detailed skill categorization")
        print("   - Both specialists complement each other perfectly")
        
    except Exception as e:
        print(f"\n❌ EXTRACTION FAILED: {e}")
        print("\n🚨 DEBUGGING INFORMATION:")
        print("1. Check if Ollama is running: curl http://localhost:11434/api/tags")
        print("2. Verify model availability: ollama list")
        print("3. Check v2.0 specialist path and imports")
        print("4. Test with simpler job description first")
        
        print("\n💡 IMMEDIATE ACTIONS FOR SANDY:")
        print("1. Validate v2.0 environment setup and dependencies")
        print("2. Test v2.0 specialist with minimal job description")
        print("3. Check LLM model availability and connectivity")
        print("4. Consider fallback extraction strategy for daily reports")

if __name__ == "__main__":
    main()
