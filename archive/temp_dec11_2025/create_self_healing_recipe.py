#!/usr/bin/env python3
"""
Create Recipe 1114: Self-Healing Dual Grader with Human Escalation

Architecture:
- Session A: gemma3:1b extraction
- Session B: gemma2:latest grading
- Session C: qwen2.5:7b grading (strict validator)
- Session D: qwen2.5:7b improvement (IF Session C failed)
- Session E: qwen2.5:7b re-grade improved version
- Session F: Create ticket for xai (IF Session E still failed)
"""

import sqlite3

DB_PATH = "/home/xai/Documents/ty_learn/data/llmcore.db"

def create_recipe():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the recipe
    cursor.execute("""
        INSERT INTO recipes (canonical_code, enabled, review_notes)
        VALUES (
            'self_healing_dual_grader',
            1,
            'Self-healing pipeline: gemma3 extract → dual grade → qwen improves if failed → re-grade → escalate to human if still failed'
        )
    """)
    
    recipe_id = cursor.lastrowid
    print(f"✅ Created Recipe {recipe_id}: self_healing_dual_grader")
    
    # Get actor IDs
    actors = {
        'gemma3': cursor.execute("SELECT actor_id FROM actors WHERE actor_id = 'gemma3:1b'").fetchone()[0],
        'gemma2': cursor.execute("SELECT actor_id FROM actors WHERE actor_id = 'gemma2:latest'").fetchone()[0],
        'qwen25': cursor.execute("SELECT actor_id FROM actors WHERE actor_id = 'qwen2.5:7b'").fetchone()[0],
    }
    
    # ==================== SESSION A: EXTRACTION ====================
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name, 
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 1, 'session_a_gemma3_extract', 0, 1, NULL, 'isolated', ?, 1)
    """, (recipe_id, actors['gemma3']))
    
    session_a_id = cursor.lastrowid
    print(f"  Session A (ID {session_a_id}): gemma3:1b extraction")
    
    # Session A Instruction
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description, prompt_template, 
            timeout_seconds, enabled
        ) VALUES (?, 1, 'Extract with gemma3:1b', ?, 60, 1)
    """, (session_a_id, """Create a concise job description summary for this job posting:

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

Extract ONLY from the provided posting. Do not add information."""))
    
    # ==================== SESSION B: GEMMA2 GRADE ====================
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name, 
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 2, 'session_b_gemma2_grade', 0, 2, ?, 'isolated', ?, 1)
    """, (recipe_id, session_a_id, actors['gemma2']))
    
    session_b_id = cursor.lastrowid
    print(f"  Session B (ID {session_b_id}): gemma2:latest grading")
    
    # Session B Instruction
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description, prompt_template, 
            timeout_seconds, enabled
        ) VALUES (?, 1, 'Grade with gemma2:latest', ?, 60, 1)
    """, (session_b_id, """# Instructions: 
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

Start your response with [PASS] or [FAIL], then explain your reasoning."""))
    
    # ==================== SESSION C: QWEN2.5 GRADE ====================
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name, 
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 3, 'session_c_qwen25_grade', 0, 2, ?, 'isolated', ?, 1)
    """, (recipe_id, session_a_id, actors['qwen25']))
    
    session_c_id = cursor.lastrowid
    print(f"  Session C (ID {session_c_id}): qwen2.5:7b grading")
    
    # Session C Instruction
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description, prompt_template, 
            timeout_seconds, enabled
        ) VALUES (?, 1, 'Grade with qwen2.5:7b', ?, 60, 1)
    """, (session_c_id, """# Instructions: 
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

Start your response with [PASS] or [FAIL], then explain your reasoning."""))
    
    # ==================== SESSION D: QWEN2.5 IMPROVE ====================
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name, 
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 4, 'session_d_qwen25_improve', 0, 3, ?, 'isolated', ?, 1)
    """, (recipe_id, session_c_id, actors['qwen25']))
    
    session_d_id = cursor.lastrowid
    print(f"  Session D (ID {session_d_id}): qwen2.5:7b improvement")
    
    # Session D Instruction
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description, prompt_template, 
            timeout_seconds, enabled
        ) VALUES (?, 1, 'Improve extraction based on previous grade', ?, 90, 1)
    """, (session_d_id, """# Your Task: Improve the job summary based on previous feedback

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

Return ONLY the improved summary (or unchanged summary if [PASS]). No explanations."""))
    
    # ==================== SESSION E: QWEN2.5 RE-GRADE ====================
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name, 
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 5, 'session_e_qwen25_regrade', 0, 4, ?, 'isolated', ?, 1)
    """, (recipe_id, session_d_id, actors['qwen25']))
    
    session_e_id = cursor.lastrowid
    print(f"  Session E (ID {session_e_id}): qwen2.5:7b re-grading")
    
    # Session E Instruction
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description, prompt_template, 
            timeout_seconds, enabled
        ) VALUES (?, 1, 'Re-grade the improved version', ?, 60, 1)
    """, (session_e_id, """# Instructions: 
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

Start your response with [PASS] or [FAIL], then explain your reasoning."""))
    
    # ==================== SESSION F: CREATE TICKET ====================
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name, 
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 6, 'session_f_create_ticket', 0, 5, ?, 'isolated', ?, 1)
    """, (recipe_id, session_e_id, actors['qwen25']))
    
    session_f_id = cursor.lastrowid
    print(f"  Session F (ID {session_f_id}): Create ticket if still failed")
    
    # Session F Instruction - uses qwen to create structured ticket
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description, prompt_template, 
            timeout_seconds, enabled
        ) VALUES (?, 1, 'Create ticket summary for human review', ?, 60, 1)
    """, (session_f_id, """# Create a ticket summary for human review

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
- Detail what issues persist after improvement attempt"""))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Recipe {recipe_id} created successfully!")
    print(f"\nPipeline Flow:")
    print(f"  Session A → Extract (gemma3:1b)")
    print(f"  Session B → Grade (gemma2:latest)")
    print(f"  Session C → Grade (qwen2.5:7b)")
    print(f"  Session D → Improve if C=[FAIL] (qwen2.5:7b)")
    print(f"  Session E → Re-grade improved (qwen2.5:7b)")
    print(f"  Session F → Create ticket (structured output)")
    print(f"\n💡 Next: Use variation from Recipe 1113 that failed qwen2.5")
    
    return recipe_id

if __name__ == "__main__":
    recipe_id = create_recipe()
