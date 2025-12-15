#!/usr/bin/env python3
"""
Import Recipe 1121 Skills to Skill Hierarchy
============================================

Imports the 393 skills extracted by Recipe 1121 into:
- skill_aliases: unique skill entries with proper naming
- skill_hierarchy: hierarchical relationships inferred from skill taxonomy

Created: 2025-10-29
Author: Arden (via ty_learn session)
"""

import psycopg2
import json
from collections import defaultdict
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

CREATED_BY = "Recipe_1121_Import_2025-10-29"

def normalize_skill_name(skill_text):
    """Convert UPPER_CASE_SKILL to proper Title Case"""
    # Remove underscores and title case
    words = skill_text.replace('_', ' ').split()
    # Handle special cases
    special_cases = {
        'Ifrs': 'IFRS',
        'Iso': 'ISO', 
        'Nist': 'NIST',
        'Cis': 'CIS',
        'It': 'IT',
        'Ai': 'AI',
        'Api': 'API',
        'Ui': 'UI',
        'Ux': 'UX',
        'Sql': 'SQL',
        'Hr': 'HR',
        'Crm': 'CRM',
        'Erp': 'ERP',
        'Sap': 'SAP'
    }
    normalized_words = []
    for word in words:
        titled = word.capitalize()
        normalized_words.append(special_cases.get(titled, titled))
    
    return ' '.join(normalized_words)

def infer_parent_skill(skill_text):
    """
    Infer parent skill from the skill name using common patterns.
    Returns (parent_skill, strength) or (None, None) if top-level
    """
    # Common patterns for hierarchical relationships
    parts = skill_text.split('_')
    
    # If skill has 3+ parts, try to find a parent in 2 parts
    if len(parts) >= 3:
        # e.g., NETWORK_SECURITY_TECHNOLOGIES -> NETWORK_SECURITY
        parent_candidate = '_'.join(parts[:2])
        return parent_candidate, 0.85
    
    # If skill has 2 parts, check for common domain categories
    if len(parts) == 2:
        first_word = parts[0]
        # Common domain prefixes
        domain_categories = {
            'NETWORK': 'NETWORKING',
            'SECURITY': 'CYBERSECURITY',
            'TEAM': 'SOFT_SKILLS',
            'LEADERSHIP': 'SOFT_SKILLS',
            'COMMUNICATION': 'SOFT_SKILLS',
            'FINANCIAL': 'FINANCE',
            'ACCOUNTING': 'FINANCE',
            'DATABASE': 'DATA_MANAGEMENT',
            'DATA': 'DATA_MANAGEMENT',
            'SOFTWARE': 'TECHNOLOGY',
            'HARDWARE': 'TECHNOLOGY',
            'AUTOMATION': 'TECHNOLOGY',
            'STRATEGIC': 'BUSINESS_STRATEGY',
            'DECISION': 'BUSINESS_STRATEGY'
        }
        
        if first_word in domain_categories:
            return domain_categories[first_word], 0.75
    
    # Top-level skill (no parent)
    return None, None

def extract_all_skills(conn):
    """Extract all unique skills from postings.skill_keywords"""
    cur = conn.cursor()
    
    print("🔍 Extracting skills from postings...")
    cur.execute("""
        SELECT DISTINCT skill
        FROM postings, json_array_elements_text(skill_keywords::json) as skill
        WHERE skill_keywords::text != '[]'
        ORDER BY skill;
    """)
    
    skills = [row[0] for row in cur.fetchall()]
    print(f"   Found {len(skills)} unique skills")
    
    cur.close()
    return skills

def create_skill_aliases(conn, skills):
    """Create entries in skill_aliases table"""
    cur = conn.cursor()
    
    print(f"\n📝 Creating {len(skills)} skill aliases...")
    
    # First, check what already exists
    cur.execute("SELECT skill FROM skill_aliases;")
    existing_skills = {row[0] for row in cur.fetchall()}
    print(f"   {len(existing_skills)} skills already exist")
    
    inserted = 0
    skipped = 0
    
    for skill_raw in skills:
        # Use the raw skill as the primary key
        skill_normalized = skill_raw
        display_name = normalize_skill_name(skill_raw)
        
        if skill_normalized in existing_skills:
            skipped += 1
            continue
        
        try:
            cur.execute("""
                INSERT INTO skill_aliases (skill_alias, skill, display_name, language, confidence, created_by, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (skill_alias) DO NOTHING;
            """, (
                skill_raw,  # skill_alias (raw format for matching)
                skill_normalized,  # skill (canonical form)
                display_name,  # display_name (human-readable)
                'de',  # language (German job postings)
                0.95,  # confidence (high - extracted by gopher)
                CREATED_BY,
                f"Extracted by Recipe 1121 from German job postings"
            ))
            inserted += 1
            
            if inserted % 50 == 0:
                print(f"   Progress: {inserted}/{len(skills)}")
                
        except Exception as e:
            print(f"   ⚠️  Error inserting {skill_raw}: {e}")
    
    conn.commit()
    print(f"   ✅ Inserted {inserted} new skills, skipped {skipped} existing")
    cur.close()
    
    return inserted

def create_skill_hierarchy(conn, skills):
    """Create hierarchical relationships in skill_hierarchy table"""
    cur = conn.cursor()
    
    print(f"\n🌲 Building skill hierarchy...")
    
    # First, check existing relationships
    cur.execute("SELECT COUNT(*) FROM skill_hierarchy;")
    existing_count = cur.fetchone()[0]
    print(f"   {existing_count} relationships already exist")
    
    # Build parent-child relationships
    relationships = []
    top_level_skills = []
    
    for skill_raw in skills:
        parent, strength = infer_parent_skill(skill_raw)
        
        if parent:
            # Check if parent exists in our skill set
            if parent in skills:
                relationships.append((skill_raw, parent, strength))
            else:
                # Parent doesn't exist, this becomes top-level
                top_level_skills.append(skill_raw)
        else:
            top_level_skills.append(skill_raw)
    
    print(f"   Found {len(relationships)} parent-child relationships")
    print(f"   Found {len(top_level_skills)} top-level skills")
    
    # Insert relationships
    inserted = 0
    errors = []
    
    for child, parent, strength in relationships:
        try:
            cur.execute("""
                INSERT INTO skill_hierarchy (skill, parent_skill, strength, created_by, notes)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (skill, parent_skill) DO NOTHING;
            """, (
                child,
                parent,
                strength,
                CREATED_BY,
                f"Inferred from skill taxonomy by Recipe 1121 import"
            ))
            inserted += 1
            
        except psycopg2.errors.ForeignKeyViolation as e:
            errors.append(f"FK violation: {child} -> {parent}")
        except Exception as e:
            errors.append(f"Error: {child} -> {parent}: {str(e)}")
    
    conn.commit()
    print(f"   ✅ Inserted {inserted} hierarchical relationships")
    
    if errors:
        print(f"   ⚠️  {len(errors)} errors (likely missing parent skills)")
        if len(errors) <= 10:
            for err in errors:
                print(f"      {err}")
    
    cur.close()
    return inserted, len(top_level_skills)

def generate_statistics(conn):
    """Generate final statistics"""
    cur = conn.cursor()
    
    print(f"\n📊 Final Statistics:")
    
    # Total skills
    cur.execute("SELECT COUNT(*) FROM skill_aliases WHERE created_by = %s;", (CREATED_BY,))
    new_skills = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM skill_aliases;")
    total_skills = cur.fetchone()[0]
    
    print(f"   Total skills in system: {total_skills}")
    print(f"   New skills from Recipe 1121: {new_skills}")
    
    # Hierarchy stats
    cur.execute("SELECT COUNT(*) FROM skill_hierarchy WHERE created_by = %s;", (CREATED_BY,))
    new_relations = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM skill_hierarchy;")
    total_relations = cur.fetchone()[0]
    
    print(f"   Total hierarchical relationships: {total_relations}")
    print(f"   New relationships from Recipe 1121: {new_relations}")
    
    # Skills by language
    cur.execute("""
        SELECT language, COUNT(*) 
        FROM skill_aliases 
        WHERE created_by = %s
        GROUP BY language;
    """, (CREATED_BY,))
    
    print(f"   Language distribution:")
    for lang, count in cur.fetchall():
        print(f"      {lang}: {count}")
    
    # Most connected skills
    cur.execute("""
        SELECT parent_skill, COUNT(*) as child_count
        FROM skill_hierarchy
        WHERE created_by = %s
        GROUP BY parent_skill
        ORDER BY child_count DESC
        LIMIT 5;
    """, (CREATED_BY,))
    
    print(f"   Top parent skills:")
    for parent, count in cur.fetchall():
        display_name = normalize_skill_name(parent)
        print(f"      {display_name}: {count} children")
    
    cur.close()

def main():
    """Main import process"""
    print("=" * 70)
    print("🚀 Recipe 1121 Skills Import to Skill Hierarchy")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected to base_yoga database\n")
        
        # Extract skills
        skills = extract_all_skills(conn)
        
        if not skills:
            print("❌ No skills found in postings!")
            return
        
        # Create skill aliases
        aliases_created = create_skill_aliases(conn, skills)
        
        # Create hierarchy
        relations_created, top_level_count = create_skill_hierarchy(conn, skills)
        
        # Generate statistics
        generate_statistics(conn)
        
        # Close connection
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ Import Complete!")
        print("=" * 70)
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
