#!/usr/bin/env python3
"""
Recursive Complete Taxonomy Deduplication
==========================================

Recursively processes EVERY folder/category at EVERY level,
asking Qwen to deduplicate siblings, then recurses into children.

Process:
1. Start at root (skills with no parent)
2. For EACH category, get its direct children
3. Ask Qwen to deduplicate those children
4. Apply merges
5. Recurse into each child
6. Repeat until entire tree is processed

This guarantees we touch every level, including:
- Root categories (no parent)
- Categories with only 2 children
- Deep nested categories

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
OUTPUT_DIR = Path('/home/xai/Documents/ty_learn/temp/recursive_dedup')

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
    """Get ONLY direct children (siblings)"""
    
    cur = conn.cursor()
    
    # If parent_id is None, get root categories
    # (categories that are parents but don't have a parent themselves)
    if parent_id is None:
        cur.execute("""
            SELECT DISTINCT
                sa.skill,
                sa.display_name
            FROM skill_aliases sa
            WHERE sa.skill IN (
                -- Skills that are parents (have children)
                SELECT DISTINCT parent_skill FROM skill_hierarchy
            )
            AND sa.skill NOT IN (
                -- But are not children themselves
                SELECT DISTINCT skill FROM skill_hierarchy
            )
            ORDER BY sa.display_name
        """)
    else:
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

def deduplicate_siblings(conn, parent_id, parent_name, siblings, depth):
    """Ask LLM to identify duplicates"""
    
    if len(siblings) < 2:
        return []
    
    indent = "  " * depth
    
    prompt = f"""You are a taxonomy specialist. These {len(siblings)} categories are ALL DIRECT CHILDREN of "{parent_name or 'ROOT'}" (siblings at same level).

SIBLINGS:
{json.dumps(siblings, indent=2)}

Task: Identify duplicates/synonyms that refer to the SAME concept.

Return JSON array of merge groups:
[
  {{
    "canonical_name": "best name to keep",
    "canonical_id": "ID_FROM_LIST",
    "duplicates": ["ID1", "ID2"],
    "reason": "why these are same concept"
  }}
]

Focus on:
- Exact synonyms (e.g., "Technical" vs "Technical Skills")
- Abbreviations
- Redundant qualifiers
- Incomplete names (trailing spaces, etc.)

Be conservative. Only merge if SAME concept.

If NO duplicates: []

Respond with ONLY the JSON array."""

    try:
        response = ask_llm(prompt)
        merge_groups = parse_json_response(response)
        return merge_groups if merge_groups else []
    except Exception as e:
        print(f"{indent}   ⚠️  Error: {e}")
        return []

def migrate_children(conn, from_parent, to_parent):
    """Move all children from from_parent to to_parent"""
    
    cur = conn.cursor()
    
    try:
        # Remove duplicates first
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
                        'MERGED INTO: ' || %s || ' (Recursive dedup ' || %s || ')'
            WHERE skill = %s
        """, (to_parent, datetime.now().strftime('%Y-%m-%d'), from_parent))
        
        conn.commit()
        cur.close()
        
        return moved
        
    except Exception as e:
        conn.rollback()
        cur.close()
        raise e

def process_category_recursive(conn, category_id, category_name, depth, stats, visited=None):
    """Recursively process a category and all its descendants"""
    
    # Track visited nodes to detect cycles
    if visited is None:
        visited = set()
    
    # Cycle detection
    if category_id in visited:
        indent = "  " * depth
        print(f"{indent}⚠️  CYCLE DETECTED: {category_name} already visited in this path, skipping\n")
        return
    
    # Add current node to visited set (modify in place, don't create new set!)
    visited.add(category_id)
    
    indent = "  " * depth
    
    # Safety limit
    if depth > 20:
        print(f"{indent}⚠️  MAX DEPTH ({depth}) reached for {category_name}, stopping\n")
        visited.remove(category_id)  # Backtrack
        return
    
    print(f"{indent}[Depth {depth}] Processing: {category_name or 'ROOT'}")
    
    # Get direct children
    children = get_direct_children(conn, category_id)
    
    if len(children) == 0:
        print(f"{indent}   ✓ Leaf node (no children)\n")
        visited.remove(category_id)  # Backtrack
        return
    
    print(f"{indent}   Found {len(children)} direct children")
    
    if len(children) < 2:
        print(f"{indent}   ✓ Only 1 child, no duplicates possible")
        # Still recurse into that child
        child = children[0]
        process_category_recursive(conn, child['id'], child['name'], depth + 1, stats, visited)
        visited.remove(category_id)  # Backtrack
        return
    
    # Ask LLM to deduplicate
    print(f"{indent}   🤖 Asking Qwen to deduplicate...")
    merge_groups = deduplicate_siblings(conn, category_id, category_name, children, depth)
    
    if not merge_groups or len(merge_groups) == 0:
        print(f"{indent}   ✓ No duplicates found")
    else:
        print(f"{indent}   ✓ Found {len(merge_groups)} merge groups")
        
        # Apply merges
        for group in merge_groups:
            canonical_id = group['canonical_id']
            duplicates = group.get('duplicates', [])
            
            print(f"{indent}      • Keep: {group['canonical_name']}")
            print(f"{indent}        Merge: {', '.join(duplicates)}")
            
            for dup_id in duplicates:
                if dup_id == canonical_id:
                    continue
                
                try:
                    moved = migrate_children(conn, dup_id, canonical_id)
                    print(f"{indent}        ✓ {dup_id} → {canonical_id} ({moved} children)")
                    stats['merged'] += 1
                    stats['children_moved'] += moved
                except Exception as e:
                    print(f"{indent}        ❌ {dup_id}: {e}")
                    stats['errors'] += 1
        
        # Re-fetch children after merges
        children = get_direct_children(conn, category_id)
    
    print(f"{indent}   ↓ Recursing into {len(children)} children...\n")
    
    # Recurse into each child
    for child in children:
        process_category_recursive(conn, child['id'], child['name'], depth + 1, stats, visited)
    
    # Backtrack: remove current node from visited when done with this subtree
    visited.remove(category_id)

def main():
    """Main recursive deduplication"""
    
    print("=" * 80)
    print("🌳 RECURSIVE COMPLETE TAXONOMY DEDUPLICATION")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}")
    print(f"Strategy: Recursively process EVERY level from root to leaves\n")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    stats = {
        'merged': 0,
        'children_moved': 0,
        'errors': 0
    }
    
    print("Starting at ROOT level...\n")
    
    # Start with root (parent_id = None)
    process_category_recursive(conn, None, None, 0, stats)
    
    conn.close()
    
    # Save results
    results_file = OUTPUT_DIR / f"recursive_dedup_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'model': LLM_MODEL,
            'stats': stats
        }, f, indent=2)
    
    # Summary
    print(f"\n{'='*80}")
    print("✅ RECURSIVE DEDUPLICATION COMPLETE")
    print(f"{'='*80}\n")
    print(f"📊 Statistics:")
    print(f"   Categories merged: {stats['merged']}")
    print(f"   Children migrated: {stats['children_moved']}")
    print(f"   Errors: {stats['errors']}")
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
