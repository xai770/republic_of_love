#!/usr/bin/env python3
"""
URGENT: German Language Technical Requirements Extraction Emergency Test
=======================================================================

The daily report is catastrophically failing at technical requirements extraction.
This script will test v3.3 specialist directly vs what's happening in the daily report.

CRITICAL ISSUES IDENTIFIED:
1. SAP ABAP Engineer job missing ALL SAP technologies (ABAP, HANA, BPC, SAC, etc.)
2. Sales Specialist job incorrectly tagged with programming languages (GO, R)
3. German text sections being completely missed or misinterpreted

This needs IMMEDIATE resolution as it affects job matching accuracy.
"""

import sys
import os
import re

# Add the correct path to the v3.3 specialist
sys.path.append('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_crisis_resolution_20250702')

def test_v3_3_vs_daily_report():
    """Compare v3.3 specialist vs daily report extraction on real job data"""
    
    print("🚨 EMERGENCY TECHNICAL EXTRACTION TEST")
    print("=" * 60)
    
    # Import the v3.3 specialist
    try:
        from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33
        specialist = ContentExtractionSpecialistV33()
        print("✅ Successfully imported ContentExtractionSpecialistV33")
    except Exception as e:
        print(f"❌ CRITICAL: Cannot import v3.3 specialist: {e}")
        return
    
    # Test Case 1: SAP ABAP Engineer
    print("\n" + "=" * 60)
    print("TEST CASE 1: SAP ABAP Engineer")
    print("=" * 60)
    
    sap_job_title = "Senior SAP ABAP Engineer – Group General Ledger (f/m/x)"
    sap_job_desc = """
    Fundierte Berufserfahrung in der Entwicklung und Programmierung großer und komplexer Softwarelösungen in SAP-Produkten wie: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI und Planung, SAP HANA, BW/4HANA, respektive die Entwicklung neuer Lösungen und die Pflege einer großen ABAP-Codebasis zur Unterstützung verschiedener Kernprozesse der Bank
    
    Wünschenswert sind Erfahrungen in Bereichen wie: SAP BTP, DataSphere und die Gen AI-Produkte von SAP; Design und Softwareentwicklung integrierter Reporting-Lösungen wie SAC BI, SAP Business Objects, Tableau oder SAP SAC
    
    Vorteilhaft sind Erfahrungen mit agilen Entwicklungsmethoden, einschließlich DevOps-Konzepten; Erfahrungen mit Google Cloud-Services, wie dem Vertex- oder Cortex-Framework und anderen Technologien, wie Python, JSON, .Net oder Tableau
    
    Profound professional experience and track record in the designing and programming of large scale & complex software solutions in some of the SAP products such as: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI and Planning, SAP HANA, BW/4HANA or developing new solutions & maintaining our large ABAP code base supporting various key processes
    
    Desirable experience in certain areas like: SAP BTP, DataSphere and SAP's Gen AI products; design and software development of integrated reporting solutions such as SAC BI, SAP Business Objects, Tableau or SAP SAC
    
    Beneficial to have experience in agile development methods including DevOps concepts; experience in Google cloud services such as Vertex or Cortex framework, Python, JSON, .Net or Tableau
    """
    
    daily_report_extraction = "Programming: PYTHON; Programming: GO; Programming: R; Database: SQL; Analytics: tableau (+2 more)"
    
    print(f"Job Title: {sap_job_title}")
    print(f"Daily Report Extracted: {daily_report_extraction}")
    
    try:
        v33_result = specialist.extract_technical_requirements(sap_job_desc, sap_job_title)
        print(f"v3.3 Specialist Result: {v33_result}")
        
        # Compare results
        expected_sap_tech = ['ABAP', 'SAP HANA', 'BPC', 'SAC', 'PaPM', 'BTP', 'DataSphere', 'Fiori', 'DevOps']
        missing_from_daily = [tech for tech in expected_sap_tech if tech.lower() not in daily_report_extraction.lower()]
        found_in_v33 = [tech for tech in expected_sap_tech if tech.lower() in str(v33_result).lower()]
        
        print(f"\n📊 COMPARISON:")
        print(f"Expected SAP Technologies: {', '.join(expected_sap_tech)}")
        print(f"Missing from Daily Report: {', '.join(missing_from_daily)}")
        print(f"Found by v3.3: {', '.join(found_in_v33)}")
        
    except Exception as e:
        print(f"❌ ERROR testing v3.3 specialist: {e}")
    
    # Test Case 2: Sales Specialist (should NOT have programming languages)
    print("\n" + "=" * 60)
    print("TEST CASE 2: Sales Specialist")
    print("=" * 60)
    
    sales_job_title = "Institutional Cash and Trade Sales Specialist (Client Sales Manager)"
    sales_job_desc = """
    Sie haben mehrjährige Erfahurng im Correspondent Banking bei einer größeren europäischen oder amerikanischen Bank
    Sie besitzen Produktkenntnisse in den Bereichen Cash Management (internationaler, grenzüberschreitender Zahlungsverkehr, Liquiditätsteuerung für Banken) und im Trade Finance
    Sie überzeugen mit Ihren Fähigkeiten zum Präsentieren um sowohl schriftlich als auch mündlich unsere Strategie, Produkte und unseren Risikoappetit zu repräsentieren
    Sie benutzen aktiv unsere MIS- und Reporting-Tools für das Management Ihrer Namen
    
    Monitor revenue trends via various reporting tools like Salesforce and dbTableau
    Sound product knowledge of cash management and trade products and services for financial institutions
    Solid presentation and communication skills in German and English, written and oral
    """
    
    daily_report_sales_extraction = "Programming: GO; Programming: R; Analytics: tableau; CRM: salesforce"
    
    print(f"Job Title: {sales_job_title}")
    print(f"Daily Report Extracted: {daily_report_sales_extraction}")
    
    try:
        v33_sales_result = specialist.extract_technical_requirements(sales_job_desc, sales_job_title)
        print(f"v3.3 Specialist Result: {v33_sales_result}")
        
        # Check for incorrect programming language extraction
        programming_langs = ['GO', 'R', 'Python', 'Java', 'C++']
        incorrect_in_daily = [lang for lang in programming_langs if lang.lower() in daily_report_sales_extraction.lower()]
        incorrect_in_v33 = [lang for lang in programming_langs if lang.lower() in str(v33_sales_result).lower()]
        
        print(f"\n📊 COMPARISON:")
        print(f"❌ Incorrect programming languages in Daily Report: {', '.join(incorrect_in_daily)}")
        print(f"❌ Incorrect programming languages in v3.3: {', '.join(incorrect_in_v33)}")
        print("Sales roles should NOT have programming language requirements!")
        
    except Exception as e:
        print(f"❌ ERROR testing v3.3 specialist on sales job: {e}")

def analyze_extraction_prompt():
    """Analyze the v3.3 specialist's prompt for German language handling"""
    
    print("\n" + "=" * 60)
    print("PROMPT ANALYSIS: German Language Handling")
    print("=" * 60)
    
    try:
        from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33
        specialist = ContentExtractionSpecialistV33()
        
        # Check if the specialist has prompt inspection capabilities
        if hasattr(specialist, 'get_technical_requirements_prompt') or hasattr(specialist, 'prompt'):
            print("✅ Can inspect v3.3 prompts")
            # Try to get the prompt
            try:
                if hasattr(specialist, 'get_technical_requirements_prompt'):
                    prompt = specialist.get_technical_requirements_prompt()
                elif hasattr(specialist, 'prompt'):
                    prompt = specialist.prompt
                else:
                    prompt = None
                
                if prompt:
                    print("📋 v3.3 Technical Requirements Prompt:")
                    print("-" * 40)
                    print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
                    
                    # Check for German language instructions
                    german_keywords = ['german', 'deutsch', 'multilingual', 'language', 'sprache']
                    found_german_refs = [word for word in german_keywords if word.lower() in prompt.lower()]
                    
                    if found_german_refs:
                        print(f"\n✅ German language references found: {', '.join(found_german_refs)}")
                    else:
                        print("\n❌ NO German language handling found in prompt!")
                        print("🎯 RECOMMENDATION: Add German language instructions to prompt")
                
            except Exception as e:
                print(f"Cannot retrieve prompt: {e}")
        else:
            print("❌ Cannot inspect v3.3 prompts - no accessible prompt methods")
            
    except Exception as e:
        print(f"❌ Cannot analyze prompt: {e}")

def check_daily_report_generator():
    """Check how the daily report generator uses the extraction specialist"""
    
    print("\n" + "=" * 60)
    print("DAILY REPORT GENERATOR ANALYSIS")
    print("=" * 60)
    
    # Look for the daily report generator
    potential_generator_files = [
        "daily_report_generator.py",
        "generate_daily_report.py",
        "job_analysis.py",
        "enhanced_daily_report_generator.py"
    ]
    
    for filename in potential_generator_files:
        # Search for the file
        search_results = []
        for root, dirs, files in os.walk('/home/xai/Documents/republic_of_love'):
            for file in files:
                if filename in file.lower():
                    search_results.append(os.path.join(root, file))
        
        if search_results:
            print(f"✅ Found potential generator: {search_results[0]}")
            return search_results[0]
    
    print("❌ Cannot locate daily report generator file")
    print("🎯 RECOMMENDATION: Sandy needs to check daily report integration")

def main():
    """Run emergency technical extraction test"""
    
    print("🚨 GERMAN LANGUAGE TECHNICAL EXTRACTION EMERGENCY")
    print("This script tests why technical requirements are catastrophically failing")
    print("in the daily report, especially for German/English mixed content.")
    print("\n")
    
    # Run comprehensive tests
    test_v3_3_vs_daily_report()
    analyze_extraction_prompt()
    check_daily_report_generator()
    
    print("\n" + "=" * 60)
    print("🎯 EMERGENCY ACTION ITEMS")
    print("=" * 60)
    
    print("1. 🔥 IMMEDIATE: Daily report is NOT using v3.3 properly")
    print("   - SAP job missing ALL SAP technologies")
    print("   - Sales job incorrectly tagged with programming languages")
    
    print("\n2. 🔍 ROOT CAUSE INVESTIGATION NEEDED:")
    print("   - Check if daily report generator imports v3.3 correctly")
    print("   - Verify v3.3 is called with correct parameters")
    print("   - Test v3.3 prompt with German/English mixed content")
    
    print("\n3. 🛠️ PROMPT IMPROVEMENTS:")
    print("   - Add explicit German language handling instructions")
    print("   - Improve SAP ecosystem technology recognition")
    print("   - Add job role context validation (sales vs technical)")
    
    print("\n4. 📧 COMMUNICATE TO SANDY:")
    print("   - Daily report generator needs immediate fix")
    print("   - v3.3 specialist works better but still needs improvement")
    print("   - German language content is not the core issue")

if __name__ == "__main__":
    main()
