#!/usr/bin/env python3
"""
Fix SkillBridge v2 Hierarchy
Populate hierarchy relationships from Recipe 1120, skipping self-loops
"""

import psycopg2
import re

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="base_yoga",
    user="base_admin",
    password="base_yoga_secure_2025"
)

def extract_and_populate_hierarchy():
    """Extract hierarchy from Recipe 1120 and populate, skipping errors"""
    
    cursor = conn.cursor()
    
    # Get all successful extractions
    cursor.execute("""
        SELECT 
            ir.response_received
        FROM instruction_runs ir
        JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
        JOIN recipe_runs rr ON sr.recipe_run_id = rr.recipe_run_id
        JOIN sessions s ON sr.session_id = s.session_id
        WHERE rr.recipe_id = 1120
          AND s.session_name = 'sb_technical_skills_phi3'
          AND rr.status = 'SUCCESS'
          AND ir.response_received LIKE '%+++OUTPUT START+++%'
          AND ir.response_received NOT LIKE '%FREIHEIT%'
    """)
    
    # Extract all skill paths
    hierarchy_pairs = set()
    
    for (response,) in cursor.fetchall():
        match = re.search(r'\+\+\+OUTPUT START\+\+\+(.*?)\+\+\+OUTPUT END\+\+\+', response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            for line in lines:
                parts = line.split('/')
                
                if len(parts) >= 3:
                    # Normalize to lowercase with underscores
                    category = parts[0].lower().replace(' ', '_').replace('-', '_')
                    subcategory = parts[1].lower().replace(' ', '_').replace('-', '_')
                    skill = parts[2].lower().replace(' ', '_').replace('-', '_')
                    
                    # Add both relationships
                    hierarchy_pairs.add((skill, subcategory))
                    hierarchy_pairs.add((subcategory, category))
                
                elif len(parts) == 2:
                    parent = parts[0].lower().replace(' ', '_').replace('-', '_')
                    skill = parts[1].lower().replace(' ', '_').replace('-', '_')
                    hierarchy_pairs.add((skill, parent))
    
    print(f"📊 Found {len(hierarchy_pairs)} unique hierarchy relationships")
    
    # Filter out self-loops and verify both skills exist
    valid_pairs = []
    skipped_self_loops = 0
    skipped_missing = 0
    
    for skill, parent_skill in hierarchy_pairs:
        # Skip self-loops
        if skill == parent_skill:
            skipped_self_loops += 1
            continue
        
        # Check if both skills exist in skill_aliases
        cursor.execute("SELECT COUNT(*) FROM skill_aliases WHERE skill = %s", (skill,))
        if cursor.fetchone()[0] == 0:
            skipped_missing += 1
            continue
            
        cursor.execute("SELECT COUNT(*) FROM skill_aliases WHERE skill = %s", (parent_skill,))
        if cursor.fetchone()[0] == 0:
            skipped_missing += 1
            continue
        
        valid_pairs.append((skill, parent_skill))
    
    print(f"✅ Valid relationships: {len(valid_pairs)}")
    print(f"⚠️  Skipped self-loops: {skipped_self_loops}")
    print(f"⚠️  Skipped missing skills: {skipped_missing}")
    
    # Insert relationships one by one (no transaction rollback on single errors)
    inserted = 0
    skipped_duplicates = 0
    errors = []
    
    for skill, parent_skill in valid_pairs:
        try:
            cursor.execute("""
                INSERT INTO skill_hierarchy (skill, parent_skill, strength, created_by)
                VALUES (%s, %s, 1.0, 'recipe_1120_fixed')
                ON CONFLICT (skill, parent_skill) DO NOTHING
            """, (skill, parent_skill))
            
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped_duplicates += 1
            
            conn.commit()  # Commit each one individually
            
        except Exception as e:
            conn.rollback()
            errors.append((skill, parent_skill, str(e)))
    
    print(f"\n✅ Successfully inserted: {inserted} relationships")
    print(f"⏭️  Skipped duplicates: {skipped_duplicates}")
    
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for skill, parent, error in errors[:10]:  # Show first 10
            print(f"   {skill} → {parent}: {error[:100]}")
    
    cursor.close()

def show_hierarchy_stats():
    """Display hierarchy statistics"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📊 HIERARCHY STATISTICS")
    print("="*80)
    
    cursor.execute("SELECT COUNT(*) FROM skill_hierarchy")
    total = cursor.fetchone()[0]
    print(f"Total hierarchy relationships: {total}")
    
    cursor.execute("SELECT COUNT(DISTINCT skill) FROM skill_hierarchy")
    children = cursor.fetchone()[0]
    print(f"Skills with parents: {children}")
    
    cursor.execute("""
        SELECT COUNT(DISTINCT sa.skill)
        FROM skill_aliases sa
        LEFT JOIN skill_hierarchy h ON sa.skill = h.skill
        WHERE h.skill IS NULL
    """)
    orphans = cursor.fetchone()[0]
    print(f"Orphan skills (no parent): {orphans}")
    
    cursor.execute("""
        SELECT COUNT(DISTINCT parent_skill)
        FROM skill_hierarchy
        WHERE parent_skill NOT IN (
            SELECT skill FROM skill_hierarchy
        )
    """)
    roots = cursor.fetchone()[0]
    print(f"Root-level categories: {roots}")
    
    # Show root categories
    print("\n🌳 Root Categories:")
    cursor.execute("""
        SELECT DISTINCT sa.display_name, sa.skill, COUNT(h.skill) as child_count
        FROM skill_aliases sa
        JOIN skill_hierarchy h ON sa.skill = h.parent_skill
        WHERE sa.skill NOT IN (
            SELECT skill FROM skill_hierarchy
        )
        GROUP BY sa.skill, sa.display_name
        ORDER BY child_count DESC
    """)
    
    for display, skill, count in cursor.fetchall():
        print(f"  📁 {display:30s} ({skill:30s}) - {count:3d} children")
    
    cursor.close()

if __name__ == '__main__':
    try:
        print("🚀 Fixing SkillBridge v2 Hierarchy\n")
        extract_and_populate_hierarchy()
        show_hierarchy_stats()
        print("\n✅ Done!")
    finally:
        conn.close()
