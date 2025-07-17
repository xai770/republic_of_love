#!/usr/bin/env python3
"""
CORRECTED EMERGENCY TEST: German Language Technical Requirements Extraction Crisis
================================================================================

Testing v3.3 specialist vs daily report extraction with correct method names.
Focus: German/English mixed content technical extraction failures.
"""

import sys
import os
import re

# Add the correct path to the v3.3 specialist
sys.path.append('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_crisis_resolution_20250702')

def test_v3_3_technical_extraction():
    """Test v3.3 specialist on problematic SAP and Sales jobs"""
    
    print("🚨 CORRECTED v3.3 TECHNICAL EXTRACTION TEST")
    print("=" * 60)
    
    try:
        from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33
        specialist = ContentExtractionSpecialistV33()
        print("✅ Successfully imported ContentExtractionSpecialistV33")
    except Exception as e:
        print(f"❌ CRITICAL: Cannot import v3.3 specialist: {e}")
        return
    
    # Test Case 1: SAP ABAP Engineer - CRITICAL failure case
    print("\n" + "=" * 60)
    print("TEST CASE 1: SAP ABAP Engineer (CRITICAL Failure)")
    print("=" * 60)
    
    sap_job_desc = """
    Senior SAP ABAP Engineer – Group General Ledger (f/m/x)
    
    Fundierte Berufserfahrung in der Entwicklung und Programmierung großer und komplexer Softwarelösungen in SAP-Produkten wie: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI und Planung, SAP HANA, BW/4HANA, respektive die Entwicklung neuer Lösungen und die Pflege einer großen ABAP-Codebasis zur Unterstützung verschiedener Kernprozesse der Bank
    
    Wünschenswert sind Erfahrungen in Bereichen wie: SAP BTP, DataSphere und die Gen AI-Produkte von SAP; Design und Softwareentwicklung integrierter Reporting-Lösungen wie SAC BI, SAP Business Objects, Tableau oder SAP SAC
    
    Vorteilhaft sind Erfahrungen mit agilen Entwicklungsmethoden, einschließlich DevOps-Konzepten; Erfahrungen mit Google Cloud-Services, wie dem Vertex- oder Cortex-Framework und anderen Technologien, wie Python, JSON, .Net oder Tableau
    
    Profound professional experience and track record in the designing and programming of large scale & complex software solutions in some of the SAP products such as: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI and Planning, SAP HANA, BW/4HANA or developing new solutions & maintaining our large ABAP code base supporting various key processes
    
    Desirable experience in certain areas like: SAP BTP, DataSphere and SAP's Gen AI products; design and software development of integrated reporting solutions such as SAC BI, SAP Business Objects, Tableau or SAP SAC
    
    Experience in agile development methods including DevOps concepts; experience in Google cloud services such as Vertex or Cortex framework, Python, JSON, .Net or Tableau
    """
    
    daily_report_extraction = "Programming: PYTHON; Programming: GO; Programming: R; Database: SQL; Analytics: tableau (+2 more)"
    
    print(f"Daily Report Extracted: {daily_report_extraction}")
    print("Expected SAP Technologies: ABAP, SAP HANA, BPC, SAC, PaPM, BTP, DataSphere, etc.")
    
    try:
        print("\n🔍 Testing v3.3 specialist...")
        v33_tech_skills = specialist.extract_technical_skills(sap_job_desc)
        print(f"v3.3 Technical Skills: {v33_tech_skills}")
        
        # Check for critical SAP technologies
        critical_sap_tech = ['ABAP', 'SAP HANA', 'HANA', 'BPC', 'SAC', 'PaPM', 'BTP', 'DataSphere']
        found_sap_tech = []
        for tech in critical_sap_tech:
            for skill in v33_tech_skills:
                if tech.lower() in skill.lower():
                    found_sap_tech.append(skill)
                    break
        
        print(f"\n📊 SAP Technologies Found by v3.3: {found_sap_tech}")
        
        missing_from_daily = [tech for tech in critical_sap_tech if tech.lower() not in daily_report_extraction.lower()]
        print(f"📊 Missing from Daily Report: {missing_from_daily}")
        
        if len(found_sap_tech) > len(daily_report_extraction.split(';')):
            print("✅ v3.3 is SIGNIFICANTLY better than daily report!")
        else:
            print("❌ v3.3 is also failing to extract SAP technologies properly")
            
    except Exception as e:
        print(f"❌ ERROR testing v3.3 specialist: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 2: Sales Specialist - Wrong programming languages
    print("\n" + "=" * 60)
    print("TEST CASE 2: Sales Specialist (Wrong Programming Languages)")
    print("=" * 60)
    
    sales_job_desc = """
    Institutional Cash and Trade Sales Specialist (Client Sales Manager) – DACHLIE (f/m/x)
    
    Sie haben mehrjährige Erfahrung im Correspondent Banking bei einer größeren europäischen oder amerikanischen Bank
    Sie besitzen Produktkenntnisse in den Bereichen Cash Management (internationaler, grenzüberschreitender Zahlungsverkehr, Liquiditätsteuerung für Banken) und im Trade Finance
    Sie überzeugen mit Ihren Fähigkeiten zum Präsentieren um sowohl schriftlich als auch mündlich unsere Strategie, Produkte und unseren Risikoappetit zu repräsentieren
    Sie benutzen aktiv unsere MIS- und Reporting-Tools für das Management Ihrer Namen
    
    Monitor revenue trends via various reporting tools like Salesforce and dbTableau
    Sound product knowledge of cash management and trade products and services for financial institutions
    Solid presentation and communication skills in German and English, written and oral
    Strong negotiation skills essential
    """
    
    daily_report_sales_extraction = "Programming: GO; Programming: R; Analytics: tableau; CRM: salesforce"
    
    print(f"Daily Report Extracted: {daily_report_sales_extraction}")
    print("❌ WRONG: Sales roles should NOT have GO, R programming languages!")
    print("✅ CORRECT: Should have Salesforce, Tableau (for reporting), MIS tools")
    
    try:
        print("\n🔍 Testing v3.3 specialist on sales job...")
        v33_sales_tech = specialist.extract_technical_skills(sales_job_desc)
        print(f"v3.3 Technical Skills: {v33_sales_tech}")
        
        # Check for inappropriate programming languages
        programming_langs = ['GO', 'R', 'Python', 'Java', 'C++', 'JavaScript']
        inappropriate_langs = []
        for skill in v33_sales_tech:
            for lang in programming_langs:
                if lang.lower() == skill.lower():
                    inappropriate_langs.append(skill)
        
        # Check for appropriate sales/reporting tools
        appropriate_tools = ['Salesforce', 'Tableau', 'MIS', 'CRM']
        found_appropriate = []
        for skill in v33_sales_tech:
            for tool in appropriate_tools:
                if tool.lower() in skill.lower():
                    found_appropriate.append(skill)
        
        print(f"\n📊 Inappropriate Programming Languages: {inappropriate_langs}")
        print(f"📊 Appropriate Sales Tools: {found_appropriate}")
        
        if len(inappropriate_langs) == 0:
            print("✅ v3.3 correctly avoids programming languages for sales role")
        else:
            print("❌ v3.3 is also incorrectly extracting programming languages")
            
    except Exception as e:
        print(f"❌ ERROR testing v3.3 on sales job: {e}")

def check_v3_3_prompt_quality():
    """Check the quality of v3.3's technical extraction prompt"""
    
    print("\n" + "=" * 60)
    print("v3.3 PROMPT QUALITY ANALYSIS")
    print("=" * 60)
    
    try:
        from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33
        specialist = ContentExtractionSpecialistV33()
        
        # Read the technical skills prompt from the source code
        with open('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_crisis_resolution_20250702/content_extraction_specialist_v3_3_PRODUCTION.py', 'r') as f:
            content = f.read()
        
        # Extract the technical skills prompt
        prompt_start = content.find('prompt = f"""EXTRACT ONLY EXPLICITLY MENTIONED TECHNICAL SKILLS.')
        if prompt_start != -1:
            prompt_end = content.find('response = self._call_ollama(prompt)', prompt_start)
            if prompt_end != -1:
                prompt_section = content[prompt_start:prompt_end]
                print("📋 v3.3 Technical Skills Prompt:")
                print("-" * 40)
                print(prompt_section)
                
                # Analyze prompt for issues
                issues = []
                
                if 'German' not in prompt_section and 'deutsch' not in prompt_section.lower():
                    issues.append("❌ No German language instructions")
                
                if 'SAP' not in prompt_section:
                    issues.append("❌ SAP ecosystem not explicitly mentioned")
                    
                if 'ABAP' not in prompt_section:
                    issues.append("❌ ABAP not in examples")
                
                if 'context' not in prompt_section.lower() and 'role' not in prompt_section.lower():
                    issues.append("❌ No job role context validation")
                
                if issues:
                    print("\n🔍 PROMPT ISSUES IDENTIFIED:")
                    for issue in issues:
                        print(f"  {issue}")
                else:
                    print("\n✅ Prompt looks comprehensive")
                    
        else:
            print("❌ Could not extract technical skills prompt from source")
            
    except Exception as e:
        print(f"❌ ERROR analyzing prompt: {e}")

def main():
    """Run corrected emergency test"""
    
    print("🚨 CORRECTED EMERGENCY ANALYSIS: German Technical Extraction Crisis")
    print("This test uses the correct v3.3 method names to diagnose the issues.")
    print("\n")
    
    test_v3_3_technical_extraction()
    check_v3_3_prompt_quality()
    
    print("\n" + "=" * 60)
    print("🎯 CORRECTED ANALYSIS SUMMARY")
    print("=" * 60)
    
    print("1. COMPARISON TEST RESULTS:")
    print("   - If v3.3 extracts SAP technologies but daily report doesn't")
    print("   - Then daily report generator is NOT using v3.3 properly")
    print("   - If v3.3 also misses SAP technologies")
    print("   - Then v3.3 prompt needs SAP-specific improvements")
    
    print("\n2. GERMAN LANGUAGE HYPOTHESIS:")
    print("   - Both German and English sections contain same tech terms")
    print("   - Issue is likely NOT German language parsing")
    print("   - Issue is extraction logic or domain knowledge")
    
    print("\n3. NEXT STEPS:")
    print("   - Compare v3.3 vs daily report results from this test")
    print("   - Improve v3.3 prompt for SAP ecosystem if needed")
    print("   - Fix daily report generator integration")
    print("   - Add job role validation to prevent sales/programming confusion")

if __name__ == "__main__":
    main()
