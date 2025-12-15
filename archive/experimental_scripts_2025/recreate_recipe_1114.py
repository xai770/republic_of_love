#!/usr/bin/env python3
"""
Recreate Recipe 1114: self_healing_dual_grader in base.yoga (BY) PostgreSQL database
7 sessions with dependencies, multi-stage job posting extraction with self-correction
"""

import psycopg2
import psycopg2.extras
from datetime import datetime

# PostgreSQL connection
DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'host': 'localhost',
    'port': '5432'
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False  # Use transactions
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        print("🔧 Creating canonicals for self_healing_dual_grader sessions...")
        
        # Define the 7 canonicals (one per session)
        # Note: response field is required but these are workflow steps, not test cases
        # Using existing facets: ce=extract, gr=rank/grade, cn=normalize, gc=cluster
        canonicals = [
            ('gemma3_extract', 'ce', 'Extract job summary using gemma3:1b', 'Structured job summary in template format'),
            ('gemma2_grade', 'gr', 'Grade extraction quality using gemma2:latest', '[PASS] or [FAIL] with explanation'),
            ('qwen25_grade', 'gr', 'Second opinion grading using qwen2.5:7b', '[PASS] or [FAIL] with explanation'),
            ('qwen25_improve', 'cn', 'Improve extraction based on grader feedback', 'Improved job summary addressing feedback'),
            ('qwen25_regrade', 'gr', 'Re-grade improved extraction', '[PASS] or [FAIL] with explanation'),
            ('create_ticket', 'fe', 'Create human review ticket for failed extractions', 'Ticket summary with type, priority, and description'),
            ('format_standardization', 'cn', 'Standardize output format', 'Clean job summary with standardized format'),
        ]
        
        for canonical_code, facet_id, description, response in canonicals:
            cursor.execute("""
                INSERT INTO canonicals (canonical_code, facet_id, capability_description, response, enabled)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (canonical_code) DO UPDATE
                SET capability_description = EXCLUDED.capability_description,
                    facet_id = EXCLUDED.facet_id,
                    response = EXCLUDED.response
            """, (canonical_code, facet_id, description, response))
            print(f"  ✅ Canonical: {canonical_code}")
        
        print("\n🔧 Creating 7 sessions...")
        
        # Session 1: gemma3_extract
        cursor.execute("""
            INSERT INTO sessions (canonical_code, session_name, session_description, actor_id, context_strategy, max_instruction_runs, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING session_id
        """, ('gemma3_extract', 'session_a_gemma3_extract', 'Extract job summary', 'gemma3:1b', 'isolated', 50))
        session_1_id = cursor.fetchone()['session_id']
        print(f"  ✅ Session 1 (ID {session_1_id}): session_a_gemma3_extract")
        
        # Session 1 Instruction
        cursor.execute("""
            INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (session_1_id, 1, 'Extract with gemma3:1b', """Create a concise job description summary for this job posting:

{variations_param_1}

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do not add information.""", 60))
        
        # Session 2: gemma2_grade
        cursor.execute("""
            INSERT INTO sessions (canonical_code, session_name, session_description, actor_id, context_strategy, max_instruction_runs, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING session_id
        """, ('gemma2_grade', 'session_b_gemma2_grade', 'Grade extraction with gemma2', 'gemma2:latest', 'isolated', 50))
        session_2_id = cursor.fetchone()['session_id']
        print(f"  ✅ Session 2 (ID {session_2_id}): session_b_gemma2_grade")
        
        # Session 2 Instruction
        cursor.execute("""
            INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (session_2_id, 1, 'Grade with gemma2:latest', """# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
{session_1_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.""", 60))
        
        # Session 3: qwen25_grade
        cursor.execute("""
            INSERT INTO sessions (canonical_code, session_name, session_description, actor_id, context_strategy, max_instruction_runs, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING session_id
        """, ('qwen25_grade', 'session_c_qwen25_grade', 'Second opinion grading', 'qwen2.5:7b', 'isolated', 50))
        session_3_id = cursor.fetchone()['session_id']
        print(f"  ✅ Session 3 (ID {session_3_id}): session_c_qwen25_grade")
        
        # Session 3 Instruction
        cursor.execute("""
            INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (session_3_id, 1, 'Grade with qwen2.5:7b', """# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
{session_1_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.""", 60))
        
        # Session 4: qwen25_improve
        cursor.execute("""
            INSERT INTO sessions (canonical_code, session_name, session_description, actor_id, context_strategy, max_instruction_runs, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING session_id
        """, ('qwen25_improve', 'session_d_qwen25_improve', 'Improve extraction based on feedback', 'qwen2.5:7b', 'isolated', 50))
        session_4_id = cursor.fetchone()['session_id']
        print(f"  ✅ Session 4 (ID {session_4_id}): session_d_qwen25_improve")
        
        # Session 4 Instruction
        cursor.execute("""
            INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (session_4_id, 1, 'Improve extraction based on previous grade', """# Your Task: Improve the job summary based on previous feedback

## Previous Grading Result:
{session_3_output}

## Original Job Posting:
{variations_param_1}

## Current Summary (that received feedback):
{session_1_output}

## Instructions:

**IF** the previous grading result starts with "[PASS]":
- Simply return the current summary unchanged
- Do NOT modify anything

**IF** the previous grading result starts with "[FAIL]":
- Read the feedback carefully
- Create an IMPROVED version of the summary that addresses ALL issues mentioned
- Use the same ===OUTPUT TEMPLATE=== format
- Extract ONLY from the original posting
- Fix completeness issues, accuracy problems, and formatting errors

Return ONLY the improved summary (or unchanged summary if [PASS]). No explanations.""", 90))
        
        # Session 5: qwen25_regrade
        cursor.execute("""
            INSERT INTO sessions (canonical_code, session_name, session_description, actor_id, context_strategy, max_instruction_runs, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING session_id
        """, ('qwen25_regrade', 'session_e_qwen25_regrade', 'Re-grade improved version', 'qwen2.5:7b', 'isolated', 50))
        session_5_id = cursor.fetchone()['session_id']
        print(f"  ✅ Session 5 (ID {session_5_id}): session_e_qwen25_regrade")
        
        # Session 5 Instruction
        cursor.execute("""
            INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (session_5_id, 1, 'Re-grade the improved version', """# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** (this is the improved version):

--- start summary ---
{session_4_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.""", 60))
        
        # Session 6: create_ticket
        cursor.execute("""
            INSERT INTO sessions (canonical_code, session_name, session_description, actor_id, context_strategy, max_instruction_runs, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING session_id
        """, ('create_ticket', 'session_f_create_ticket', 'Create human review ticket', 'qwen2.5:7b', 'isolated', 50))
        session_6_id = cursor.fetchone()['session_id']
        print(f"  ✅ Session 6 (ID {session_6_id}): session_f_create_ticket")
        
        # Session 6 Instruction
        cursor.execute("""
            INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (session_6_id, 1, 'Create ticket summary for human review', """# Create a ticket summary for human review

## Re-grading Result:
{session_5_output}

## Original Summary:
{session_1_output}

## Improved Summary:
{session_4_output}

## Task:
Create a concise ticket summary in this format:

**TICKET_TYPE:** [EXTRACTION_FAILED or QUALITY_CHECK_NEEDED]
**PRIORITY:** [1=urgent, 2=normal, 3=low]
**TITLE:** [Brief description of the issue]
**DESCRIPTION:**
[2-3 sentences explaining what went wrong and why human review is needed]

**CONTEXT:**
- Original extraction quality: [brief assessment]
- Improvement attempt: [what was tried]
- Remaining issues: [what still needs fixing]

**IF** the re-grading result is [PASS]:
- Set TICKET_TYPE to QUALITY_CHECK_NEEDED
- Set PRIORITY to 3
- Note that improvement was successful but flagging for verification

**IF** the re-grading result is [FAIL]:
- Set TICKET_TYPE to EXTRACTION_FAILED
- Set PRIORITY to 2
- Detail what issues persist after improvement attempt""", 60))
        
        # Session 7: format_standardization
        cursor.execute("""
            INSERT INTO sessions (canonical_code, session_name, session_description, actor_id, context_strategy, max_instruction_runs, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING session_id
        """, ('format_standardization', 'Format Standardization', 'Standardize output format', 'phi3:latest', 'isolated', 50))
        session_7_id = cursor.fetchone()['session_id']
        print(f"  ✅ Session 7 (ID {session_7_id}): Format Standardization")
        
        # Session 7 Instruction
        cursor.execute("""
            INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (session_7_id, 1, 'Standardize output format', """Clean this job posting summary by following these rules EXACTLY:

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

Return ONLY the cleaned version, nothing else.""", 300))
        
        print("\n🔧 Checking recipe: self_healing_dual_grader...")
        
        # Check if recipe exists
        cursor.execute("""
            SELECT recipe_id FROM recipes 
            WHERE recipe_name = %s AND recipe_version = %s
        """, ('self_healing_dual_grader', 1))
        
        existing = cursor.fetchone()
        if existing:
            recipe_id = existing['recipe_id']
            print(f"  ✅ Recipe already exists (ID {recipe_id}), will link sessions")
            # Update description
            cursor.execute("""
                UPDATE recipes 
                SET recipe_description = %s,
                    max_total_session_runs = %s,
                    updated_at = NOW()
                WHERE recipe_id = %s
            """, ('Multi-stage job posting extraction with self-correction using multiple LLMs for extraction, grading, improvement, and formatting',
                  100, recipe_id))
        else:
            # Create the recipe
            cursor.execute("""
                INSERT INTO recipes (recipe_name, recipe_description, recipe_version, max_total_session_runs, enabled)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING recipe_id
            """, ('self_healing_dual_grader', 
                  'Multi-stage job posting extraction with self-correction using multiple LLMs for extraction, grading, improvement, and formatting',
                  1, 100))
            recipe_id = cursor.fetchone()['recipe_id']
            print(f"  ✅ Recipe created (ID {recipe_id})")
        
        print("\n🔧 Linking sessions to recipe via recipe_sessions...")
        
        # Link sessions with proper execution order
        # on_success_action: 'continue', 'skip_to', 'stop'
        # on_failure_action: 'stop', 'retry', 'skip_to'
        session_links = [
            (recipe_id, session_1_id, 1, 'always', 'continue', 'stop', 0),
            (recipe_id, session_2_id, 2, 'always', 'continue', 'stop', 0),
            (recipe_id, session_3_id, 3, 'always', 'continue', 'stop', 0),
            (recipe_id, session_4_id, 4, 'always', 'continue', 'retry', 1),  # Improvement can retry
            (recipe_id, session_5_id, 5, 'always', 'continue', 'stop', 0),
            (recipe_id, session_6_id, 6, 'always', 'continue', 'stop', 0),
            (recipe_id, session_7_id, 7, 'always', 'continue', 'stop', 0),
        ]
        
        for link in session_links:
            cursor.execute("""
                INSERT INTO recipe_sessions 
                (recipe_id, session_id, execution_order, execute_condition, on_success_action, on_failure_action, max_retry_attempts)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, link)
            print(f"  ✅ Linked session at position {link[2]}")
        
        # Commit all changes
        conn.commit()
        print(f"\n✅ SUCCESS! Recipe 1114 'self_healing_dual_grader' recreated in base.yoga")
        print(f"   Recipe ID: {recipe_id}")
        print(f"   Sessions: {session_1_id}, {session_2_id}, {session_3_id}, {session_4_id}, {session_5_id}, {session_6_id}, {session_7_id}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
