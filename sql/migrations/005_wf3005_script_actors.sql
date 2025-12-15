-- Migration: Create WF3005 Script Actors
-- Purpose: Script actors for hierarchy consultation workflow (UEO schema)
-- Date: 2025-12-07
-- Author: Sandy

BEGIN;

-- ============================================================================
-- Actor 1: ueo_orphan_fetcher - Fetch orphan skills from entities table
-- ============================================================================

INSERT INTO actors (
    actor_name,
    actor_type,
    url,
    enabled,
    script_language,
    script_code,
    input_format,
    output_format
) VALUES (
    'ueo_orphan_fetcher',
    'script',
    'script://ueo_orphan_fetcher',
    true,
    'python',
    '#!/usr/bin/env python3
"""
UEO Orphan Fetcher - WF3005 Step 1

Fetches a batch of orphan skills from the UEO entities table.
Orphans = skills with no parent relationship in entity_relationships.
"""

import json
import sys
import os
import psycopg2
from dotenv import load_dotenv

BATCH_SIZE = 25  # Per Arden guidance


def fetch_orphan_skills(batch_size: int = BATCH_SIZE) -> dict:
    """Fetch next batch of orphan skills from entities table."""
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

        # Get skills with no parent relationship (orphans)
        cursor.execute("""
            SELECT e.entity_id, e.canonical_name, en.display_name
            FROM entities e
            LEFT JOIN entity_names en ON e.entity_id = en.entity_id 
                AND en.is_primary = true AND en.language = ''en''
            WHERE e.entity_type = ''skill''
              AND e.status = ''active''
              AND NOT EXISTS (
                  SELECT 1 FROM entity_relationships er 
                  WHERE er.entity_id = e.entity_id 
                  AND er.relationship = ''child_of''
              )
              AND NOT EXISTS (
                  SELECT 1 FROM entity_relationships er 
                  WHERE er.related_entity_id = e.entity_id 
                  AND er.relationship = ''child_of''
              )
              AND NOT EXISTS (
                  SELECT 1 FROM registry_decisions rd
                  WHERE rd.subject_entity_id = e.entity_id
                  AND rd.decision_type = ''assign''
              )
            ORDER BY e.entity_id
            LIMIT %s
        """, (batch_size,))

        skills = cursor.fetchall()

        if not skills:
            return {"status": "complete", "message": "No more orphan skills to process"}

        skill_list = [
            {"entity_id": s[0], "canonical_name": s[1], "display_name": s[2] or s[1]}
            for s in skills
        ]

        # Format for prompt
        formatted = "\\n".join([
            f"{i+1}. {s[''display_name'']} (id:{s[''entity_id'']})"
            for i, s in enumerate(skill_list)
        ])

        return {
            "status": "success",
            "batch_size": len(skill_list),
            "orphan_skills": formatted,
            "skill_data": skill_list
        }

    finally:
        conn.close()


if __name__ == "__main__":
    result = fetch_orphan_skills()
    print(json.dumps(result, indent=2))
',
    'none',
    'json'
) ON CONFLICT (actor_name) DO UPDATE SET
    script_code = EXCLUDED.script_code,
    enabled = EXCLUDED.enabled;

-- ============================================================================
-- Actor 2: ueo_decision_saver - Save decisions to registry_decisions
-- ============================================================================

INSERT INTO actors (
    actor_name,
    actor_type,
    url,
    enabled,
    script_language,
    script_code,
    input_format,
    output_format
) VALUES (
    'ueo_decision_saver',
    'script',
    'script://ueo_decision_saver',
    true,
    'python',
    '#!/usr/bin/env python3
"""
UEO Decision Saver - WF3005 Step 4

Parses classifier and grader outputs, saves to registry_decisions.
Auto-approves when: confidence >= 0.9 AND grader agrees.
"""

import json
import sys
import os
import re
import psycopg2
from dotenv import load_dotenv

AUTO_APPROVE_THRESHOLD = 0.9


def save_decisions(classifier_output: str, grader_output: str) -> dict:
    """Parse outputs and save to registry_decisions."""
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

        # Parse classifier output (one JSON per line)
        classifier_decisions = {}
        for line in classifier_output.strip().split("\\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    d = json.loads(line)
                    classifier_decisions[d["skill"]] = d
                except:
                    continue

        # Parse grader output
        grader_decisions = {}
        for line in grader_output.strip().split("\\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    d = json.loads(line)
                    grader_decisions[d["skill"]] = d
                except:
                    continue

        saved = 0
        auto_approved = 0
        pending = 0

        for skill_name, class_d in classifier_decisions.items():
            grade_d = grader_decisions.get(skill_name, {})
            
            # Determine final parent
            if grade_d.get("agree", True):
                final_parent = class_d["parent"]
            else:
                final_parent = grade_d.get("corrected_parent") or class_d["parent"]

            confidence = class_d.get("confidence", 0.5)
            agrees = grade_d.get("agree", False)

            # Determine review status
            if confidence >= AUTO_APPROVE_THRESHOLD and agrees:
                review_status = "auto_approved"
                auto_approved += 1
            else:
                review_status = "pending"
                pending += 1

            # Find entity_id for skill
            cursor.execute("""
                SELECT entity_id FROM entities 
                WHERE canonical_name = %s AND entity_type = ''skill''
            """, (skill_name.lower().replace(" ", "_"),))
            row = cursor.fetchone()
            if not row:
                # Try display_name match
                cursor.execute("""
                    SELECT e.entity_id FROM entities e
                    JOIN entity_names en ON e.entity_id = en.entity_id
                    WHERE en.display_name ILIKE %s AND e.entity_type = ''skill''
                """, (skill_name,))
                row = cursor.fetchone()
            
            if not row:
                continue  # Skip if skill not found
            
            subject_entity_id = row[0]

            # Find target entity_id (the parent/domain)
            parent_name = final_parent.replace("NEW:", "").lower().replace(" ", "_")
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
                subject_entity_id,
                target_entity_id,
                confidence,
                json.dumps({
                    "classifier": class_d.get("reasoning"),
                    "grader": grade_d.get("reasoning"),
                    "grader_agrees": agrees
                }),
                review_status
            ))
            saved += 1

        conn.commit()

        return {
            "status": "success",
            "saved": saved,
            "auto_approved": auto_approved,
            "pending": pending
        }

    except Exception as e:
        conn.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    # Expect classifier and grader output from env or stdin
    classifier = os.getenv("CLASSIFIER_OUTPUT", "")
    grader = os.getenv("GRADER_OUTPUT", "")
    if not classifier:
        classifier = sys.stdin.read()
    result = save_decisions(classifier, grader)
    print(json.dumps(result, indent=2))
',
    'json',
    'json'
) ON CONFLICT (actor_name) DO UPDATE SET
    script_code = EXCLUDED.script_code,
    enabled = EXCLUDED.enabled;

-- ============================================================================
-- Update WF3005 to use new actors
-- ============================================================================

UPDATE conversations 
SET actor_id = (SELECT actor_id FROM actors WHERE actor_name = 'ueo_orphan_fetcher')
WHERE canonical_name = 'w3005_c1_fetch';

UPDATE conversations 
SET actor_id = (SELECT actor_id FROM actors WHERE actor_name = 'ueo_decision_saver')
WHERE canonical_name = 'w3005_c4_save';

COMMIT;

-- Verify
SELECT actor_id, actor_name, actor_type FROM actors 
WHERE actor_name IN ('ueo_orphan_fetcher', 'ueo_decision_saver');
