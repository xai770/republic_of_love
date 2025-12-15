#!/usr/bin/env python3
"""
Cleanup Taxonomy Synonyms
=========================

Uses an LLM to identify duplicate/synonym categories and merge them
into canonical forms for a cleaner hierarchy.

Process:
1. Extract all category names from a parent (e.g., TECHNICAL_SKILLS)
2. Ask LLM to identify synonym groups
3. Generate merge mappings (old → canonical)
4. Preview changes before applying
5. Update database and re-export

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
CONVERSATION_DIR = Path('/home/xai/Documents/ty_learn/temp/taxonomy_cleanup')

def ask_llm(prompt, conversation_file=None):
    """Ask LLM a question using ollama directly"""
    
    print(f"\n💭 Asking {LLM_MODEL}...")
    
    # Call ollama directly
    result = subprocess.run(
        ['ollama', 'run', LLM_MODEL],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        raise Exception(f"Ollama error: {result.stderr}")
    
    response = result.stdout.strip()
    
    # Save conversation if file specified
    if conversation_file:
        conversation_data = {
            'timestamp': datetime.now().isoformat(),
            'model': LLM_MODEL,
            'prompt': prompt,
            'response': response
        }
        with open(conversation_file, 'w') as f:
            json.dump(conversation_data, f, indent=2)
    
    return response

def get_all_categories_under_parent(conn, parent_skill):
    """Get all unique category names that are children of a parent"""
    
    cur = conn.cursor()
    
    # Get all skills that are children (directly or indirectly) of the parent
    cur.execute("""
        WITH RECURSIVE skill_tree AS (
            -- Start with direct children
            SELECT skill, parent_skill, 1 as depth
            FROM skill_hierarchy
            WHERE parent_skill = %s
            
            UNION ALL
            
            -- Get their children
            SELECT h.skill, h.parent_skill, t.depth + 1
            FROM skill_hierarchy h
            JOIN skill_tree t ON h.parent_skill = t.skill
            WHERE t.depth < 10  -- Prevent infinite loops
        )
        SELECT DISTINCT sa.skill, sa.display_name
        FROM skill_tree st
        JOIN skill_aliases sa ON st.skill = sa.skill
        WHERE sa.skill IN (
            -- Only include skills that are themselves parents (categories)
            SELECT DISTINCT parent_skill FROM skill_hierarchy
        )
        ORDER BY sa.display_name
    """, (parent_skill,))
    
    categories = cur.fetchall()
    cur.close()
    
    return categories

def parse_llm_merge_suggestions(response):
    """Parse LLM's merge suggestions into structured format"""
    
    # Clean up response
    response = response.strip()
    
    # Remove markdown code fences if present
    response = response.replace('```json', '').replace('```', '').strip()
    
    # Try to find JSON array in the response
    start_idx = response.find('[')
    end_idx = response.rfind(']')
    
    if start_idx != -1 and end_idx != -1:
        json_text = response[start_idx:end_idx+1]
        try:
            data = json.loads(json_text)
            return data
        except json.JSONDecodeError as e:
            print(f"\n⚠️  JSON parse error: {e}")
            print(f"Attempted to parse:\n{json_text[:500]}...")
    
    print("\n⚠️  Could not find valid JSON array in response")
    return None

def apply_merge(conn, old_skill, canonical_skill):
    """Merge old_skill into canonical_skill in the database"""
    
    cur = conn.cursor()
    
    # Update all child relationships: old_skill's children → canonical_skill's children
    cur.execute("""
        UPDATE skill_hierarchy
        SET parent_skill = %s
        WHERE parent_skill = %s
    """, (canonical_skill, old_skill))
    
    updated_children = cur.rowcount
    
    # Update all parent relationships: old_skill as child → canonical_skill as child
    cur.execute("""
        UPDATE skill_hierarchy
        SET skill = %s
        WHERE skill = %s
    """, (canonical_skill, old_skill))
    
    updated_parents = cur.rowcount
    
    # Mark old skill as deprecated (don't delete, keep for audit trail)
    cur.execute("""
        UPDATE skill_aliases
        SET notes = COALESCE(notes || ' ', '') || 
                    'MERGED INTO: ' || %s || ' on ' || %s
        WHERE skill = %s
    """, (canonical_skill, datetime.now().strftime('%Y-%m-%d'), old_skill))
    
    conn.commit()
    cur.close()
    
    return updated_children, updated_parents

def cleanup_taxonomy(parent_category="TECHNICAL_SKILLS"):
    """Main cleanup function"""
    
    print("=" * 80)
    print("🧹 TAXONOMY SYNONYM CLEANUP")
    print("=" * 80)
    print(f"Target category: {parent_category}")
    print(f"LLM model: {LLM_MODEL}\n")
    
    # Create conversation directory
    CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    conversation_file = CONVERSATION_DIR / f"cleanup_{parent_category}_{timestamp}.json"
    
    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Get all categories
    print(f"📊 Extracting all categories under {parent_category}...")
    categories = get_all_categories_under_parent(conn, parent_category)
    
    print(f"   Found {len(categories)} categories\n")
    
    if len(categories) == 0:
        print("❌ No categories found!")
        return
    
    # Prepare category list for LLM
    category_list = []
    for skill_id, display_name in categories:
        category_list.append({
            'id': skill_id,
            'name': display_name
        })
    
    # Create prompt for LLM
    prompt = f"""I have {len(categories)} category names in a skill taxonomy under "{parent_category}". 

Many are synonyms or very similar concepts that should be merged. Please analyze this list and identify groups of synonyms/duplicates that should be consolidated into a single canonical name.

CATEGORIES:
{json.dumps(category_list, indent=2)}

Please respond with a JSON array of merge groups. Each group should have:
- "canonical": the best/most standard name to keep
- "canonical_id": the skill ID to use (from the list above)
- "merge_into_canonical": array of skill IDs that should be merged into the canonical
- "reason": brief explanation of why these are synonyms

Example format:
[
  {{
    "canonical": "Information Technology",
    "canonical_id": "INFORMATION_TECHNOLOGY",
    "merge_into_canonical": ["IT_INFRASTRUCTURE", "INFORMATION_TECHNOLOGY_SKILLS"],
    "reason": "All refer to the same IT domain"
  }}
]

Focus on:
1. Obvious synonyms (e.g., "IT Security" vs "Information Security")
2. Abbreviations vs full names (e.g., "Risk Mgmt" vs "Risk Management")
3. Redundant qualifiers (e.g., "Risk Management Skills" vs "Risk Management")

Only suggest merges you're confident about. When in doubt, keep them separate.

Respond with ONLY the JSON array, no other text."""

    # Ask LLM
    print("🤖 Asking LLM to identify synonyms...\n")
    response = ask_llm(prompt, conversation_file)
    
    print("\n" + "=" * 80)
    print("LLM RESPONSE:")
    print("=" * 80)
    print(response)
    print("=" * 80 + "\n")
    
    # Parse response
    merge_groups = parse_llm_merge_suggestions(response)
    
    if not merge_groups:
        print("\n⚠️  Could not automatically parse LLM response.")
        print(f"📄 Conversation saved to: {conversation_file}")
        print("\nPlease review the response above and create merge mappings manually if needed.")
        conn.close()
        return
    
    # Display merge plan
    print(f"\n📋 PROPOSED MERGES ({len(merge_groups)} groups):\n")
    
    total_merges = 0
    for i, group in enumerate(merge_groups, 1):
        canonical = group.get('canonical', '?')
        canonical_id = group.get('canonical_id', '?')
        to_merge = group.get('merge_into_canonical', [])
        reason = group.get('reason', 'No reason given')
        
        print(f"{i}. Keep: {canonical} ({canonical_id})")
        print(f"   Merge: {', '.join(to_merge)} ({len(to_merge)} items)")
        print(f"   Reason: {reason}\n")
        
        total_merges += len(to_merge)
    
    print(f"Total: {total_merges} categories will be merged into {len(merge_groups)} canonical forms\n")
    
    # Apply merges automatically
    print("=" * 80)
    print("\n🔨 Applying merges automatically...\n")
    
    # Apply merges
    print("\n🔨 Applying merges...\n")
    
    stats = {
        'groups_processed': 0,
        'categories_merged': 0,
        'relationships_updated': 0
    }
    
    for i, group in enumerate(merge_groups, 1):
        canonical_id = group.get('canonical_id')
        to_merge = group.get('merge_into_canonical', [])
        
        print(f"[{i}/{len(merge_groups)}] Merging into {canonical_id}...")
        
        for old_id in to_merge:
            if old_id == canonical_id:
                print(f"   ⚠️  Skipping {old_id} (same as canonical)")
                continue
            
            try:
                children, parents = apply_merge(conn, old_id, canonical_id)
                print(f"   ✓ {old_id} → {canonical_id} ({children} children, {parents} parents updated)")
                stats['categories_merged'] += 1
                stats['relationships_updated'] += children + parents
            except Exception as e:
                print(f"   ❌ Failed to merge {old_id}: {e}")
        
        stats['groups_processed'] += 1
    
    conn.close()
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETE")
    print("=" * 80)
    print(f"\n📊 Statistics:")
    print(f"   Merge groups processed: {stats['groups_processed']}")
    print(f"   Categories merged: {stats['categories_merged']}")
    print(f"   Relationships updated: {stats['relationships_updated']}")
    print(f"\n📄 Details saved to: {conversation_file}")
    print(f"\n🔄 Next step: Re-export folder structure to see clean hierarchy")
    print(f"   python3 export_skills_to_folders.py")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        cleanup_taxonomy("TECHNICAL_SKILLS")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
