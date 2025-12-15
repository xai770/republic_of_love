#!/usr/bin/env python3
"""
Generic Sibling Deduplication
==============================

For ANY parent category, show LLM the direct children (siblings only),
ask it to identify duplicates and return a unique list with merge mappings.
Then automatically migrate all sub-folders from duplicates to the canonical.

Process:
1. Get direct children of a parent (siblings only, not descendants)
2. Ask LLM: "Which of these are duplicates? Return unique list + merge plan"
3. For each duplicate, move all its children to the canonical
4. Mark duplicate as merged

Fully generic - works on any parent at any level.

Created: 2025-10-29
Author: Arden
"""

import psycopg2
import json
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

# LLM settings
LLM_MODEL = "qwen2.5:7b"
OUTPUT_DIR = Path('/home/xai/Documents/ty_learn/temp/sibling_dedup')

def ask_llm(prompt):
    """Ask LLM"""
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
    response = response.strip().replace('```json', '').replace('```', '').strip()
    
    start_idx = response.find('[')
    end_idx = response.rfind(']')
    
    if start_idx != -1 and end_idx != -1:
        json_text = response[start_idx:end_idx+1]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None
    
    return None

def get_direct_children(conn, parent_id):
    """Get ONLY direct children (siblings), not all descendants"""
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            h.skill,
            sa.display_name
        FROM skill_hierarchy h
        JOIN skill_aliases sa ON h.skill = sa.skill
        WHERE h.parent_skill = %s
        ORDER BY sa.display_name
    """, (parent_id,))
    
    results = cur.fetchall()
    cur.close()
    
    return [{'id': skill_id, 'name': display_name} for skill_id, display_name in results]

def deduplicate_siblings(conn, parent_id, parent_name, siblings):
    """Ask LLM to identify duplicates and return unique list"""
    
    if len(siblings) < 2:
        return []
    
    prompt = f"""You are a taxonomy specialist. These {len(siblings)} skills/categories are ALL DIRECT CHILDREN of "{parent_name}" (they are siblings at the same level).

SIBLINGS:
{json.dumps(siblings, indent=2)}

Task: Identify which are duplicates/synonyms that refer to the same concept.

Return a JSON array of merge groups:
[
  {{
    "canonical_name": "best name to keep",
    "canonical_id": "ID_FROM_LIST",
    "duplicates": ["ID1", "ID2", ...],
    "reason": "why these are the same concept"
  }}
]

Focus on:
- Exact synonyms (e.g., "Data Analysis" vs "Data Analysis Methods")
- Abbreviations (e.g., "IT Security" vs "Information Technology Security")
- Redundant qualifiers (e.g., "Security" vs "Security And Compliance")
- Incomplete names (e.g., "Security And " with trailing space)

Be conservative. Only merge if you're confident they're the SAME concept.

If NO duplicates found, return: []

Respond with ONLY the JSON array."""

    try:
        response = ask_llm(prompt)
        merge_groups = parse_json_response(response)
        return merge_groups if merge_groups else []
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return []

def migrate_children(conn, from_parent, to_parent):
    """Move all children from from_parent to to_parent"""
    
    cur = conn.cursor()
    
    try:
        # Get count of children
        cur.execute("""
            SELECT COUNT(*) FROM skill_hierarchy
            WHERE parent_skill = %s
        """, (from_parent,))
        
        child_count = cur.fetchone()[0]
        
        if child_count == 0:
            cur.close()
            return 0
        
        # Remove duplicates that would be created
        cur.execute("""
            DELETE FROM skill_hierarchy
            WHERE parent_skill = %s
            AND skill IN (
                SELECT skill FROM skill_hierarchy
                WHERE parent_skill = %s
            )
        """, (to_parent, from_parent))
        
        # Move remaining children
        cur.execute("""
            UPDATE skill_hierarchy
            SET parent_skill = %s
            WHERE parent_skill = %s
        """, (to_parent, from_parent))
        
        moved = cur.rowcount
        
        # Remove the now-empty parent from hierarchy
        cur.execute("""
            DELETE FROM skill_hierarchy
            WHERE skill = %s
        """, (from_parent,))
        
        # Mark as merged
        cur.execute("""
            UPDATE skill_aliases
            SET notes = COALESCE(notes || ' | ', '') || 
                        'MERGED INTO: ' || %s || ' (Sibling dedup ' || %s || ')'
            WHERE skill = %s
        """, (to_parent, datetime.now().strftime('%Y-%m-%d'), from_parent))
        
        conn.commit()
        cur.close()
        
        return moved
        
    except Exception as e:
        conn.rollback()
        cur.close()
        raise e

def process_parent(conn, parent_id, parent_name):
    """Process one parent: deduplicate its direct children"""
    
    print(f"\n{'='*80}")
    print(f"Processing: {parent_name} ({parent_id})")
    print(f"{'='*80}\n")
    
    # Get direct children only
    siblings = get_direct_children(conn, parent_id)
    
    print(f"   Found {len(siblings)} direct children")
    
    if len(siblings) < 2:
        print(f"   ✓ Too few children to have duplicates\n")
        return {'parent': parent_name, 'merged': 0, 'children_moved': 0}
    
    # Ask LLM to identify duplicates
    print(f"   🤖 Asking {LLM_MODEL} to identify duplicates...")
    merge_groups = deduplicate_siblings(conn, parent_id, parent_name, siblings)
    
    if not merge_groups or len(merge_groups) == 0:
        print(f"   ✓ No duplicates found\n")
        return {'parent': parent_name, 'merged': 0, 'children_moved': 0}
    
    print(f"   ✓ Found {len(merge_groups)} merge groups\n")
    
    # Show merge plan
    total_duplicates = sum(len(g.get('duplicates', [])) for g in merge_groups)
    print(f"   📋 MERGE PLAN ({total_duplicates} duplicates):")
    for group in merge_groups:
        print(f"      • Keep: {group['canonical_name']}")
        print(f"        Merge: {', '.join(group.get('duplicates', []))}")
        print(f"        Reason: {group['reason']}\n")
    
    # Apply merges
    print(f"   🔨 Applying merges...\n")
    
    stats = {'merged': 0, 'children_moved': 0}
    
    for group in merge_groups:
        canonical_id = group['canonical_id']
        duplicates = group.get('duplicates', [])
        
        for dup_id in duplicates:
            if dup_id == canonical_id:
                continue
            
            try:
                moved = migrate_children(conn, dup_id, canonical_id)
                print(f"      ✓ {dup_id} → {canonical_id} ({moved} children moved)")
                stats['merged'] += 1
                stats['children_moved'] += moved
            except Exception as e:
                print(f"      ❌ {dup_id}: {e}")
    
    print()
    return {'parent': parent_name, **stats}

def find_all_parents(conn):
    """Find all skills that are parents (have children)"""
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT 
            h.parent_skill,
            sa.display_name,
            COUNT(*) as child_count
        FROM skill_hierarchy h
        JOIN skill_aliases sa ON h.parent_skill = sa.skill
        GROUP BY h.parent_skill, sa.display_name
        HAVING COUNT(*) >= 3  -- Only parents with 3+ children
        ORDER BY COUNT(*) DESC
    """)
    
    results = cur.fetchall()
    cur.close()
    
    return [(parent_id, parent_name, count) for parent_id, parent_name, count in results]

def main():
    """Main generic sibling deduplication"""
    
    print("=" * 80)
    print("🔄 GENERIC SIBLING DEDUPLICATION")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}")
    print(f"Strategy: Process each parent separately, deduplicate its direct children\n")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("📊 Finding all parent categories with 3+ children...")
    parents = find_all_parents(conn)
    
    print(f"   Found {len(parents)} parents to process\n")
    
    if len(parents) == 0:
        print("✨ No parents with 3+ children found!")
        conn.close()
        return
    
    # Process each parent
    all_results = []
    
    for i, (parent_id, parent_name, child_count) in enumerate(parents, 1):
        print(f"[{i}/{len(parents)}] {parent_name} ({child_count} children)")
        result = process_parent(conn, parent_id, parent_name)
        all_results.append(result)
    
    conn.close()
    
    # Save results
    results_file = OUTPUT_DIR / f"sibling_dedup_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'model': LLM_MODEL,
            'parents_processed': len(parents),
            'results': all_results
        }, f, indent=2)
    
    # Summary
    total_merged = sum(r['merged'] for r in all_results)
    total_children_moved = sum(r['children_moved'] for r in all_results)
    
    print(f"\n{'='*80}")
    print("✅ GENERIC DEDUPLICATION COMPLETE")
    print(f"{'='*80}\n")
    print(f"📊 Statistics:")
    print(f"   Parents processed: {len(parents)}")
    print(f"   Siblings merged: {total_merged}")
    print(f"   Children migrated: {total_children_moved}")
    print(f"\n📄 Results: {results_file}")
    print(f"\n🔄 Next: Re-export folder structure")
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
