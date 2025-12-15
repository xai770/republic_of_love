#!/usr/bin/env python3
"""
Level-by-Level Taxonomy Deduplication
======================================

Processes each level of the hierarchy separately, asking LLM to deduplicate
siblings (skills/categories at the same level with the same parent).

This catches cases like:
- Speaking.md, Speaking Skills.md, Verbal Communication.md (all siblings under Communication Skills)

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
OUTPUT_DIR = Path('/home/xai/Documents/ty_learn/temp/level_dedup')

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

def get_siblings_by_parent(conn):
    """Get all skills grouped by their parent"""
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            h.parent_skill,
            sa_parent.display_name as parent_name,
            h.skill,
            sa_child.display_name as child_name
        FROM skill_hierarchy h
        JOIN skill_aliases sa_parent ON h.parent_skill = sa_parent.skill
        JOIN skill_aliases sa_child ON h.skill = sa_child.skill
        ORDER BY h.parent_skill, sa_child.display_name
    """)
    
    results = cur.fetchall()
    cur.close()
    
    # Group by parent
    siblings_by_parent = defaultdict(list)
    for parent_id, parent_name, child_id, child_name in results:
        siblings_by_parent[parent_id].append({
            'parent_name': parent_name,
            'child_id': child_id,
            'child_name': child_name
        })
    
    return siblings_by_parent

def deduplicate_siblings(conn, parent_id, siblings):
    """Ask LLM to deduplicate a set of siblings"""
    
    if len(siblings) < 2:
        return []
    
    parent_name = siblings[0]['parent_name']
    
    # Prepare sibling list
    sibling_list = [{'id': s['child_id'], 'name': s['child_name']} for s in siblings]
    
    prompt = f"""You are a taxonomy specialist. These {len(siblings)} skills/categories are all direct children of the same parent: "{parent_name}"

SIBLINGS (all under "{parent_name}"):
{json.dumps(sibling_list, indent=2)}

Identify which are duplicates/synonyms that should be merged. Look for:
1. Same concept with different wording ("Speaking" vs "Speaking Skills")
2. Abbreviations vs full names
3. Synonyms ("Verbal Communication" vs "Speaking")

Respond with a JSON array of merge groups:
[
  {{
    "canonical": "best name to keep",
    "canonical_id": "SKILL_ID_FROM_LIST",
    "merge_into_canonical": ["ID1", "ID2"],
    "reason": "why these are duplicates"
  }}
]

If no duplicates found, respond with: []

Respond with ONLY the JSON array."""

    try:
        response = ask_llm(prompt)
        merge_groups = parse_json_response(response)
        
        if merge_groups and len(merge_groups) > 0:
            return merge_groups
        
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    return []

def apply_merge(conn, old_skill, canonical_skill):
    """Merge old_skill into canonical_skill"""
    
    cur = conn.cursor()
    
    try:
        # Update children
        cur.execute("""
            UPDATE skill_hierarchy
            SET parent_skill = %s
            WHERE parent_skill = %s
        """, (canonical_skill, old_skill))
        
        children = cur.rowcount
        
        # Update parents (remove duplicates first)
        cur.execute("""
            DELETE FROM skill_hierarchy
            WHERE skill = %s AND parent_skill IN (
                SELECT parent_skill FROM skill_hierarchy
                WHERE skill = %s
            )
        """, (canonical_skill, old_skill))
        
        # Now update remaining
        cur.execute("""
            UPDATE skill_hierarchy
            SET skill = %s
            WHERE skill = %s
        """, (canonical_skill, old_skill))
        
        parents = cur.rowcount
        
        # Mark as merged
        cur.execute("""
            UPDATE skill_aliases
            SET notes = COALESCE(notes || ' | ', '') || 
                        'MERGED INTO: ' || %s || ' (Level dedup ' || %s || ')'
            WHERE skill = %s
        """, (canonical_skill, datetime.now().strftime('%Y-%m-%d'), old_skill))
        
        conn.commit()
        cur.close()
        
        return children, parents
        
    except Exception as e:
        conn.rollback()
        cur.close()
        raise e

def main():
    """Main level-by-level deduplication"""
    
    print("=" * 80)
    print("🧹 LEVEL-BY-LEVEL DEDUPLICATION")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}\n")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("📊 Grouping skills by parent...")
    siblings_by_parent = get_siblings_by_parent(conn)
    
    # Filter to only parents with 3+ children (more likely to have duplicates)
    candidates = {parent_id: siblings 
                  for parent_id, siblings in siblings_by_parent.items() 
                  if len(siblings) >= 3}
    
    print(f"   Found {len(candidates)} parent categories with 3+ children\n")
    
    all_merges = []
    
    for i, (parent_id, siblings) in enumerate(candidates.items(), 1):
        parent_name = siblings[0]['parent_name']
        
        print(f"[{i}/{len(candidates)}] Checking: {parent_name} ({len(siblings)} children)")
        
        merge_groups = deduplicate_siblings(conn, parent_id, siblings)
        
        if merge_groups:
            print(f"   ✓ Found {len(merge_groups)} merge groups")
            for group in merge_groups:
                print(f"      • {group['canonical']} ← {len(group['merge_into_canonical'])} items")
                all_merges.append({
                    'parent_id': parent_id,
                    'parent_name': parent_name,
                    **group
                })
        else:
            print(f"   ✓ No duplicates found")
    
    # Save merge plan
    plan_file = OUTPUT_DIR / f"level_dedup_plan_{timestamp}.json"
    with open(plan_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'model': LLM_MODEL,
            'parents_checked': len(candidates),
            'merge_groups': all_merges
        }, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"📋 DEDUPLICATION SUMMARY")
    print(f"{'='*80}\n")
    print(f"Parents checked: {len(candidates)}")
    print(f"Merge groups found: {len(all_merges)}")
    
    total_merges = sum(len(m['merge_into_canonical']) for m in all_merges)
    print(f"Total items to merge: {total_merges}")
    
    if len(all_merges) == 0:
        print("\n✨ No duplicates found at any level!")
        conn.close()
        return
    
    print(f"\n📄 Plan saved to: {plan_file}")
    
    # Show top merge targets
    print(f"\n{'='*80}")
    print("TOP MERGE TARGETS:")
    print(f"{'='*80}\n")
    
    sorted_merges = sorted(all_merges, 
                          key=lambda m: len(m['merge_into_canonical']), 
                          reverse=True)[:20]
    
    for merge in sorted_merges:
        print(f"• [{merge['parent_name']}] {merge['canonical']} ← {len(merge['merge_into_canonical'])} items")
        print(f"  Reason: {merge['reason']}")
    
    # Apply merges
    print(f"\n{'='*80}")
    print("🔨 APPLYING MERGES")
    print(f"{'='*80}\n")
    
    stats = {'merged': 0, 'relationships': 0, 'errors': 0}
    
    for i, merge in enumerate(all_merges, 1):
        canonical_id = merge['canonical_id']
        to_merge = merge['merge_into_canonical']
        
        print(f"[{i}/{len(all_merges)}] [{merge['parent_name']}] {merge['canonical']}")
        
        for old_id in to_merge:
            if old_id == canonical_id:
                continue
            
            try:
                children, parents = apply_merge(conn, old_id, canonical_id)
                stats['merged'] += 1
                stats['relationships'] += children + parents
                print(f"   ✓ {old_id} → {canonical_id}")
            except Exception as e:
                print(f"   ❌ {old_id}: {e}")
                stats['errors'] += 1
    
    conn.close()
    
    # Final summary
    print(f"\n{'='*80}")
    print("✅ LEVEL-BY-LEVEL DEDUPLICATION COMPLETE")
    print(f"{'='*80}\n")
    print(f"📊 Statistics:")
    print(f"   Items merged: {stats['merged']}")
    print(f"   Relationships updated: {stats['relationships']}")
    print(f"   Errors: {stats['errors']}")
    print(f"\n📄 Plan: {plan_file}")
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
