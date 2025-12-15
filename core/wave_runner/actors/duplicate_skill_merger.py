#!/usr/bin/env python3
"""
Duplicate Skill Merger - WF3007 Step 1a

Merges duplicate skills that differ only in casing/underscores.
Uses pg_trgm similarity to identify duplicates.

Approach:
1. Find micro-categories (parent with 1 child) 
2. Check if parent and child are naming variants (similarity > 0.7)
3. If so, merge the child into the parent (or vice versa based on conventions)
"""

import json
import sys
import os
import psycopg2
from dotenv import load_dotenv


def normalize_name(name: str) -> str:
    """Normalize skill name for comparison."""
    return name.lower().replace('_', '').replace('-', '').replace(' ', '').replace('&', 'and')


def find_duplicate_pairs(batch_size: int = 50) -> dict:
    """
    Find parent-child pairs that are actually duplicates.
    Returns pairs where similarity > 0.7.
    """
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )
    
    try:
        cursor = conn.cursor()
        
        # Find micro-categories (1 child) where parent and child are similar
        cursor.execute("""
            WITH micro_cats AS (
                SELECT 
                    parent.entity_id as parent_id,
                    parent.canonical_name as parent_name,
                    child.entity_id as child_id,
                    child.canonical_name as child_name,
                    similarity(
                        LOWER(REPLACE(REPLACE(REPLACE(parent.canonical_name, '_', ''), '-', ''), ' ', '')),
                        LOWER(REPLACE(REPLACE(REPLACE(child.canonical_name, '_', ''), '-', ''), ' ', ''))
                    ) as sim
                FROM entities parent
                JOIN entity_relationships er ON er.related_entity_id = parent.entity_id 
                    AND er.relationship = 'child_of'
                JOIN entities child ON child.entity_id = er.entity_id
                WHERE parent.entity_type = 'skill'
                  AND child.entity_type = 'skill'
                  AND NOT EXISTS (
                      SELECT 1 FROM entity_relationships er2 
                      WHERE er2.entity_id = parent.entity_id AND er2.relationship = 'child_of'
                  )
                  -- Ensure exactly 1 child
                  AND (SELECT COUNT(*) FROM entity_relationships er3 
                       WHERE er3.related_entity_id = parent.entity_id AND er3.relationship = 'child_of') = 1
            )
            SELECT parent_id, parent_name, child_id, child_name, sim
            FROM micro_cats
            WHERE sim > 0.7
            ORDER BY sim DESC
            LIMIT %s
        """, (batch_size,))
        
        pairs = []
        for row in cursor.fetchall():
            parent_id, parent_name, child_id, child_name, sim = row
            
            # Decide which to keep: prefer lowercase_with_underscores
            parent_score = score_name_convention(parent_name)
            child_score = score_name_convention(child_name)
            
            if parent_score >= child_score:
                keep_id, keep_name = parent_id, parent_name
                merge_id, merge_name = child_id, child_name
            else:
                keep_id, keep_name = child_id, child_name
                merge_id, merge_name = parent_id, parent_name
            
            pairs.append({
                "keep_id": keep_id,
                "keep_name": keep_name,
                "merge_id": merge_id,
                "merge_name": merge_name,
                "similarity": float(sim)
            })
        
        # Count remaining
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT parent.entity_id
                FROM entities parent
                JOIN entity_relationships er ON er.related_entity_id = parent.entity_id 
                    AND er.relationship = 'child_of'
                JOIN entities child ON child.entity_id = er.entity_id
                WHERE parent.entity_type = 'skill'
                  AND NOT EXISTS (
                      SELECT 1 FROM entity_relationships er2 
                      WHERE er2.entity_id = parent.entity_id AND er2.relationship = 'child_of'
                  )
                  AND (SELECT COUNT(*) FROM entity_relationships er3 
                       WHERE er3.related_entity_id = parent.entity_id AND er3.relationship = 'child_of') = 1
                  AND similarity(
                      LOWER(REPLACE(REPLACE(REPLACE(parent.canonical_name, '_', ''), '-', ''), ' ', '')),
                      LOWER(REPLACE(REPLACE(REPLACE(child.canonical_name, '_', ''), '-', ''), ' ', ''))
                  ) > 0.7
            ) t
        """)
        remaining = cursor.fetchone()[0]
        
        return {
            "status": "success",
            "has_more": remaining > batch_size,
            "batch_size": len(pairs),
            "remaining": remaining,
            "pairs": pairs
        }
        
    finally:
        conn.close()


def score_name_convention(name: str) -> int:
    """
    Score a name based on naming convention preference.
    Higher = better.
    Prefer: lowercase_with_underscores
    """
    score = 0
    
    # Prefer lowercase
    if name == name.lower():
        score += 10
    
    # Prefer underscores over no separators
    if '_' in name:
        score += 5
    
    # Penalize ALL CAPS
    if name == name.upper() and name != name.lower():
        score -= 10
    
    # Penalize special characters
    if '&' in name or '(' in name or ')' in name:
        score -= 3
    
    return score


def merge_duplicates(pairs: list, dry_run: bool = True) -> dict:
    """
    Merge duplicate skills.
    
    For each pair:
    1. Add merge_name as alias of keep_name
    2. Reassign all relationships from merge_id to keep_id
    3. Mark merge entity as status='merged', merged_into_entity_id=keep_id
    """
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )
    
    try:
        cursor = conn.cursor()
        merged = []
        errors = []
        
        for pair in pairs:
            keep_id = pair['keep_id']
            merge_id = pair['merge_id']
            keep_name = pair['keep_name']
            merge_name = pair['merge_name']
            
            try:
                if not dry_run:
                    # 1. Add merge_name as alias of keep entity
                    cursor.execute("""
                        INSERT INTO entity_names (entity_id, language, display_name, is_primary, created_by)
                        VALUES (%s, 'en', %s, false, 'duplicate_merger')
                        ON CONFLICT (entity_id, language, display_name) DO NOTHING
                    """, (keep_id, merge_name))
                    
                    # 2. Reassign children of merge_id to keep_id
                    cursor.execute("""
                        UPDATE entity_relationships
                        SET related_entity_id = %s,
                            provenance = jsonb_set(
                                COALESCE(provenance, '{}'), 
                                '{merged_from}', 
                                to_jsonb(%s::text)
                            )
                        WHERE related_entity_id = %s AND relationship = 'child_of'
                    """, (keep_id, merge_name, merge_id))
                    
                    # 3. Delete the duplicate relationship (child -> parent becomes self-referential conceptually)
                    cursor.execute("""
                        DELETE FROM entity_relationships
                        WHERE entity_id = %s AND related_entity_id = %s AND relationship = 'child_of'
                    """, (merge_id, keep_id))
                    
                    # Also handle if merge was parent of keep
                    cursor.execute("""
                        DELETE FROM entity_relationships
                        WHERE entity_id = %s AND related_entity_id = %s AND relationship = 'child_of'
                    """, (keep_id, merge_id))
                    
                    # 4. Mark merge entity as merged
                    cursor.execute("""
                        UPDATE entities
                        SET status = 'merged', merged_into_entity_id = %s
                        WHERE entity_id = %s
                    """, (keep_id, merge_id))
                    
                merged.append({
                    "keep": keep_name,
                    "merged": merge_name
                })
                
            except Exception as e:
                errors.append({
                    "pair": pair,
                    "error": str(e)
                })
        
        if not dry_run:
            conn.commit()
        
        return {
            "status": "success",
            "dry_run": dry_run,
            "merged_count": len(merged),
            "error_count": len(errors),
            "merged": merged,
            "errors": errors
        }
        
    except Exception as e:
        conn.rollback()
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        conn.close()


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Wave runner entry point.
    
    Modes:
    - find: Find duplicate pairs
    - merge: Merge duplicates (requires pairs in input)
    """
    input_data = interaction_data.get('input_data', {})
    mode = input_data.get('mode', 'find')
    
    try:
        if mode == 'find':
            batch_size = input_data.get('batch_size', 50)
            return find_duplicate_pairs(batch_size)
        elif mode == 'merge':
            pairs = input_data.get('pairs', [])
            dry_run = input_data.get('dry_run', True)
            return merge_duplicates(pairs, dry_run)
        else:
            return {"status": "error", "error": f"Unknown mode: {mode}"}
    except Exception as e:
        if db_conn:
            db_conn.rollback()
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # CLI mode for testing
    mode = sys.argv[1] if len(sys.argv) > 1 else 'find'
    
    if mode == 'find':
        result = find_duplicate_pairs(batch_size=10)
    elif mode == 'merge':
        # First find, then merge with dry_run
        pairs_result = find_duplicate_pairs(batch_size=100)
        if pairs_result['status'] == 'success':
            dry_run = '--execute' not in sys.argv
            result = merge_duplicates(pairs_result['pairs'], dry_run=dry_run)
            result['pairs_found'] = len(pairs_result['pairs'])
        else:
            result = pairs_result
    else:
        result = {"error": "Usage: python duplicate_skill_merger.py [find|merge] [--execute]"}
    
    print(json.dumps(result, indent=2))
