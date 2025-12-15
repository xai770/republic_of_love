#!/usr/bin/env python3
"""
Fix Recipe 1114 Session 7 prompt template to use fallback syntax
"""

import psycopg2

DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'host': 'localhost',
    'port': '5432'
}

NEW_PROMPT = """Clean this job posting summary by following these rules EXACTLY:

INPUT (use the best available summary - improved version if available, otherwise original):
{session_4_output?session_1_output}

RULES:
1. Remove ALL markdown code block markers (```, ```json, etc.)
2. Keep ONLY these section headers in this order:
   - **Role:**
   - **Company:**
   - **Location:**
   - **Job ID:**
   - **Key Responsibilities:**
   - **Requirements:**
   - **Details:**

3. Remove any "Type:", "Skills and Experience:", "Benefits:" sections - merge content into appropriate sections above
4. Format consistently:
   - Use "- " for all bullet points
   - Keep sections concise
   - No nested formatting
   - No extra blank lines between sections

5. Output PLAIN TEXT ONLY - no markdown wrappers

Return ONLY the cleaned version, nothing else."""

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Update Session 7 instruction
        cursor.execute("""
            UPDATE instructions 
            SET prompt_template = %s
            WHERE step_description = 'Standardize output format'
              AND session_id IN (SELECT session_id FROM sessions WHERE session_name = 'Format Standardization')
            RETURNING instruction_id, step_number, step_description
        """, (NEW_PROMPT,))
        
        result = cursor.fetchone()
        conn.commit()
        
        if result:
            print(f"✅ Updated Session 7 instruction:")
            print(f"   Instruction ID: {result[0]}")
            print(f"   Step: {result[1]}")
            print(f"   Description: {result[2]}")
            print(f"\n✅ Now uses fallback syntax: {{session_4_output?session_1_output}}")
        else:
            print("⚠️  No instructions were updated (might not exist)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
