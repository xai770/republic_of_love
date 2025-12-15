#!/usr/bin/env python3
"""
Batch Taxonomy Cleanup with LLM Specialist
==========================================

Processes entire skill hierarchy in batches, asking an LLM taxonomy specialist
to identify synonyms and suggest canonical forms.

Creates a new cleaned hierarchy version for comparison.

Process:
1. Extract all categories from database
2. Process in batches of 15 categories
3. Collect all merge suggestions
4. Apply merges to create cleaned hierarchy
5. Export both versions for comparison

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
BATCH_SIZE = 15
OUTPUT_DIR = Path('/home/xai/Documents/ty_learn/temp/taxonomy_cleanup')

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
    
    # Find JSON array
    start_idx = response.find('[')
    end_idx = response.rfind(']')
    
    if start_idx != -1 and end_idx != -1:
        json_text = response[start_idx:end_idx+1]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"   ⚠️  JSON parse error: {e}")
            return None
    
    return None

def get_all_categories(conn):
    """Get all unique categories from skill_hierarchy"""
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT sa.skill, sa.display_name, sa.created_by
        FROM skill_aliases sa
        WHERE sa.skill IN (
            SELECT DISTINCT parent_skill FROM skill_hierarchy
        )
        ORDER BY sa.display_name
    """)
    
    categories = cur.fetchall()
    cur.close()
    
    return categories

def validate_merge_group(group, valid_skill_ids):
    """Validate that all skill IDs in merge group actually exist"""
    
    canonical_id = group.get('canonical_id')
    merge_list = group.get('merge_into_canonical', [])
    
    # Check canonical exists
    if canonical_id not in valid_skill_ids:
        return None
    
    # Filter merge list to only valid IDs
    valid_merges = [skill_id for skill_id in merge_list 
                    if skill_id in valid_skill_ids and skill_id != canonical_id]
    
    if len(valid_merges) == 0:
        # No valid merges, skip this group
        return None
    
    # Return cleaned group
    return {
        'canonical': group.get('canonical'),
        'canonical_id': canonical_id,
        'merge_into_canonical': valid_merges,
        'reason': group.get('reason')
    }

def process_batch(batch, batch_num, all_skill_ids):
    """Process a batch of categories with LLM"""
    
    print(f"\n{'='*80}")
    print(f"📦 BATCH {batch_num} ({len(batch)} categories)")
    print(f"{'='*80}\n")
    
    # Prepare category list
    category_list = [{'id': skill_id, 'name': display_name} 
                    for skill_id, display_name, _ in batch]
    
    # Create prompt
    prompt = f"""You are a taxonomy specialist. Analyze these {len(batch)} skill category names and identify groups of synonyms/duplicates that should be consolidated.

CATEGORIES:
{json.dumps(category_list, indent=2)}

Identify merge groups where:
1. Names are obvious synonyms (e.g., "IT Security" vs "Information Security")
2. Abbreviations vs full names (e.g., "Risk Mgmt" vs "Risk Management")  
3. Redundant qualifiers (e.g., "Risk Management Skills" vs "Risk Management")

CRITICAL: Only suggest skill IDs that appear in the CATEGORIES list above. Do not invent new IDs.

Respond with a JSON array of merge groups:
[
  {{
    "canonical": "best name to keep",
    "canonical_id": "SKILL_ID_FROM_LIST_ABOVE",
    "merge_into_canonical": ["ID1_FROM_LIST", "ID2_FROM_LIST"],
    "reason": "brief explanation"
  }}
]

If no merges are needed, respond with an empty array: []

Respond with ONLY the JSON array, no other text."""

    print(f"💭 Asking {LLM_MODEL} to analyze batch...")
    
    try:
        response = ask_llm(prompt)
        merge_groups = parse_json_response(response)
        
        if merge_groups is None:
            print(f"   ⚠️  Could not parse response, skipping batch")
            return []
        
        # Validate all merge groups
        validated_groups = []
        for group in merge_groups:
            validated = validate_merge_group(group, all_skill_ids)
            if validated:
                validated_groups.append(validated)
        
        print(f"   ✓ Found {len(validated_groups)} valid merge groups")
        
        for group in validated_groups:
            print(f"      • {group['canonical']} ← {len(group['merge_into_canonical'])} items")
        
        return validated_groups
        
    except Exception as e:
        print(f"   ❌ Error processing batch: {e}")
        return []

def create_merge_mapping(all_merge_groups):
    """Create a mapping of old_id → canonical_id"""
    
    merge_map = {}
    
    for group in all_merge_groups:
        canonical_id = group['canonical_id']
        for old_id in group['merge_into_canonical']:
            merge_map[old_id] = canonical_id
    
    return merge_map

def apply_merges_to_database(conn, merge_map):
    """Apply merge mapping to database"""
    
    print(f"\n{'='*80}")
    print(f"🔨 APPLYING {len(merge_map)} MERGES TO DATABASE")
    print(f"{'='*80}\n")
    
    cur = conn.cursor()
    
    stats = {
        'merged': 0,
        'children_updated': 0,
        'parents_updated': 0
    }
    
    for i, (old_id, canonical_id) in enumerate(merge_map.items(), 1):
        print(f"[{i}/{len(merge_map)}] {old_id} → {canonical_id}")
        
        try:
            # Update children: old_id as parent → canonical_id as parent
            cur.execute("""
                UPDATE skill_hierarchy
                SET parent_skill = %s
                WHERE parent_skill = %s
            """, (canonical_id, old_id))
            children_updated = cur.rowcount
            
            # Update parents: old_id as child → canonical_id as child
            cur.execute("""
                UPDATE skill_hierarchy
                SET skill = %s
                WHERE skill = %s
            """, (canonical_id, old_id))
            parents_updated = cur.rowcount
            
            # Mark old skill as deprecated
            cur.execute("""
                UPDATE skill_aliases
                SET notes = COALESCE(notes || ' | ', '') || 
                            'MERGED INTO: ' || %s || ' (Taxonomy Cleanup ' || %s || ')'
                WHERE skill = %s
            """, (canonical_id, datetime.now().strftime('%Y-%m-%d'), old_id))
            
            stats['merged'] += 1
            stats['children_updated'] += children_updated
            stats['parents_updated'] += parents_updated
            
            print(f"   ✓ {children_updated} children, {parents_updated} parents updated")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    
    return stats

def main():
    """Main batch cleanup process"""
    
    print("=" * 80)
    print("🎓 TAXONOMY SPECIALIST - BATCH CLEANUP")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}")
    print(f"Batch size: {BATCH_SIZE} categories")
    print()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Get all categories
    print("📊 Loading all categories...")
    all_categories = get_all_categories(conn)
    print(f"   Found {len(all_categories)} total categories\n")
    
    # Create set of valid skill IDs for validation
    all_skill_ids = {cat[0] for cat in all_categories}
    
    # Process in batches
    all_merge_groups = []
    
    for i in range(0, len(all_categories), BATCH_SIZE):
        batch = all_categories[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        merge_groups = process_batch(batch, batch_num, all_skill_ids)
        all_merge_groups.extend(merge_groups)
    
    # Save merge plan
    merge_plan_file = OUTPUT_DIR / f"merge_plan_{timestamp}.json"
    with open(merge_plan_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'model': LLM_MODEL,
            'total_categories': len(all_categories),
            'batches_processed': (len(all_categories) + BATCH_SIZE - 1) // BATCH_SIZE,
            'total_merge_groups': len(all_merge_groups),
            'merge_groups': all_merge_groups
        }, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"📋 MERGE PLAN SUMMARY")
    print(f"{'='*80}\n")
    print(f"Total categories analyzed: {len(all_categories)}")
    print(f"Merge groups identified: {len(all_merge_groups)}")
    
    total_merges = sum(len(g['merge_into_canonical']) for g in all_merge_groups)
    print(f"Total categories to merge: {total_merges}")
    print(f"\n📄 Plan saved to: {merge_plan_file}")
    
    if len(all_merge_groups) == 0:
        print("\n✨ No merges needed - hierarchy is already clean!")
        conn.close()
        return
    
    # Show summary by canonical
    print(f"\n{'='*80}")
    print("TOP MERGE TARGETS:")
    print(f"{'='*80}\n")
    
    sorted_groups = sorted(all_merge_groups, 
                          key=lambda g: len(g['merge_into_canonical']), 
                          reverse=True)
    
    for group in sorted_groups[:10]:
        print(f"• {group['canonical']} ← {len(group['merge_into_canonical'])} categories")
        print(f"  Reason: {group['reason']}")
    
    # Apply merges automatically
    print(f"\n{'='*80}")
    print(f"\n🔨 Applying merges automatically...\n")
    
    # Create merge mapping
    merge_map = create_merge_mapping(all_merge_groups)
    
    # Apply merges
    stats = apply_merges_to_database(conn, merge_map)
    
    conn.close()
    
    # Final summary
    print(f"\n{'='*80}")
    print("✅ CLEANUP COMPLETE")
    print(f"{'='*80}\n")
    print(f"📊 Statistics:")
    print(f"   Categories merged: {stats['merged']}")
    print(f"   Child relationships updated: {stats['children_updated']}")
    print(f"   Parent relationships updated: {stats['parents_updated']}")
    print(f"\n📄 Merge plan: {merge_plan_file}")
    print(f"\n🔄 Next step: Re-export folder structure")
    print(f"   python3 export_skills_to_folders.py")
    print(f"\n💡 Then compare:")
    print(f"   diff -r skills_taxonomy/ skills_taxonomy_backup/")
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
