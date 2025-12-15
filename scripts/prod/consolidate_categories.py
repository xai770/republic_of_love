#!/usr/bin/env python3
"""
Category Consolidation - WF3004 Step 5

Uses LLM to identify and merge duplicate/similar categories.
Runs iteratively until no more merges are suggested.

Usage:
    python3 scripts/prod/consolidate_categories.py [--dry-run] [--max-rounds N]
"""

import argparse
import json
import os
import re
import sys
import requests
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)

def get_root_categories(conn):
    """Get all categories that are parents but have no parent themselves."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT sa.skill_id, sa.display_name
        FROM skill_hierarchy sh
        JOIN skill_aliases sa ON sh.parent_skill_id = sa.skill_id
        WHERE sh.parent_skill_id NOT IN (SELECT skill_id FROM skill_hierarchy)
        ORDER BY sa.display_name
    """)
    return cursor.fetchall()

def get_category_child_count(conn, skill_id):
    """Count how many skills are under this category."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM skill_hierarchy WHERE parent_skill_id = %s
    """, (skill_id,))
    return cursor.fetchone()[0]

def normalize_name(name):
    """Normalize a category name to Title_Case_With_Underscores format."""
    # Known acronyms/terms to preserve as-is (check whole name first)
    preserve_whole = {
        'devops': 'DevOps',
    }
    
    # Check if the whole name (lowercased) is a special term
    if name.lower().replace('_', '').replace(' ', '') in preserve_whole:
        return preserve_whole[name.lower().replace('_', '').replace(' ', '')]
    
    # Known acronyms to preserve when they appear as words
    preserve_parts = {
        'sap': 'SAP', 
        'esg': 'ESG',
        'ux': 'UX',
        'ui': 'UI',
        'it': 'IT',
        'qa': 'QA',
        'api': 'API',
        'sql': 'SQL',
    }
    
    # Replace & with And
    name = name.replace('&', ' And ')
    # Remove parenthetical suffixes like (UX)
    name = re.sub(r'\s*\([^)]+\)', '', name)
    # Split CamelCase (but not already-underscored words)
    # ProcessImprovementAndEfficiency → Process Improvement And Efficiency
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    # Replace multiple spaces/underscores with single space
    name = re.sub(r'[\s_]+', ' ', name)
    
    # Title case each word, preserving known acronyms
    words = name.strip().split()
    result_words = []
    for w in words:
        lower = w.lower()
        if lower in preserve_parts:
            result_words.append(preserve_parts[lower])
        else:
            result_words.append(w.capitalize())
    
    # Join with underscores
    return '_'.join(result_words)

def ask_llm_for_merges(categories):
    """Ask LLM to identify categories that should be merged (same meaning)."""
    category_list = "\n".join([f"- {name}" for _, name in categories])
    
    prompt = f'''You are a Taxonomy Consolidation Expert.

We have {len(categories)} skill categories. Identify which ones are DUPLICATES (same meaning, different names).

CATEGORIES:
{category_list}

TASK: Find categories that mean the SAME THING and should be merged.

Examples of duplicates:
- "Cloud_Computing" and "Cloud_Technology" (same concept)
- "Database_Management" and "Database_Administration" (same concept)
- "Project_Management" and "Project_Planning" (same concept)

DO NOT merge categories that are related but different:
- "Security" and "Audit_And_Compliance" (different concepts)
- "Development" and "DevOps" (different concepts)

OUTPUT FORMAT (JSON only):
{{
  "merges": [
    {{"keep": "Category_To_Keep", "remove": ["Duplicate1", "Duplicate2"]}}
  ]
}}

IMPORTANT: 
- "keep" must be an EXACT name from the list above
- "remove" contains names to merge INTO the kept category
- If no merges needed, return: {{"merges": []}}'''

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={'model': 'qwen2.5:7b', 'prompt': prompt, 'stream': False},
            timeout=180
        )
        response.raise_for_status()
        result = response.json().get('response', '')
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            json_str = json_match.group()
            # Remove // comments that LLM sometimes adds
            json_str = re.sub(r'//[^\n]*', '', json_str)
            # Remove trailing commas before } or ]
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                log(f"  JSON parse error: {e}")
                return {"merges": []}
        return {"merges": []}
    except Exception as e:
        log(f"  LLM error: {e}")
        return {"merges": []}

def apply_merge(conn, canonical_name, duplicate_names, dry_run=False):
    """Merge duplicate categories into canonical one."""
    cursor = conn.cursor()
    
    # Find canonical skill_id
    cursor.execute("""
        SELECT skill_id FROM skill_aliases 
        WHERE display_name = %s OR skill_name = %s
        LIMIT 1
    """, (canonical_name, canonical_name.lower().replace(' ', '_')))
    row = cursor.fetchone()
    
    if not row:
        log(f"    ⚠ Canonical '{canonical_name}' not found, skipping")
        return 0
    
    canonical_id = row[0]
    merged_count = 0
    
    for dup_name in duplicate_names:
        # Find duplicate skill_id
        cursor.execute("""
            SELECT skill_id FROM skill_aliases 
            WHERE display_name = %s OR skill_name = %s
            LIMIT 1
        """, (dup_name, dup_name.lower().replace(' ', '_')))
        row = cursor.fetchone()
        
        if not row:
            log(f"    ⚠ Duplicate '{dup_name}' not found, skipping")
            continue
        
        dup_id = row[0]
        
        if dup_id == canonical_id:
            continue
        
        # Count children being moved
        cursor.execute("""
            SELECT COUNT(*) FROM skill_hierarchy WHERE parent_skill_id = %s
        """, (dup_id,))
        child_count = cursor.fetchone()[0]
        
        if dry_run:
            log(f"    [DRY RUN] Would merge '{dup_name}' ({child_count} skills) → '{canonical_name}'")
        else:
            # Move all children to canonical (but not if it would create self-reference)
            cursor.execute("""
                UPDATE skill_hierarchy 
                SET parent_skill_id = %s 
                WHERE parent_skill_id = %s
                  AND skill_id != %s
            """, (canonical_id, dup_id, canonical_id))
            
            # Remove the duplicate from hierarchy (if it's a child somewhere)
            cursor.execute("""
                DELETE FROM skill_hierarchy WHERE skill_id = %s
            """, (dup_id,))
            
            log(f"    ✓ Merged '{dup_name}' ({child_count} skills) → '{canonical_name}'")
        
        merged_count += child_count
    
    if not dry_run:
        conn.commit()
    
    return merged_count

def apply_rename(conn, old_name, new_name, dry_run=False):
    """Rename a category (update display_name)."""
    cursor = conn.cursor()
    
    # Find the skill by display_name or skill_name
    cursor.execute("""
        SELECT skill_id, display_name, skill_name FROM skill_aliases 
        WHERE display_name = %s OR skill_name = %s
        LIMIT 1
    """, (old_name, old_name.lower().replace(' ', '_')))
    row = cursor.fetchone()
    
    if not row:
        log(f"    ⚠ '{old_name}' not found, skipping rename")
        return False
    
    skill_id, current_display, current_name = row
    
    if dry_run:
        log(f"    [DRY RUN] Would rename '{old_name}' → '{new_name}'")
    else:
        # Update display_name
        cursor.execute("""
            UPDATE skill_aliases 
            SET display_name = %s
            WHERE skill_id = %s
        """, (new_name, skill_id))
        conn.commit()
        log(f"    ✓ Renamed '{old_name}' → '{new_name}'")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Consolidate duplicate categories')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--max-rounds', type=int, default=5, help='Max consolidation rounds')
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    log("=" * 60)
    log("CATEGORY CONSOLIDATION")
    log("=" * 60)
    
    if args.dry_run:
        log("DRY RUN MODE - no changes will be made")
    
    total_merged = 0
    
    # PHASE 1: Merge duplicates via LLM
    for round_num in range(1, args.max_rounds + 1):
        log(f"\n--- MERGE ROUND {round_num} ---")
        
        # Get current root categories
        categories = get_root_categories(conn)
        log(f"  Found {len(categories)} root categories")
        
        if len(categories) <= 25:
            log(f"  Category count is reasonable ({len(categories)} ≤ 25), stopping merges")
            break
        
        # Ask LLM for merge suggestions only
        log("  Asking LLM for merge suggestions...")
        result = ask_llm_for_merges(categories)
        merges = result.get('merges', [])
        
        if not merges:
            log("  No merges suggested, stopping")
            break
        
        log(f"  LLM suggested {len(merges)} merge groups")
        
        # Apply merges
        round_merged = 0
        for merge in merges:
            # Support both formats: {keep, remove} and {canonical, duplicates}
            canonical = merge.get('keep', merge.get('canonical', ''))
            duplicates = merge.get('remove', merge.get('duplicates', []))
            
            if canonical and duplicates:
                log(f"  Merging into '{canonical}':")
                count = apply_merge(conn, canonical, duplicates, args.dry_run)
                round_merged += count
        
        total_merged += round_merged
        log(f"  Round {round_num}: {round_merged} skills re-parented")
        
        if round_merged == 0:
            log("  No actual merges applied, stopping")
            break
    
    # PHASE 2: Normalize all names programmatically
    log("\n--- NORMALIZING NAMES ---")
    categories = get_root_categories(conn)
    rename_count = 0
    
    for skill_id, display_name in categories:
        normalized = normalize_name(display_name)
        if normalized != display_name:
            if args.dry_run:
                log(f"  [DRY RUN] Would rename '{display_name}' → '{normalized}'")
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE skill_aliases SET display_name = %s WHERE skill_id = %s
                """, (normalized, skill_id))
                conn.commit()
                log(f"  ✓ Renamed '{display_name}' → '{normalized}'")
            rename_count += 1
    
    if rename_count == 0:
        log("  All names already normalized")
    else:
        log(f"  Normalized {rename_count} category names")
    
    # Final stats
    categories = get_root_categories(conn)
    log("\n" + "=" * 60)
    log("CONSOLIDATION COMPLETE")
    log("=" * 60)
    log(f"Final category count: {len(categories)}")
    log(f"Total skills re-parented: {total_merged}")
    log(f"Names normalized: {rename_count}")
    
    if not args.dry_run and (total_merged > 0 or rename_count > 0):
        log("\nRun 'python3 tools/rebuild_skills_taxonomy.py' to update folder export")
    
    conn.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
