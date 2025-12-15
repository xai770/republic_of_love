-- Migration: Add Triage step to WF3005
-- Purpose: Add ALIAS/NEW/SPLIT/SKIP decision step between fetch and classify
-- This absorbs functionality from deprecated WF3002 into WF3005
-- Date: 2025-12-08

BEGIN;

-- 0. Update entity_orphan_fetcher to also return sample_skills for ALIAS matching
UPDATE actors SET script_code = '#!/usr/bin/env python3
"""
Entity Registry - Orphan Skill Fetcher - WF3005 Step 1

Fetches orphan skills from Entity Registry.
Orphan = skill with no parent (no child_of relationship in either direction).

Also fetches sample of existing skills for ALIAS matching in triage step.
"""

import json
import sys
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

BATCH_SIZE = 25
SAMPLE_SIZE = 50  # Sample of existing skills for ALIAS matching


def fetch_orphans() -> dict:
    """Fetch next batch of orphan skills + sample for ALIAS matching."""
    load_dotenv()

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME", "turing"),
        user=os.getenv("DB_USER", "base_admin"),
        password=os.getenv("DB_PASSWORD", "")
    )

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get orphan skills not yet processed
        cursor.execute("""
            WITH orphans AS (
                SELECT e.entity_id, e.canonical_name, en.display_name
                FROM entities e
                JOIN entity_names en ON e.entity_id = en.entity_id AND en.is_primary = true
                WHERE e.entity_type = ''skill''
                  AND e.status = ''active''
                  AND NOT EXISTS (
                      SELECT 1 FROM entity_relationships er 
                      WHERE er.entity_id = e.entity_id AND er.relationship = ''child_of''
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM entity_relationships er 
                      WHERE er.related_entity_id = e.entity_id AND er.relationship = ''child_of''
                  )
            ),
            already_processed AS (
                SELECT DISTINCT subject_entity_id 
                FROM registry_decisions 
                WHERE decision_type = ''assign''
            )
            SELECT o.* FROM orphans o
            WHERE o.entity_id NOT IN (SELECT subject_entity_id FROM already_processed)
            ORDER BY o.entity_id
            LIMIT %s
        """, (BATCH_SIZE,))

        rows = cursor.fetchall()

        # Format for both LLM (pipe-separated) and saver (JSON)
        skill_data = [
            {
                "entity_id": row["entity_id"],
                "display_name": row["display_name"],
                "canonical_name": row["canonical_name"]
            }
            for row in rows
        ]

        # Create LLM-friendly format: "entity_id|display_name"
        orphan_skills_text = "\\n".join([
            f"{s[''entity_id'']}|{s[''display_name'']}"
            for s in skill_data
        ])
        
        # Get sample of existing skills for ALIAS matching
        cursor.execute("""
            SELECT e.entity_id, en.display_name
            FROM entities e
            JOIN entity_names en ON e.entity_id = en.entity_id AND en.is_primary = true
            WHERE e.entity_type = ''skill''
              AND e.status = ''active''
              AND EXISTS (
                  SELECT 1 FROM entity_relationships er 
                  WHERE er.entity_id = e.entity_id AND er.relationship = ''child_of''
              )
            ORDER BY RANDOM()
            LIMIT %s
        """, (SAMPLE_SIZE,))
        
        sample_rows = cursor.fetchall()
        sample_skills_text = ", ".join([
            f"{r[''display_name'']} (id:{r[''entity_id'']})"
            for r in sample_rows
        ])

        return {
            "status": "success",
            "batch_size": len(rows),
            "skill_data": skill_data,
            "orphan_skills": orphan_skills_text,  # For template substitution
            "sample_skills": sample_skills_text   # For ALIAS matching in triage
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    result = fetch_orphans()
    print(json.dumps(result, indent=2))
'
WHERE actor_name = 'entity_orphan_fetcher';

-- 1. We don't need a new actor - we'll reuse qwen2.5:7b which already exists
-- The triage conversation will use the same model as classify

-- 2. Create the triage conversation
INSERT INTO conversations (
    conversation_name, 
    conversation_description,
    actor_id,
    context_strategy,
    max_instruction_runs,
    enabled,
    canonical_name,
    conversation_type
) 
SELECT 
    'w3005_triage_skills',
    'Triage each skill: ALIAS (map to existing), NEW (genuinely new skill), SPLIT (compound skill), SKIP (not a skill)',
    (SELECT actor_id FROM actors WHERE actor_name = 'qwen2.5:7b' LIMIT 1),
    'isolated',
    50,
    true,
    'w3005_c1b_triage',
    'single_actor'
WHERE NOT EXISTS (SELECT 1 FROM conversations WHERE canonical_name = 'w3005_c1b_triage');

-- 3. Get the new conversation ID and update workflow
DO $$
DECLARE
    v_triage_conv_id INTEGER;
    v_classify_conv_id INTEGER := 9230;
    v_fetch_instr_id INTEGER := 3440;
    v_triage_instr_id INTEGER;
BEGIN
    SELECT conversation_id INTO v_triage_conv_id 
    FROM conversations WHERE canonical_name = 'w3005_c1b_triage';
    
    -- Shift execution_order for all conversations after fetch (order >= 2)
    -- Update in reverse order to avoid unique constraint violation
    FOR i IN REVERSE 10..2 LOOP
        UPDATE workflow_conversations 
        SET execution_order = execution_order + 1
        WHERE workflow_id = 3005 AND execution_order = i;
    END LOOP;
    
    -- 4. Link triage to WF3005 with execution_order = 2
    INSERT INTO workflow_conversations (workflow_id, conversation_id, is_entry_point, execution_order)
    SELECT 3005, v_triage_conv_id, false, 2
    WHERE NOT EXISTS (
        SELECT 1 FROM workflow_conversations 
        WHERE workflow_id = 3005 AND conversation_id = v_triage_conv_id
    );
    
    -- 5. Create the triage instruction with prompt
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        step_description,
        prompt_template,
        timeout_seconds,
        is_terminal
    )
    SELECT 
        v_triage_conv_id,
        'w3005_triage_orphans',
        1,
        'Classify each skill as ALIAS/NEW/SPLIT/SKIP before categorization',
        'You are a skill registry expert. For each orphan skill, decide its fate:

**Decision options:**
1. **ALIAS** - This is another name for an existing skill. Map it to the existing entity_id.
2. **NEW** - This is a genuinely new skill that should be added to the registry.
3. **SPLIT** - This is a compound skill (like "Python/R" or "SQL and Excel"). Split into components.
4. **SKIP** - This is NOT a skill (e.g., "3+ years experience", "team player", "German B2", job titles).

**Skills to triage (format: entity_id|display_name):**
{orphan_skills}

**Existing skills in registry (sample for ALIAS matching):**
{sample_skills}

For EACH skill, output ONE JSON object per line:

For ALIAS:
{"entity_id": 123, "decision": "ALIAS", "target_entity_id": 456, "confidence": 0.9, "reasoning": "Same as existing Python"}

For NEW:
{"entity_id": 123, "decision": "NEW", "confidence": 0.85, "reasoning": "Genuine new skill not in registry"}

For SPLIT:
{"entity_id": 123, "decision": "SPLIT", "split_into": ["Python", "R"], "confidence": 0.9, "reasoning": "Compound skill Python/R"}

For SKIP:
{"entity_id": 123, "decision": "SKIP", "confidence": 0.95, "reasoning": "Not a skill - experience requirement"}

Output ONLY JSON objects, one per line. No other text.',
        300,
        false
    WHERE NOT EXISTS (
        SELECT 1 FROM instructions i 
        JOIN conversations c ON i.conversation_id = c.conversation_id
        WHERE c.canonical_name = 'w3005_c1b_triage'
    )
    RETURNING instruction_id INTO v_triage_instr_id;
    
    -- Get instruction_id if it already existed
    IF v_triage_instr_id IS NULL THEN
        SELECT i.instruction_id INTO v_triage_instr_id
        FROM instructions i
        JOIN conversations c ON i.conversation_id = c.conversation_id
        WHERE c.canonical_name = 'w3005_c1b_triage'
        LIMIT 1;
    END IF;
    
    -- 6. Update fetch (3440) to branch to triage instead of classify
    UPDATE instruction_steps 
    SET next_conversation_id = v_triage_conv_id,
        branch_description = 'After fetch, triage skills first'
    WHERE instruction_id = v_fetch_instr_id
      AND next_conversation_id = v_classify_conv_id;
    
    -- 7. Add branch from triage to classify
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority,
        branch_description,
        enabled
    )
    SELECT 
        'triage_to_classify',
        v_triage_instr_id,
        '*',
        v_classify_conv_id,
        5,
        'After triage, proceed to categorize NEW skills',
        true
    WHERE v_triage_instr_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM instruction_steps 
        WHERE instruction_id = v_triage_instr_id 
          AND next_conversation_id = v_classify_conv_id
    );
    
    RAISE NOTICE 'Triage conversation created: %, instruction: %', v_triage_conv_id, v_triage_instr_id;
END $$;

-- 8. Verify the changes
SELECT 'Verification' as check_type;
SELECT c.conversation_id, c.canonical_name, c.conversation_name 
FROM conversations c 
JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id
WHERE wc.workflow_id = 3005
ORDER BY c.conversation_id;

COMMIT;
