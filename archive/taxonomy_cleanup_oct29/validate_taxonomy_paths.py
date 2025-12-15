#!/usr/bin/env python3
"""
Taxonomy Validation and Correction
===================================

Uses an LLM taxonomy specialist to review and correct the hierarchy path
and spelling for each skill node.

Process:
1. Get all skills with their current hierarchy paths
2. Process in batches of 15
3. Ask LLM to validate/correct each path and spelling
4. Apply corrections to database
5. Re-export clean hierarchy

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
BATCH_SIZE = 15
OUTPUT_DIR = Path('/home/xai/Documents/ty_learn/temp/taxonomy_validation')

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

def get_current_hierarchy_path(conn, skill_id):
    """Get current hierarchy path by following parent chain"""
    
    path = [skill_id]
    current = skill_id
    
    cur = conn.cursor()
    
    # Follow parent chain (max 20 levels to prevent infinite loops)
    for _ in range(20):
        cur.execute("""
            SELECT parent_skill, sa.display_name
            FROM skill_hierarchy sh
            JOIN skill_aliases sa ON sh.parent_skill = sa.skill
            WHERE sh.skill = %s
            LIMIT 1
        """, (current,))
        
        result = cur.fetchone()
        if not result:
            break
        
        parent_id, parent_name = result
        path.insert(0, parent_id)
        current = parent_id
    
    cur.close()
    
    # Get display names for path
    cur = conn.cursor()
    display_path = []
    for skill in path:
        cur.execute("SELECT display_name FROM skill_aliases WHERE skill = %s", (skill,))
        result = cur.fetchone()
        if result:
            display_path.append(result[0])
    cur.close()
    
    return path, display_path

def get_all_leaf_skills(conn):
    """Get all leaf skills (skills that have no children)"""
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT 
            sa.skill, 
            sa.display_name,
            sa.created_by
        FROM skill_aliases sa
        WHERE sa.skill IN (
            -- Get skills that are children but not parents (leaf nodes)
            SELECT DISTINCT skill 
            FROM skill_hierarchy
            WHERE skill NOT IN (
                SELECT DISTINCT parent_skill FROM skill_hierarchy
            )
        )
        AND sa.created_by LIKE 'Recipe%'  -- Only process extracted skills, not auto-generated categories
        ORDER BY sa.display_name
    """)
    
    skills = cur.fetchall()
    cur.close()
    
    return skills

def process_batch(conn, batch, batch_num):
    """Process a batch of skills with LLM"""
    
    print(f"\n{'='*80}")
    print(f"📦 BATCH {batch_num} ({len(batch)} skills)")
    print(f"{'='*80}\n")
    
    # Prepare skills with current paths
    skills_data = []
    for skill_id, display_name, created_by in batch:
        path_ids, path_names = get_current_hierarchy_path(conn, skill_id)
        current_path = " > ".join(path_names)
        
        skills_data.append({
            'skill_id': skill_id,
            'current_name': display_name,
            'current_path': current_path
        })
    
    # Create prompt
    prompt = f"""You are a taxonomy specialist using O*NET standards. Review these {len(batch)} skills and their current hierarchy paths.

For each skill, validate:
1. Is the hierarchy path correct according to O*NET taxonomy?
2. Is the spelling/capitalization correct?
3. Should the skill be under different parent categories?

SKILLS TO REVIEW:
{json.dumps(skills_data, indent=2)}

For each skill, respond with corrections needed. Use proper O*NET category names with correct capitalization.

Respond with a JSON array:
[
  {{
    "skill_id": "SKILL_ID_FROM_ABOVE",
    "corrected_name": "Correct Spelling And Capitalization",
    "corrected_path": "Top Category > Mid Category > Subcategory > Skill Name",
    "changes": "what was corrected (spelling/hierarchy/both/none)"
  }}
]

Use standard O*NET top-level categories like:
- Business Skills
- Technical Skills  
- Soft Skills
- Industry Knowledge

Use proper capitalization (e.g., "IT Infrastructure" not "It Infrastructure").

Respond with ONLY the JSON array, no other text."""

    print(f"💭 Asking {LLM_MODEL} to validate batch...")
    
    try:
        response = ask_llm(prompt)
        corrections = parse_json_response(response)
        
        if corrections is None:
            print(f"   ⚠️  Could not parse response, skipping batch")
            return []
        
        # Filter to only skills that need changes
        needs_correction = [c for c in corrections if c.get('changes') != 'none']
        
        print(f"   ✓ Found {len(needs_correction)} skills needing correction")
        
        for correction in needs_correction:
            print(f"      • {correction['skill_id']}: {correction['changes']}")
        
        return corrections
        
    except Exception as e:
        print(f"   ❌ Error processing batch: {e}")
        return []

def parse_corrected_path(path_string):
    """Parse corrected path into category list"""
    return [category.strip() for category in path_string.split('>')]

def ensure_category_exists(conn, category_name, parent_skill=None):
    """Ensure a category exists in skill_aliases, create if needed"""
    
    # Normalize to skill_id format
    category_id = category_name.upper().replace(' ', '_').replace('-', '_')
    
    cur = conn.cursor()
    
    # Check if exists
    cur.execute("SELECT skill FROM skill_aliases WHERE skill = %s", (category_id,))
    if cur.fetchone():
        cur.close()
        return category_id
    
    # Create new category
    cur.execute("""
        INSERT INTO skill_aliases (skill, skill_alias, display_name, language, confidence, created_by, notes)
        VALUES (%s, %s, %s, 'en', 0.95, %s, %s)
        ON CONFLICT (skill) DO NOTHING
    """, (
        category_id,
        category_id,
        category_name,
        'Taxonomy_Validation_' + datetime.now().strftime('%Y%m%d'),
        'Auto-created during taxonomy validation'
    ))
    
    conn.commit()
    cur.close()
    
    return category_id

def apply_corrections(conn, all_corrections):
    """Apply all corrections to database"""
    
    print(f"\n{'='*80}")
    print(f"🔨 APPLYING CORRECTIONS")
    print(f"{'='*80}\n")
    
    stats = {
        'spelling_fixed': 0,
        'hierarchy_changed': 0,
        'both_changed': 0,
        'no_change': 0,
        'errors': 0
    }
    
    cur = conn.cursor()
    
    for i, correction in enumerate(all_corrections, 1):
        skill_id = correction['skill_id']
        corrected_name = correction.get('corrected_name')
        corrected_path = correction.get('corrected_path')
        changes = correction.get('changes', 'none')
        
        if changes == 'none':
            stats['no_change'] += 1
            continue
        
        print(f"[{i}/{len(all_corrections)}] {skill_id}")
        print(f"   Changes: {changes}")
        
        try:
            # Update display name if spelling corrected
            if 'spelling' in changes.lower():
                cur.execute("""
                    UPDATE skill_aliases
                    SET display_name = %s,
                        notes = COALESCE(notes || ' | ', '') || 
                                'Name corrected from validation on ' || %s
                    WHERE skill = %s
                """, (corrected_name, datetime.now().strftime('%Y-%m-%d'), skill_id))
                stats['spelling_fixed'] += 1
                print(f"   ✓ Updated name to: {corrected_name}")
            
            # Update hierarchy if path changed
            if 'hierarchy' in changes.lower():
                # Parse the corrected path
                path_categories = parse_corrected_path(corrected_path)
                
                # Remove old parent relationships for this skill
                cur.execute("DELETE FROM skill_hierarchy WHERE skill = %s", (skill_id,))
                
                # Build new hierarchy
                parent_id = None
                for category_name in path_categories[:-1]:  # Exclude the skill itself
                    # Ensure category exists
                    category_id = ensure_category_exists(conn, category_name, parent_id)
                    
                    if parent_id:
                        # Create relationship between parent and this category
                        cur.execute("""
                            INSERT INTO skill_hierarchy (skill, parent_skill, strength, created_at)
                            VALUES (%s, %s, 0.95, CURRENT_TIMESTAMP)
                            ON CONFLICT (skill, parent_skill) DO NOTHING
                        """, (category_id, parent_id))
                    
                    parent_id = category_id
                
                # Link the skill to its immediate parent
                if parent_id:
                    cur.execute("""
                        INSERT INTO skill_hierarchy (skill, parent_skill, strength, created_at)
                        VALUES (%s, %s, 0.95, CURRENT_TIMESTAMP)
                        ON CONFLICT (skill, parent_skill) DO NOTHING
                    """, (skill_id, parent_id))
                
                stats['hierarchy_changed'] += 1
                print(f"   ✓ Updated path to: {corrected_path}")
            
            if 'both' in changes.lower():
                stats['both_changed'] += 1
            
            conn.commit()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            stats['errors'] += 1
            conn.rollback()
    
    cur.close()
    return stats

def main():
    """Main validation process"""
    
    print("=" * 80)
    print("🎓 TAXONOMY SPECIALIST - VALIDATION & CORRECTION")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}")
    print(f"Batch size: {BATCH_SIZE} skills")
    print()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Get all leaf skills (the actual skills, not categories)
    print("📊 Loading all skills to validate...")
    all_skills = get_all_leaf_skills(conn)
    print(f"   Found {len(all_skills)} skills to validate\n")
    
    if len(all_skills) == 0:
        print("❌ No skills found to validate!")
        conn.close()
        return
    
    # Process in batches
    all_corrections = []
    
    for i in range(0, len(all_skills), BATCH_SIZE):
        batch = all_skills[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        corrections = process_batch(conn, batch, batch_num)
        all_corrections.extend(corrections)
    
    # Save correction plan
    correction_plan_file = OUTPUT_DIR / f"corrections_{timestamp}.json"
    with open(correction_plan_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'model': LLM_MODEL,
            'total_skills': len(all_skills),
            'batches_processed': (len(all_skills) + BATCH_SIZE - 1) // BATCH_SIZE,
            'corrections': all_corrections
        }, f, indent=2)
    
    # Summary
    needs_correction = [c for c in all_corrections if c.get('changes') != 'none']
    
    print(f"\n{'='*80}")
    print(f"📋 VALIDATION SUMMARY")
    print(f"{'='*80}\n")
    print(f"Skills validated: {len(all_skills)}")
    print(f"Skills needing correction: {len(needs_correction)}")
    print(f"\n📄 Plan saved to: {correction_plan_file}")
    
    if len(needs_correction) == 0:
        print("\n✨ All skills are correctly categorized and spelled!")
        conn.close()
        return
    
    # Show sample corrections
    print(f"\n{'='*80}")
    print("SAMPLE CORRECTIONS:")
    print(f"{'='*80}\n")
    
    for correction in needs_correction[:10]:
        print(f"• {correction['skill_id']}")
        print(f"  Current: {correction.get('current_name', 'N/A')}")
        print(f"  Corrected: {correction['corrected_name']}")
        print(f"  New path: {correction['corrected_path']}")
        print(f"  Changes: {correction['changes']}\n")
    
    if len(needs_correction) > 10:
        print(f"  ... and {len(needs_correction) - 10} more\n")
    
    # Apply corrections automatically
    print(f"{'='*80}")
    print(f"\n🔨 Applying corrections automatically...\n")
    
    # Apply corrections
    stats = apply_corrections(conn, all_corrections)
    
    conn.close()
    
    # Final summary
    print(f"\n{'='*80}")
    print("✅ VALIDATION COMPLETE")
    print(f"{'='*80}\n")
    print(f"📊 Statistics:")
    print(f"   Spelling corrected: {stats['spelling_fixed']}")
    print(f"   Hierarchy changed: {stats['hierarchy_changed']}")
    print(f"   Both corrected: {stats['both_changed']}")
    print(f"   No changes needed: {stats['no_change']}")
    print(f"   Errors: {stats['errors']}")
    print(f"\n📄 Corrections: {correction_plan_file}")
    print(f"\n🔄 Next step: Re-export folder structure")
    print(f"   python3 export_skills_to_folders.py")
    print(f"\n💡 Then compare:")
    print(f"   diff -r skills_taxonomy_backup/ skills_taxonomy/")
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
