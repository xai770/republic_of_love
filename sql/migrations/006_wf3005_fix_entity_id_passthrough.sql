-- Migration 006: Fix WF3005 entity_id passthrough
-- ============================================================================
-- Problem: Classifier and grader prompts don't include entity_id, so saver
--          can't correlate back to the original entities.
-- Solution: Update prompts to require entity_id in outputs.
-- ============================================================================

BEGIN;

-- ============================================================================
-- Fix 1: Update classifier prompt (instruction 3436)
-- ============================================================================

UPDATE instructions 
SET prompt_template = 'You are a professional skills taxonomy expert. Your task is to categorize orphan skills into the appropriate domain.

CURRENT DOMAINS (choose from these, or prefix with NEW: if none fit):
- Technology (programming, software, infrastructure)
- Data_And_Analytics (data science, BI, statistics)
- Business_Operations (operations, logistics, supply chain)
- People_And_Communication (leadership, teamwork, presentation)
- Compliance_And_Risk (legal, audit, regulatory)
- Project_And_Product (PM, product management, agile)
- Corporate_Culture (DEI, values, ethics)
- Specialized_Knowledge (domain-specific expertise)

SKILLS TO CATEGORIZE (format: entity_id|display_name):
{orphan_skills}

For EACH skill, output a JSON object on its own line. INCLUDE the entity_id:
{"entity_id": 5655, "skill": "Data_Analysis", "parent": "Data_And_Analytics", "confidence": 0.85, "reasoning": "One sentence explanation"}

If no domain fits, use NEW: prefix:
{"entity_id": 1234, "skill": "Some_Skill", "parent": "NEW:Suggested_Category", "confidence": 0.7, "reasoning": "Why new category needed"}

Output ONLY the JSON objects, one per line. No other text.',
    updated_at = NOW()
WHERE instruction_id = 3436;

-- ============================================================================
-- Fix 2: Update grader prompt (instruction 3437)
-- ============================================================================

UPDATE instructions 
SET prompt_template = 'You are an expert skills taxonomy grader. Review the classifier''s categorization decisions.

VALID DOMAINS:
- Technology (programming, software, infrastructure)
- Data_And_Analytics (data science, BI, statistics)
- Business_Operations (operations, logistics, supply chain)
- People_And_Communication (leadership, teamwork, presentation)
- Compliance_And_Risk (legal, audit, regulatory)
- Project_And_Product (PM, product management, agile)
- Corporate_Culture (DEI, values, ethics)
- Specialized_Knowledge (domain-specific expertise)

CLASSIFIER DECISIONS TO REVIEW:
{parent_response}

For EACH decision, output a JSON object on its own line. PRESERVE the entity_id:
{"entity_id": 5655, "skill": "Data_Analysis", "agree": true, "original_parent": "Data_And_Analytics", "corrected_parent": null, "reasoning": "Correct categorization"}

If you disagree:
{"entity_id": 5655, "skill": "Data_Analysis", "agree": false, "original_parent": "Technology", "corrected_parent": "Data_And_Analytics", "reasoning": "Better fit because..."}

Output ONLY the JSON objects, one per line. No other text.',
    updated_at = NOW()
WHERE instruction_id = 3437;

-- ============================================================================
-- Fix 3: Update fetcher to output pipe-separated format for LLM prompt
-- ============================================================================

UPDATE actors
SET script_code = '#!/usr/bin/env python3
"""
UEO Orphan Fetcher - WF3005 Step 1

Fetches orphan skills from UEO entities table.
Orphan = skill with no parent (no child_of relationship in either direction).
"""

import json
import sys
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

BATCH_SIZE = 25


def fetch_orphans() -> dict:
    """Fetch next batch of orphan skills."""
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

        return {
            "status": "success",
            "batch_size": len(rows),
            "skill_data": skill_data,
            "orphan_skills": orphan_skills_text  # For template substitution
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    result = fetch_orphans()
    print(json.dumps(result, indent=2))
',
    updated_at = NOW()
WHERE actor_name = 'ueo_orphan_fetcher';

-- ============================================================================
-- Fix 4: Update saver to use entity_id from grader output
-- ============================================================================

UPDATE actors
SET script_code = '#!/usr/bin/env python3
"""
UEO Decision Saver - WF3005 Step 4

Parses grader output (which includes entity_id), saves to registry_decisions.
Auto-approves when: confidence >= 0.9 AND grader agrees.
"""

import json
import sys
import os
import re
import psycopg2
from dotenv import load_dotenv

AUTO_APPROVE_THRESHOLD = 0.9


def parse_json_lines(text: str) -> list:
    """Parse newline-delimited JSON objects."""
    results = []
    for line in text.strip().split("\\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return results


def save_decisions(grader_output: str, classifier_output: str = "") -> dict:
    """Parse grader output and save to registry_decisions."""
    load_dotenv()

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME", "turing"),
        user=os.getenv("DB_USER", "base_admin"),
        password=os.getenv("DB_PASSWORD", "")
    )

    try:
        cursor = conn.cursor()

        # Parse grader output (has entity_id, agree, original_parent, corrected_parent)
        grader_decisions = parse_json_lines(grader_output)
        
        # Build classifier lookup for confidence scores
        classifier_decisions = {}
        for d in parse_json_lines(classifier_output):
            if "entity_id" in d:
                classifier_decisions[d["entity_id"]] = d

        saved = 0
        auto_approved = 0
        pending = 0
        errors = []

        for grade_d in grader_decisions:
            entity_id = grade_d.get("entity_id")
            if not entity_id:
                errors.append(f"Missing entity_id in grader output: {grade_d}")
                continue

            # Get classifier data for this entity
            class_d = classifier_decisions.get(entity_id, {})
            
            # Determine final parent
            agrees = grade_d.get("agree", False)
            if agrees:
                final_parent = grade_d.get("original_parent")
            else:
                final_parent = grade_d.get("corrected_parent") or grade_d.get("original_parent")

            if not final_parent:
                errors.append(f"No parent determined for entity {entity_id}")
                continue

            # Get confidence from classifier, default 0.5
            confidence = class_d.get("confidence", 0.5)

            # Determine review status
            if confidence >= AUTO_APPROVE_THRESHOLD and agrees:
                review_status = "auto_approved"
                auto_approved += 1
            else:
                review_status = "pending"
                pending += 1

            # Handle NEW: prefix
            parent_name = final_parent.replace("NEW:", "").lower().replace(" ", "_")

            # Find target entity_id (the parent/domain)
            cursor.execute("""
                SELECT entity_id FROM entities 
                WHERE canonical_name = %s AND entity_type = ''skill''
            """, (parent_name,))
            row = cursor.fetchone()
            target_entity_id = row[0] if row else None

            # Save decision
            cursor.execute("""
                INSERT INTO registry_decisions (
                    decision_type,
                    subject_entity_id,
                    target_entity_id,
                    model,
                    confidence,
                    reasoning,
                    review_status,
                    created_at
                ) VALUES (
                    ''assign'',
                    %s,
                    %s,
                    ''qwen2.5:7b+mistral:latest'',
                    %s,
                    %s,
                    %s,
                    now()
                )
            """, (
                entity_id,
                target_entity_id,
                confidence,
                json.dumps({
                    "classifier": class_d.get("reasoning"),
                    "grader": grade_d.get("reasoning"),
                    "grader_agrees": agrees,
                    "final_parent": final_parent
                }),
                review_status
            ))
            saved += 1

        conn.commit()

        return {
            "status": "success",
            "saved": saved,
            "auto_approved": auto_approved,
            "pending": pending,
            "errors": errors[:5] if errors else []  # Limit error output
        }

    except Exception as e:
        conn.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    # Read from parent_response (grader output comes via workflow chain)
    input_data = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
    grader_output = input_data.get("parent_response", "")
    # Classifier output might need to be fetched from chain ancestor
    classifier_output = input_data.get("classifier_response", "")
    result = save_decisions(grader_output, classifier_output)
    print(json.dumps(result, indent=2))
',
    updated_at = NOW()
WHERE actor_name = 'ueo_decision_saver';

COMMIT;

-- Verify updates
SELECT 'Instructions updated:' as status;
SELECT instruction_id, instruction_name, LENGTH(prompt_template) as prompt_len 
FROM instructions WHERE instruction_id IN (3436, 3437);

SELECT 'Actors updated:' as status;
SELECT actor_id, actor_name, LENGTH(script_code) as code_len
FROM actors WHERE actor_name IN ('ueo_orphan_fetcher', 'ueo_decision_saver');
