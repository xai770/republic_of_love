#!/usr/bin/env python3
"""
Auto-Categorize Skills Using O*NET Taxonomy
===========================================

Uses LLM knowledge of O*NET to automatically categorize all skills
and build the hierarchy in the database.

Strategy:
1. Fetch all 287 skills from database
2. For each skill, ask LLM to place it in O*NET taxonomy
3. Parse the hierarchy path (e.g., TECHNICAL > IT > NETWORKING > Network Architecture)
4. Create skill_aliases entries for parent categories (if missing)
5. Create skill_hierarchy relationships
6. Validate consistency across models (optional multi-model consensus)

Created: 2025-10-29
Author: Arden
"""

import psycopg2
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

# Model to use (best performer from interviews)
MODEL = "qwen2.5:7b"  # qwen gave most structured answers
CREATED_BY = f"Auto_ONET_Categorization_{datetime.now().strftime('%Y%m%d')}"

def fetch_all_skills_to_categorize(conn):
    """Get all skills that need categorization"""
    cur = conn.cursor()
    
    # Get skills from Recipe 1121 (our 287 extracted skills)
    cur.execute("""
        SELECT DISTINCT skill, display_name
        FROM skill_aliases
        WHERE created_by = 'Recipe_1121_Import_2025-10-29'
        ORDER BY skill
    """)
    
    skills = [{'skill': row[0], 'display_name': row[1]} for row in cur.fetchall()]
    cur.close()
    
    return skills

def ask_llm_for_onet_path(skill_display_name, model=MODEL):
    """Ask LLM to categorize skill into O*NET taxonomy"""
    
    prompt = f"""Using the O*NET taxonomy standard, categorize this skill:

Skill: {skill_display_name}

Provide the COMPLETE hierarchical path from top-level category down to this specific skill.

Format your response as a clean path using > separators, like:
TECHNICAL_SKILLS > IT_INFRASTRUCTURE > NETWORKING > Network Architecture

Rules:
- Use underscores for multi-word categories (e.g., TECHNICAL_SKILLS not "Technical Skills")
- Go as deep as needed (2-5 levels typical)
- Top level should be one of: TECHNICAL_SKILLS, BUSINESS_SKILLS, SOFT_SKILLS, MANAGEMENT_SKILLS, COMMUNICATION_SKILLS, INDUSTRY_KNOWLEDGE, PERSONAL_ATTRIBUTES
- Be specific but not overly granular

Respond with ONLY the path, no explanation:"""
    
    # Use llm_chat.py to get response
    try:
        # Clear conversation
        subprocess.run(
            ['python3', 'llm_chat.py', model, 'clear'],
            capture_output=True,
            timeout=10
        )
        
        # Ask for categorization
        result = subprocess.run(
            ['python3', 'llm_chat.py', model, 'send', prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse response from conversation file
        conv_file = Path(f"temp/conversation_{model.replace(':', '_').replace('.', '_')}.json")
        if conv_file.exists():
            with open(conv_file, 'r') as f:
                history = json.load(f)
                if history and history[-1]['role'] == 'assistant':
                    response = history[-1]['content']
                    return response.strip()
        
        return None
        
    except Exception as e:
        print(f"   ⚠️  Error asking LLM: {e}")
        return None

def parse_onet_path(response_text):
    """Extract clean path from LLM response"""
    
    # Look for paths with > separator
    lines = response_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if '>' in line:
            # Clean up the line
            # Remove markdown, bullets, etc.
            line = re.sub(r'^[*\-•]\s*', '', line)
            line = re.sub(r'^\d+\.\s*', '', line)
            
            # Extract just the path part
            parts = [p.strip() for p in line.split('>')]
            
            # Validate: should have 2+ parts, all uppercase/underscore style
            if len(parts) >= 2:
                # Normalize to uppercase with underscores
                normalized = []
                for part in parts:
                    # Convert to uppercase and replace spaces with underscores
                    normalized_part = part.upper().replace(' ', '_').replace('-', '_')
                    # Remove special characters
                    normalized_part = re.sub(r'[^A-Z0-9_]', '', normalized_part)
                    if normalized_part:
                        normalized.append(normalized_part)
                
                if len(normalized) >= 2:
                    return normalized
    
    return None

def ensure_skill_exists(conn, skill_name, display_name, created_by, notes=""):
    """Ensure a skill exists in skill_aliases (create if missing)"""
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO skill_aliases (skill_alias, skill, display_name, language, confidence, created_by, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (skill_alias) DO NOTHING
            RETURNING skill_alias
        """, (
            skill_name,
            skill_name,
            display_name,
            'en',  # O*NET is English-based
            0.90,  # High confidence - from O*NET standard
            created_by,
            notes
        ))
        
        inserted = cur.fetchone()
        conn.commit()
        return bool(inserted)
        
    except Exception as e:
        print(f"   ⚠️  Error ensuring skill {skill_name}: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

def create_hierarchy_from_path(conn, path, original_skill, created_by):
    """Create all parent-child relationships from the path"""
    
    if not path or len(path) < 2:
        return 0
    
    relationships_created = 0
    
    # Ensure all nodes in the path exist as skills
    for i, node in enumerate(path):
        # Create human-readable display name
        display_name = node.replace('_', ' ').title()
        
        # Categorize node type
        if i == 0:
            notes = "O*NET top-level category"
        elif i == len(path) - 1:
            notes = f"Leaf skill (original: {original_skill})"
        else:
            notes = f"O*NET intermediate category (level {i+1})"
        
        ensure_skill_exists(conn, node, display_name, created_by, notes)
    
    # Create parent-child relationships
    cur = conn.cursor()
    
    for i in range(len(path) - 1):
        child = path[i + 1]
        parent = path[i]
        
        # Calculate strength based on distance from leaf
        # Closer to leaf = stronger relationship
        distance_from_leaf = len(path) - i - 2
        strength = max(0.7, 1.0 - (distance_from_leaf * 0.1))
        
        try:
            cur.execute("""
                INSERT INTO skill_hierarchy (skill, parent_skill, strength, created_by, notes)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (skill, parent_skill) DO UPDATE
                SET strength = EXCLUDED.strength,
                    notes = EXCLUDED.notes
                RETURNING skill
            """, (
                child,
                parent,
                strength,
                created_by,
                f"Auto-categorized using O*NET via {MODEL}"
            ))
            
            if cur.fetchone():
                relationships_created += 1
                
        except Exception as e:
            print(f"   ⚠️  Error creating relationship {child} -> {parent}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    
    return relationships_created

def categorize_all_skills():
    """Main function to categorize all skills"""
    
    print("=" * 80)
    print("🏗️  AUTO-CATEGORIZE SKILLS USING O*NET TAXONOMY")
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"Created by: {CREATED_BY}\n")
    
    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Fetch skills to categorize
    print("📥 Fetching skills to categorize...")
    skills = fetch_all_skills_to_categorize(conn)
    print(f"   Found {len(skills)} skills from Recipe 1121\n")
    
    # Statistics
    total_skills = len(skills)
    categorized = 0
    failed = 0
    relationships_created = 0
    
    # Process each skill
    print("🔍 Categorizing skills...\n")
    
    for i, skill_data in enumerate(skills, 1):
        skill = skill_data['skill']
        display_name = skill_data['display_name']
        
        print(f"[{i}/{total_skills}] {display_name}")
        
        # Ask LLM for O*NET path
        response = ask_llm_for_onet_path(display_name, MODEL)
        
        if not response:
            print(f"   ❌ No response from LLM")
            failed += 1
            continue
        
        # Parse the path
        path = parse_onet_path(response)
        
        if not path:
            print(f"   ❌ Could not parse path from: {response[:100]}...")
            failed += 1
            continue
        
        # Show the path
        path_str = ' > '.join(path)
        print(f"   ✓ {path_str}")
        
        # Create hierarchy in database
        count = create_hierarchy_from_path(conn, path, skill, CREATED_BY)
        relationships_created += count
        categorized += 1
        
        print(f"   📊 Created {count} relationships\n")
        
        # Progress checkpoint every 25 skills
        if i % 25 == 0:
            print(f"\n{'='*80}")
            print(f"CHECKPOINT: {i}/{total_skills} skills processed")
            print(f"Categorized: {categorized}, Failed: {failed}, Relationships: {relationships_created}")
            print(f"{'='*80}\n")
    
    # Final statistics
    print("\n" + "=" * 80)
    print("✅ CATEGORIZATION COMPLETE")
    print("=" * 80)
    print(f"\n📊 Final Statistics:")
    print(f"   Total skills: {total_skills}")
    print(f"   Successfully categorized: {categorized} ({100*categorized/total_skills:.1f}%)")
    print(f"   Failed: {failed}")
    print(f"   Relationships created: {relationships_created}")
    print(f"   Average depth: {relationships_created/categorized:.1f}" if categorized > 0 else "")
    
    # Query final hierarchy stats
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(DISTINCT parent_skill) 
        FROM skill_hierarchy 
        WHERE created_by = %s
    """, (CREATED_BY,))
    unique_parents = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(DISTINCT skill) 
        FROM skill_hierarchy 
        WHERE created_by = %s
    """, (CREATED_BY,))
    unique_children = cur.fetchone()[0]
    
    print(f"\n🌳 Hierarchy Structure:")
    print(f"   Parent categories created: {unique_parents}")
    print(f"   Child skills linked: {unique_children}")
    
    # Show top-level categories
    cur.execute("""
        SELECT DISTINCT parent_skill, COUNT(skill) as children
        FROM skill_hierarchy
        WHERE created_by = %s
        AND parent_skill NOT IN (SELECT skill FROM skill_hierarchy WHERE created_by = %s)
        GROUP BY parent_skill
        ORDER BY children DESC
    """, (CREATED_BY, CREATED_BY))
    
    print(f"\n🏆 Top-Level Categories:")
    for parent, count in cur.fetchall():
        display = parent.replace('_', ' ').title()
        print(f"   {display}: {count} direct children")
    
    cur.close()
    conn.close()
    
    print(f"\n💾 To view in Protégé: Re-run export_skills_to_owl.py")
    print("=" * 80)

if __name__ == "__main__":
    try:
        categorize_all_skills()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
