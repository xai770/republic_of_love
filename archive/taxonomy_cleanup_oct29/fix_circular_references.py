#!/usr/bin/env python3
"""
Fix Circular References in Taxonomy
====================================

Detects circular references in skill hierarchy and asks LLM to resolve them
by choosing the correct parent-child direction.

Created: 2025-10-29
Author: Arden
"""

import psycopg2
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

# LLM settings
LLM_MODEL = "qwen2.5:7b"
OUTPUT_DIR = Path('/home/xai/Documents/ty_learn/temp/circular_fixes')

def ask_llm(prompt):
    """Ask LLM taxonomy specialist"""
    
    result = subprocess.run(
        ['ollama', 'run', LLM_MODEL],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        raise Exception(f"Ollama error: {result.stderr}")
    
    return result.stdout.strip()

def parse_json_response(response):
    """Extract JSON from LLM response"""
    
    response = response.strip()
    response = response.replace('```json', '').replace('```', '').strip()
    
    # Find JSON object or array
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = response.find(start_char)
        end_idx = response.rfind(end_char)
        
        if start_idx != -1 and end_idx != -1:
            json_text = response[start_idx:end_idx+1]
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                continue
    
    return None

def detect_circular_references(conn):
    """Detect all circular references in hierarchy"""
    
    cur = conn.cursor()
    
    # Find skills that are both parent and child of each other
    cur.execute("""
        SELECT DISTINCT 
            h1.skill as skill_a,
            h1.parent_skill as skill_b,
            sa1.display_name as name_a,
            sa2.display_name as name_b
        FROM skill_hierarchy h1
        JOIN skill_hierarchy h2 ON h1.skill = h2.parent_skill 
                                AND h1.parent_skill = h2.skill
        JOIN skill_aliases sa1 ON h1.skill = sa1.skill
        JOIN skill_aliases sa2 ON h1.parent_skill = sa2.skill
        WHERE h1.skill < h1.parent_skill  -- Avoid duplicates
        ORDER BY sa1.display_name, sa2.display_name
    """)
    
    circular_pairs = cur.fetchall()
    cur.close()
    
    return circular_pairs

def get_skill_details(conn, skill_id):
    """Get details about a skill"""
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            skill,
            display_name,
            notes,
            created_by
        FROM skill_aliases
        WHERE skill = %s
    """, (skill_id,))
    
    result = cur.fetchone()
    cur.close()
    
    if result:
        return {
            'id': result[0],
            'name': result[1],
            'notes': result[2],
            'created_by': result[3]
        }
    return None

def get_children_count(conn, skill_id):
    """Count how many children a skill has"""
    
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) 
        FROM skill_hierarchy 
        WHERE parent_skill = %s
    """, (skill_id,))
    
    count = cur.fetchone()[0]
    cur.close()
    return count

def resolve_circular_pair(conn, skill_a_id, skill_b_id):
    """Ask LLM to resolve which should be parent/child"""
    
    # Get details about both skills
    skill_a = get_skill_details(conn, skill_a_id)
    skill_b = get_skill_details(conn, skill_b_id)
    
    # Get child counts
    a_children = get_children_count(conn, skill_a_id)
    b_children = get_children_count(conn, skill_b_id)
    
    # Create prompt
    prompt = f"""You are a taxonomy specialist. There is a circular reference in the skill hierarchy:

SKILL A:
- ID: {skill_a['id']}
- Name: {skill_a['name']}
- Has {a_children} child skills
- Created by: {skill_a['created_by']}
- Notes: {skill_a['notes'] or 'None'}

SKILL B:
- ID: {skill_b['id']}  
- Name: {skill_b['name']}
- Has {b_children} child skills
- Created by: {skill_b['created_by']}
- Notes: {skill_b['notes'] or 'None'}

Currently, Skill A is marked as a parent of Skill B, AND Skill B is marked as a parent of Skill A. This creates a circular reference.

Based on O*NET taxonomy standards and the skill names, which should be the parent and which should be the child?

Consider:
1. More general/broad skills should be parents of more specific skills
2. Category names should be parents of specific skill instances
3. Skills with more children are often higher in the hierarchy

Respond with JSON:
{{
  "parent": "SKILL_A_ID or SKILL_B_ID",
  "child": "SKILL_A_ID or SKILL_B_ID",
  "reason": "brief explanation of why this hierarchy makes sense"
}}

Respond with ONLY the JSON object, no other text."""

    print(f"\n💭 Asking {LLM_MODEL} about: {skill_a['name']} ↔ {skill_b['name']}")
    
    try:
        response = ask_llm(prompt)
        resolution = parse_json_response(response)
        
        if resolution:
            print(f"   ✓ Decision: {resolution.get('parent')} → {resolution.get('child')}")
            print(f"   Reason: {resolution.get('reason')}")
            return resolution
        else:
            print(f"   ⚠️  Could not parse LLM response")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def apply_resolution(conn, parent_id, child_id):
    """Remove incorrect relationship, keep correct one"""
    
    cur = conn.cursor()
    
    # Remove the incorrect relationship (where child is parent of parent)
    cur.execute("""
        DELETE FROM skill_hierarchy
        WHERE skill = %s AND parent_skill = %s
    """, (parent_id, child_id))
    
    deleted = cur.rowcount
    
    conn.commit()
    cur.close()
    
    return deleted

def main():
    """Main circular reference resolution process"""
    
    print("=" * 80)
    print("🔄 CIRCULAR REFERENCE RESOLUTION")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}\n")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Detect circular references
    print("📊 Detecting circular references...")
    circular_pairs = detect_circular_references(conn)
    
    print(f"   Found {len(circular_pairs)} circular reference pairs\n")
    
    if len(circular_pairs) == 0:
        print("✨ No circular references found! Hierarchy is clean.")
        conn.close()
        return
    
    # Show all circular pairs
    print("=" * 80)
    print("CIRCULAR REFERENCES FOUND:")
    print("=" * 80 + "\n")
    
    for i, (skill_a_id, skill_b_id, name_a, name_b) in enumerate(circular_pairs, 1):
        print(f"{i}. {name_a} ↔ {name_b}")
        print(f"   IDs: {skill_a_id} ↔ {skill_b_id}\n")
    
    # Process each circular pair
    print("=" * 80)
    print("RESOLVING CIRCULAR REFERENCES")
    print("=" * 80)
    
    resolutions = []
    
    for i, (skill_a_id, skill_b_id, name_a, name_b) in enumerate(circular_pairs, 1):
        print(f"\n[{i}/{len(circular_pairs)}] {name_a} ↔ {name_b}")
        
        resolution = resolve_circular_pair(conn, skill_a_id, skill_b_id)
        
        if resolution:
            resolutions.append({
                'skill_a': skill_a_id,
                'skill_b': skill_b_id,
                'name_a': name_a,
                'name_b': name_b,
                'parent': resolution['parent'],
                'child': resolution['child'],
                'reason': resolution['reason']
            })
    
    # Save resolution plan
    resolution_file = OUTPUT_DIR / f"resolutions_{timestamp}.json"
    with open(resolution_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'model': LLM_MODEL,
            'circular_pairs_found': len(circular_pairs),
            'resolutions': resolutions
        }, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"📋 RESOLUTION SUMMARY")
    print(f"{'='*80}\n")
    print(f"Circular pairs: {len(circular_pairs)}")
    print(f"Resolutions generated: {len(resolutions)}")
    print(f"\n📄 Plan saved to: {resolution_file}")
    
    if len(resolutions) == 0:
        print("\n⚠️  No valid resolutions generated.")
        conn.close()
        return
    
    # Show resolution plan
    print(f"\n{'='*80}")
    print("RESOLUTION PLAN:")
    print(f"{'='*80}\n")
    
    for res in resolutions:
        parent_name = res['name_a'] if res['parent'] == res['skill_a'] else res['name_b']
        child_name = res['name_b'] if res['parent'] == res['skill_a'] else res['name_a']
        print(f"✓ {parent_name} → {child_name}")
        print(f"  Reason: {res['reason']}\n")
    
    # Apply resolutions automatically
    print(f"{'='*80}")
    print(f"\n🔨 Applying resolutions automatically...\n")
    
    # Apply resolutions
    print(f"\n{'='*80}")
    print("🔨 APPLYING RESOLUTIONS")
    print(f"{'='*80}\n")
    
    stats = {'fixed': 0, 'errors': 0}
    
    for i, res in enumerate(resolutions, 1):
        parent_id = res['parent']
        child_id = res['child']
        parent_name = res['name_a'] if res['parent'] == res['skill_a'] else res['name_b']
        child_name = res['name_b'] if res['parent'] == res['skill_a'] else res['name_a']
        
        print(f"[{i}/{len(resolutions)}] Fixing: {parent_name} → {child_name}")
        
        try:
            deleted = apply_resolution(conn, parent_id, child_id)
            print(f"   ✓ Removed incorrect relationship ({deleted} records)")
            stats['fixed'] += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            stats['errors'] += 1
    
    conn.close()
    
    # Final summary
    print(f"\n{'='*80}")
    print("✅ CIRCULAR REFERENCE RESOLUTION COMPLETE")
    print(f"{'='*80}\n")
    print(f"📊 Statistics:")
    print(f"   Circular references fixed: {stats['fixed']}")
    print(f"   Errors: {stats['errors']}")
    print(f"\n📄 Resolutions: {resolution_file}")
    print(f"\n🔄 Next step: Re-export folder structure")
    print(f"   python3 export_skills_to_folders.py")
    print(f"\n{'='*80}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
