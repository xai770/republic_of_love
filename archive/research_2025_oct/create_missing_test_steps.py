#!/usr/bin/env python3
"""
Create test_steps for all enabled models that don't have ce_char_extract test steps yet
"""

import sqlite3

def create_missing_test_steps():
    db_path = "/home/xai/Documents/ty_learn/data/llmcore.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the template from existing test_steps
    cursor.execute("""
        SELECT 
            prompt_template,
            expected_pattern,
            step_description,
            validation_rules
        FROM test_steps ts
        JOIN tests t ON ts.test_id = t.test_id
        WHERE t.canonical_code = 'ce_char_extract'
        LIMIT 1
    """)
    
    template_row = cursor.fetchone()
    if not template_row:
        print("❌ No template found!")
        return
    
    prompt_template, expected_pattern, step_description, validation_rules = template_row
    
    # Get all enabled models that don't have test_steps for ce_char_extract
    cursor.execute("""
        SELECT DISTINCT m.model_name
        FROM models m
        WHERE m.enabled = 1
        AND m.model_name NOT IN (
            SELECT DISTINCT ts.model_name
            FROM test_steps ts
            JOIN tests t ON ts.test_id = t.test_id
            WHERE t.canonical_code = 'ce_char_extract'
        )
        ORDER BY m.model_name
    """)
    
    missing_models = [row[0] for row in cursor.fetchall()]
    
    if not missing_models:
        print("✅ All models already have test_steps!")
        return
    
    print(f"📊 Creating test_steps for {len(missing_models)} models...")
    
    # Get all ce_char_extract test_ids (one for each parameter)
    cursor.execute("""
        SELECT DISTINCT t.test_id
        FROM tests t
        WHERE t.canonical_code = 'ce_char_extract'
        ORDER BY t.test_id
    """)
    
    test_ids = [row[0] for row in cursor.fetchall()]
    print(f"📋 Found {len(test_ids)} ce_char_extract tests")
    
    # Create test_steps for each missing model × each test_id
    # Use different step_numbers to avoid UNIQUE constraint violation
    created_count = 0
    for model_idx, model_name in enumerate(missing_models):
        step_number = model_idx + 2  # Start from 2 since llama3.2:latest uses step 1
        for test_id in test_ids:
            cursor.execute("""
                INSERT INTO test_steps (
                    test_id,
                    step_number,
                    step_description,
                    prompt_template,
                    model_name,
                    expected_pattern,
                    validation_rules
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id,
                step_number,
                step_description,
                prompt_template,
                model_name,
                expected_pattern,
                validation_rules
            ))
            created_count += 1
        
        print(f"   ✅ Created {len(test_ids)} test_steps for {model_name} (step_number={step_number})")
    
    conn.commit()
    conn.close()
    
    print(f"🎉 Successfully created {created_count} test_steps!")
    print(f"📊 Now all {len(missing_models) + 1} models have ce_char_extract test_steps")

if __name__ == "__main__":
    create_missing_test_steps()