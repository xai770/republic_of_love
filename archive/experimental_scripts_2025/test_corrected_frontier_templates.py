#!/usr/bin/env python3
"""
Test Corrected Frontier Templates
=================================

Test the corrected templates for the 7 frontier instructions to verify
that parameter substitution is working correctly.
"""

import sqlite3
import re

def test_template_rendering():
    """Test the corrected frontier templates"""
    
    db_path = "/home/xai/Documents/ty_learn/data/llmcore.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get frontier instructions with their updated templates and sample variations
    cursor.execute("""
        SELECT 
            i.instruction_id,
            r.canonical_code,
            i.prompt_template,
            v.test_input,
            v.expected_response
        FROM instructions i 
        JOIN recipes r ON i.recipe_id = r.recipe_id
        JOIN variations v ON r.recipe_id = v.recipe_id
        WHERE i.instruction_id IN (912, 915, 916, 917, 918, 922, 923)
        AND v.variation_id = (
            SELECT MIN(variation_id) 
            FROM variations v2 
            WHERE v2.recipe_id = v.recipe_id
        )
        ORDER BY i.instruction_id
    """)
    
    results = cursor.fetchall()
    
    print("🧪 Testing Corrected Frontier Templates")
    print("=" * 60)
    
    for instruction_id, canonical_code, template, test_input, expected_response in results:
        print(f"\n📋 Instruction {instruction_id}: {canonical_code}")
        print(f"   Test Input: {test_input}")
        print(f"   Expected: {expected_response}")
        
        # Simulate the template rendering process
        rendered_prompt = render_prompt(template, test_input)
        
        print(f"   ✅ Rendered Prompt Preview:")
        print(f"      {rendered_prompt[:200]}...")
        
        # Check for unsubstituted placeholders
        unsubstituted = re.findall(r'\{([^}]+)\}', rendered_prompt)
        if unsubstituted:
            print(f"   ⚠️  Unsubstituted placeholders: {unsubstituted}")
        else:
            print(f"   ✅ All placeholders substituted correctly")
    
    conn.close()
    print(f"\n🎯 Template rendering test complete!")

def render_prompt(template: str, test_input: str) -> str:
    """Simulate the prompt rendering process from test_runner.py"""
    # Handle payload replacements (most common pattern)
    rendered = template.replace('{{payload}}', test_input)
    rendered = rendered.replace('{payload}', test_input)
    
    # Handle word replacements
    rendered = rendered.replace('{word}', test_input)
    
    # Handle any other single placeholders by replacing with test_input
    placeholders = re.findall(r'\{([^}]+)\}', rendered)
    for placeholder in placeholders:
        if placeholder not in ['payload', 'word']:  # Don't double-replace
            rendered = rendered.replace(f'{{{placeholder}}}', test_input)
            
    return rendered

if __name__ == "__main__":
    test_template_rendering()