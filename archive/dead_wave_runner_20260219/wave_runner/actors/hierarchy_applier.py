#!/usr/bin/env python3
"""
Hierarchy Applier - WF3004 Step 4

Parses LLM output and inserts skill_hierarchy records.
Creates category skills if they don't exist.

Domain-agnostic: categories are created dynamically based on LLM output.
"""

import json
import re


def execute(input_data: dict, context: dict) -> dict:
    """
    Parse LLM category assignments and insert into skill_hierarchy.
    
    Expected input format from LLM (index-based):
    {
        "domain": "detected domain",
        "categories": {"1": "Category_Name", "2": "Another_Category", ...},
        "assignments": [{"i": 0, "c": 1}, {"i": 1, "c": 2}, ...]
    }
    
    Where "i" is the skill index from the batch, "c" is the category number.
    skill_ids list must be passed in input_data to map indices to actual IDs.
    """
    db_conn = context.get('db_conn')
    if not db_conn:
        return {"error": "No database connection", "success": False}
    
    # Get LLM response and skill mappings
    llm_response = input_data.get('response', '') or input_data.get('llm_output', '')
    skill_ids = input_data.get('skill_ids', [])
    skill_names = input_data.get('skill_names', [])
    
    if not llm_response:
        return {"error": "No LLM response to process", "success": False}
    
    try:
        # Parse JSON from LLM response (may be wrapped in markdown)
        json_match = re.search(r'\{[\s\S]*\}', llm_response)
        if not json_match:
            return {"error": f"No JSON found in response: {llm_response[:200]}", "success": False}
        
        data = json.loads(json_match.group())
        
        domain = data.get('domain', 'Unknown')
        categories = data.get('categories', {})
        assignments = data.get('assignments', [])
        
        if not assignments:
            return {"error": "No assignments in LLM response", "success": False}
        
        cursor = db_conn.cursor()
        
        # Ensure category skills exist and get their IDs
        category_skill_ids = {}
        for cat_num, cat_name in categories.items():
            # Normalize category name
            canonical = cat_name.lower().replace(' ', '_').replace('-', '_')
            
            # Check if exists
            cursor.execute("""
                SELECT skill_id FROM skill_aliases 
                WHERE skill_name = %s OR display_name = %s
                LIMIT 1
            """, (canonical, cat_name))
            row = cursor.fetchone()
            
            if row:
                category_skill_ids[int(cat_num)] = row[0]
            else:
                # Create category skill
                cursor.execute("""
                    INSERT INTO skill_aliases (display_name, skill_name, skill_alias)
                    VALUES (%s, %s, %s)
                    RETURNING skill_id
                """, (cat_name, canonical, canonical))
                category_skill_ids[int(cat_num)] = cursor.fetchone()[0]
        
        # Apply assignments (using indices)
        inserted = 0
        skipped = 0
        errors = []
        
        for assignment in assignments:
            # Support both old format (s=name) and new format (i=index)
            skill_index = assignment.get('i')
            skill_name = assignment.get('s')
            category_num = assignment.get('c')
            
            if skill_index is not None:
                # New index-based format
                if skill_index < 0 or skill_index >= len(skill_ids):
                    errors.append(f"Invalid skill index: {skill_index}")
                    continue
                skill_id = skill_ids[skill_index]
            elif skill_name:
                # Old name-based format (fallback)
                cursor.execute("""
                    SELECT skill_id FROM skill_aliases 
                    WHERE display_name = %s OR skill_name = %s
                    LIMIT 1
                """, (skill_name, skill_name.lower()))
                row = cursor.fetchone()
                if not row:
                    errors.append(f"Skill not found: {skill_name}")
                    continue
                skill_id = row[0]
            else:
                skipped += 1
                continue
            
            if category_num is None:
                skipped += 1
                continue
            
            parent_skill_id = category_skill_ids.get(int(category_num))
            
            if not parent_skill_id:
                skill_label = skill_names[skill_index] if skill_index is not None and skill_index < len(skill_names) else skill_name or f"id:{skill_id}"
                errors.append(f"Category {category_num} not found for skill {skill_label}")
                continue
            
            # Skip if skill is its own parent (categories)
            if skill_id == parent_skill_id:
                skipped += 1
                continue
            
            # Insert hierarchy relationship (single parent per skill)
            try:
                cursor.execute("""
                    INSERT INTO skill_hierarchy (skill_id, parent_skill_id)
                    VALUES (%s, %s)
                    ON CONFLICT (skill_id) DO NOTHING
                """, (skill_id, parent_skill_id))
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                errors.append(f"Insert error for {skill_name}: {str(e)}")
        
        db_conn.commit()
        
        return {
            "success": True,
            "domain_detected": domain,
            "categories_created": len(category_skill_ids),
            "category_names": list(categories.values()),
            "assignments_processed": len(assignments),
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors[:10] if errors else [],
            "message": f"Applied {inserted} hierarchy assignments. Domain: {domain}"
        }
        
    except json.JSONDecodeError as e:
        db_conn.rollback()
        return {"error": f"JSON parse error: {str(e)}", "success": False}
    except Exception as e:
        db_conn.rollback()
        return {"error": str(e), "success": False}


def apply_hierarchy_cli(input_data: dict) -> dict:
    """
    CLI-compatible version that creates its own DB connection.
    """
    import os
    import psycopg2
    from dotenv import load_dotenv
    
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )
    
    try:
        result = execute(input_data, {'db_conn': conn})
        # Convert success to status for CLI consistency
        if result.get('success'):
            result['status'] = 'success'
        elif result.get('error'):
            result['status'] = 'error'
        return result
    finally:
        conn.close()


def main():
    """CLI entry point."""
    import sys
    
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            pass
    
    result = apply_hierarchy_cli(input_data)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
