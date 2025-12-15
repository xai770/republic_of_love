#!/usr/bin/env python3
"""
Import Gershon's profile from Markdown to database
Parse work history and create profile record
"""

import psycopg2
from datetime import datetime
import json

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

def parse_markdown_profile(file_path):
    """Parse Gershon's profile from Markdown"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Basic profile info
    profile = {
        'full_name': 'Gershon Pollatschek',
        'email': 'gershon.pollatschek@example.com',  # Placeholder
        'location': 'Frankfurt/Basel area',
        'profile_source': 'markdown',
        'profile_raw_text': content,
        'current_title': 'Project Lead Contract Compliance/Tech Lead',
        'experience_level': 'executive',
        'years_of_experience': 28,  # 1996-2024
        'availability_status': 'passive'
    }
    
    # Work history entries
    work_history = [
        {
            'company_name': 'Deutsche Bank',
            'job_title': 'Project Lead Contract Compliance/Tech Lead',
            'department': 'Chief Technology Office',
            'start_date': '2022-01-01',
            'is_current': True,
            'location': 'Frankfurt',
            'job_description': '''Each piece of software may only be used according to contractually agreed licensing conditions. To ensure these conditions are adhered to DB must have visibility of which contract/s apply to a given software purchase.''',
            'achievements': [
                'Understand and reverse engineer the process, which was followed up to this point',
                'Analyze gaps in process and propose new process',
                'Identify and review data sources to be utilized. Flag data quality issues with stakeholders',
                'Formalize new process into automated application, which will generate the required output and update worklists'
            ],
            'technologies_used': ['Software Compliance', 'Contract Management', 'Process Automation', 'Data Analysis']
        },
        {
            'company_name': 'Deutsche Bank',
            'job_title': 'Team Lead Proof of Entitlement/Contractual Provisions Management',
            'department': 'Chief Technology Office',
            'start_date': '2021-01-01',
            'end_date': '2022-01-01',
            'is_current': False,
            'location': 'Frankfurt',
            'job_description': '''Leading development of processes and supporting tools for Proof of Entitlement Capturing.''',
            'achievements': [
                'Mobilize relevant data from purchasing systems, uploading it to a work list',
                'Design and implement backend/frontend solution to enable team collaboration',
                'Provide automated KPI reporting on involved processes',
                'Ensure contractual documentation are referred to in Proofs of Entitlement',
                'Provide cleansed PoE records to ServiceNow/SAM Pro for upload'
            ],
            'technologies_used': ['Backend Development', 'Frontend Development', 'KPI Reporting', 'ServiceNow', 'SAM Pro', 'Data Integration']
        },
        {
            'company_name': 'Deutsche Bank',
            'job_title': 'Financial Planning and Governance - Software License Management',
            'department': 'Chief Technology Office',
            'start_date': '2020-01-01',
            'end_date': '2021-01-01',
            'is_current': False,
            'location': 'Frankfurt',
            'job_description': '''Monitoring spend and reviewing it with divisional stakeholders.''',
            'achievements': [
                'Setting up network of divisional stakeholders and holding monthly review sessions',
                'Review trends in spending, compare to forecast and plan',
                'Prepare monthly updates for Board of Director review'
            ],
            'technologies_used': ['Financial Planning', 'Governance', 'Budget Management', 'Stakeholder Management']
        },
        {
            'company_name': 'Self-Employed',
            'job_title': 'Software Developer - Text Analysis Framework',
            'start_date': '2016-01-01',
            'end_date': '2020-01-01',
            'is_current': False,
            'location': 'Frankfurt/Basel',
            'job_description': '''Development of analysis framework for structured text documents.''',
            'achievements': [
                'Generation of ontologies for structured content (scientific articles, legal texts, technical documents)',
                'Prediction of relevant key phrases using statistical models and machine learning',
                'Reporting of match/no match condition of paragraphs between document sets'
            ],
            'technologies_used': ['Python', 'Machine Learning', 'NLP', 'Statistical Modeling', 'Ontology Design']
        },
        {
            'company_name': 'Novartis',
            'job_title': 'Global Sourcing IT Change Management and Governance',
            'department': 'Global Sourcing',
            'start_date': '2012-01-01',
            'end_date': '2015-12-31',
            'is_current': False,
            'location': 'Basel',
            'job_description': '''Responsible for governance of global IT category of Novartis group. Managing 15+ sub-category managers.''',
            'achievements': [
                'Annual target setting and regular reporting of spend and benefits',
                'Implement standard operating procedures for sourcing',
                'Support savings recognition and reporting to top management',
                'Design, implement and maintain reporting backend application integrating multiple data sources'
            ],
            'technologies_used': ['SAP CLM', 'SavePlan', 'eSourcing', 'Data Warehouse', 'SharePoint', 'KPI Reporting']
        },
        {
            'company_name': 'Novartis',
            'job_title': 'Global Lead, Software License Management',
            'department': 'Global Sourcing',
            'start_date': '2010-01-01',
            'end_date': '2012-12-31',
            'is_current': False,
            'location': 'Basel',
            'job_description': '''Group wide designated single point of contact for all software compliance challenges.''',
            'achievements': [
                'Managed major software compliance challenges (Interwoven, SAS, SAP)',
                'Provides guidance on best practice of software compliance management',
                'Interfaced with legal team as subject matter expert in contract negotiations',
                'Analyzed existing applications for possible licensing gaps'
            ],
            'technologies_used': ['Software Compliance', 'Contract Negotiation', 'Legal Compliance', 'Risk Management']
        },
        {
            'company_name': 'Deutsche Bank AG',
            'job_title': 'Software Licenses and Services Vendor Manager',
            'department': 'Global Banking IT',
            'start_date': '2008-01-01',
            'end_date': '2010-12-31',
            'is_current': False,
            'location': 'Frankfurt',
            'job_description': '''Led Software Licenses and Services team for Global Banking IT division globally.''',
            'achievements': [
                'Led strategic five-year outsourcing deal with IBM (12m€+)',
                'Established steering committee to monitor KPIs and manage change requests',
                'Led centralized rate reduction initiative (1.8m€ savings)',
                'Managed 70+ new contracts amounting to 8m€ and saving 680k€+'
            ],
            'technologies_used': ['Contract Management', 'Vendor Management', 'HP Mercury', 'Outsourcing Management']
        },
        {
            'company_name': 'Deutsche Bank AG',
            'job_title': 'Software Category Manager',
            'department': 'Global Procurement',
            'start_date': '2005-01-01',
            'end_date': '2008-12-31',
            'is_current': False,
            'location': 'Frankfurt',
            'job_description': '''Led software category management in EMEA and co-led globally.''',
            'achievements': [
                'Managed 70+ contracts (8m€) with 680k€+ savings',
                'Completed strategic vendor transactions (Microsoft, HP, WebMethods, Adobe)',
                'Compiled dynamic contract master with 189+ clauses for compliance assessment',
                'Managed vendor portal onboarding project'
            ],
            'technologies_used': ['Contract Management', 'Procurement', 'Vendor Management', 'Compliance Management']
        }
    ]
    
    # Languages
    languages = [
        {'language_name': 'German', 'proficiency_level': 'native'},
        {'language_name': 'English', 'proficiency_level': 'fluent'},
    ]
    
    return profile, work_history, languages

def insert_profile(conn, profile, work_history, languages):
    """Insert profile and related data into database"""
    
    cursor = conn.cursor()
    
    try:
        # Insert main profile
        cursor.execute("""
            INSERT INTO profiles (
                full_name, email, location, profile_source, profile_raw_text,
                current_title, experience_level, years_of_experience, availability_status,
                enabled, created_at, updated_at
            ) VALUES (
                %(full_name)s, %(email)s, %(location)s, %(profile_source)s, %(profile_raw_text)s,
                %(current_title)s, %(experience_level)s, %(years_of_experience)s, %(availability_status)s,
                TRUE, NOW(), NOW()
            ) RETURNING profile_id
        """, profile)
        
        profile_id = cursor.fetchone()[0]
        print(f"✅ Inserted profile: {profile['full_name']} (ID: {profile_id})")
        
        # Insert work history
        for work in work_history:
            cursor.execute("""
                INSERT INTO profile_work_history (
                    profile_id, company_name, job_title, department,
                    start_date, end_date, is_current, location,
                    job_description, achievements, technologies_used,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
            """, (
                profile_id,
                work['company_name'],
                work['job_title'],
                work.get('department'),
                work['start_date'],
                work.get('end_date'),
                work['is_current'],
                work.get('location'),
                work['job_description'],
                work['achievements'],
                work['technologies_used']
            ))
        
        print(f"✅ Inserted {len(work_history)} work history entries")
        
        # Insert languages
        for lang in languages:
            cursor.execute("""
                INSERT INTO profile_languages (
                    profile_id, language_name, proficiency_level, created_at
                ) VALUES (%s, %s, %s, NOW())
            """, (profile_id, lang['language_name'], lang['proficiency_level']))
        
        print(f"✅ Inserted {len(languages)} languages")
        
        conn.commit()
        print(f"\n🎉 Profile import complete! Profile ID: {profile_id}")
        
        return profile_id
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error inserting profile: {e}")
        raise

def main():
    """Main import process"""
    
    print("🔍 Parsing Gershon's profile from Markdown...")
    profile, work_history, languages = parse_markdown_profile(
        '/home/xai/Documents/ty_learn/docs/Gershon Pollatschek Projects.md'
    )
    
    print(f"\n📋 Profile Summary:")
    print(f"   Name: {profile['full_name']}")
    print(f"   Current Title: {profile['current_title']}")
    print(f"   Experience Level: {profile['experience_level']}")
    print(f"   Years of Experience: {profile['years_of_experience']}")
    print(f"   Work History Entries: {len(work_history)}")
    print(f"   Languages: {len(languages)}")
    
    print(f"\n💾 Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    print(f"✅ Connected! Inserting profile...")
    profile_id = insert_profile(conn, profile, work_history, languages)
    
    # Show inserted data
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.profile_id,
            p.full_name,
            p.current_title,
            p.experience_level,
            COUNT(DISTINCT w.work_history_id) as work_entries,
            COUNT(DISTINCT l.language_id) as languages
        FROM profiles p
        LEFT JOIN profile_work_history w ON p.profile_id = w.profile_id
        LEFT JOIN profile_languages l ON p.profile_id = l.profile_id
        WHERE p.profile_id = %s
        GROUP BY p.profile_id, p.full_name, p.current_title, p.experience_level
    """, (profile_id,))
    
    result = cursor.fetchone()
    print(f"\n📊 Verification:")
    print(f"   Profile ID: {result[0]}")
    print(f"   Name: {result[1]}")
    print(f"   Title: {result[2]}")
    print(f"   Level: {result[3]}")
    print(f"   Work Entries: {result[4]}")
    print(f"   Languages: {result[5]}")
    
    conn.close()
    print(f"\n✅ All done!")

if __name__ == '__main__':
    main()
