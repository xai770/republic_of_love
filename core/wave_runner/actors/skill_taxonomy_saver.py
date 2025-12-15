#!/usr/bin/env python3
"""
Skill Taxonomy Saver - WF3002 Step 3

Applies LLM decisions to the skill taxonomy:
- ALIAS: Update posting_skills to point to existing skill
- NEW: Create new skill in skill_aliases, optionally place in hierarchy
- SPLIT: Create multiple posting_skills entries for compound skills
- SKIP: Mark as invalid (not a real skill)

Author: Sandy
Date: December 4, 2025
"""

import json
import sys
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


class SkillTaxonomySaver:
    """Applies taxonomy decisions to the database."""
    
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    def _mark_pending_reviewed(self, raw_skill_name: str, status: str = 'approved'):
        """Mark skill as reviewed in skills_pending_taxonomy."""
        self.cursor.execute("""
            UPDATE skills_pending_taxonomy
            SET review_status = %s, reviewed_at = NOW(), reviewed_by = 'wf3002_taxonomy_saver'
            WHERE LOWER(raw_skill_name) = LOWER(%s)
        """, (status, raw_skill_name))
    
    def apply_decision(self, decision: dict, raw_skill_name: str) -> dict:
        """
        Apply a taxonomy decision for a raw skill name.
        
        Args:
            decision: LLM decision with type and details
            raw_skill_name: The original unmatched skill name
            
        Returns:
            Result dict with status and details
        """
        decision_type = decision.get('decision', '').upper()
        
        if decision_type == 'ALIAS':
            return self._apply_alias(decision, raw_skill_name)
        elif decision_type == 'NEW':
            return self._apply_new(decision, raw_skill_name)
        elif decision_type == 'SPLIT':
            return self._apply_split(decision, raw_skill_name)
        elif decision_type == 'SKIP':
            return self._apply_skip(decision, raw_skill_name)
        else:
            return {
                'status': 'error',
                'error': f'Unknown decision type: {decision_type}'
            }
    
    def _apply_alias(self, decision: dict, raw_skill_name: str) -> dict:
        """Map raw skill to existing skill_id."""
        target_skill_id = decision.get('skill_id')
        if not target_skill_id:
            return {'status': 'error', 'error': 'ALIAS decision missing skill_id'}
        
        try:
            # Verify target skill exists
            self.cursor.execute(
                "SELECT skill_name FROM skill_aliases WHERE skill_id = %s",
                (target_skill_id,)
            )
            target = self.cursor.fetchone()
            if not target:
                return {'status': 'error', 'error': f'Target skill_id {target_skill_id} not found'}
            
            # Update all posting_skills with this raw_skill_name
            self.cursor.execute("""
                UPDATE posting_skills
                SET skill_id = %s, updated_at = NOW()
                WHERE LOWER(raw_skill_name) = LOWER(%s)
                  AND skill_id IS NULL
            """, (target_skill_id, raw_skill_name))
            
            rows_updated = self.cursor.rowcount
            
            # Note: profile_skills doesn't store raw_skill_name, so can't be updated here.
            # Profiles need to be re-processed via WF1125 to pick up newly mapped skills.
            
            # Mark as reviewed in pending table
            self._mark_pending_reviewed(raw_skill_name, 'approved')
            
            self.conn.commit()
            
            return {
                'status': 'success',
                'action': 'ALIAS',
                'raw_skill_name': raw_skill_name,
                'mapped_to_skill_id': target_skill_id,
                'mapped_to_skill_name': target['skill_name'],
                'rows_updated': rows_updated
            }
            
        except Exception as e:
            self.conn.rollback()
            return {'status': 'error', 'error': str(e)}
    
    def _apply_new(self, decision: dict, raw_skill_name: str) -> dict:
        """Create new skill in taxonomy."""
        new_skill_name = decision.get('new_skill_name', raw_skill_name)
        parent_skill_id = decision.get('parent_skill_id')
        
        # Convert to UPPER_SNAKE_CASE for skill_name
        canonical_name = new_skill_name.upper().replace(' ', '_').replace('-', '_')
        
        try:
            # Check if skill already exists
            self.cursor.execute(
                "SELECT skill_id FROM skill_aliases WHERE UPPER(skill_name) = %s",
                (canonical_name,)
            )
            existing = self.cursor.fetchone()
            if existing:
                # Skill exists - treat as ALIAS instead
                return self._apply_alias({'skill_id': existing['skill_id']}, raw_skill_name)
            
            # Create new skill
            self.cursor.execute("""
                INSERT INTO skill_aliases (skill_name, display_name, skill_alias, created_by)
                VALUES (%s, %s, %s, 'wf3002_taxonomy_saver')
                RETURNING skill_id
            """, (canonical_name, new_skill_name, raw_skill_name.lower()))
            
            new_skill_id = self.cursor.fetchone()['skill_id']
            
            # Add to hierarchy if parent specified
            if parent_skill_id:
                self.cursor.execute("""
                    INSERT INTO skill_hierarchy (skill_id, parent_skill_id, created_by)
                    VALUES (%s, %s, 'wf3002_taxonomy_saver')
                    ON CONFLICT DO NOTHING
                """, (new_skill_id, parent_skill_id))
            
            # Update posting_skills
            self.cursor.execute("""
                UPDATE posting_skills
                SET skill_id = %s, updated_at = NOW()
                WHERE LOWER(raw_skill_name) = LOWER(%s)
                  AND skill_id IS NULL
            """, (new_skill_id, raw_skill_name))
            
            rows_updated = self.cursor.rowcount
            
            # Note: profile_skills doesn't store raw_skill_name, so can't be updated here.
            # Profiles need to be re-processed via WF1125 to pick up newly created skills.
            
            # Mark as reviewed in pending table
            self._mark_pending_reviewed(raw_skill_name, 'approved')
            
            self.conn.commit()
            
            return {
                'status': 'success',
                'action': 'NEW',
                'raw_skill_name': raw_skill_name,
                'created_skill_id': new_skill_id,
                'created_skill_name': canonical_name,
                'parent_skill_id': parent_skill_id,
                'rows_updated': rows_updated
            }
            
        except Exception as e:
            self.conn.rollback()
            return {'status': 'error', 'error': str(e)}
    
    def _apply_split(self, decision: dict, raw_skill_name: str) -> dict:
        """Split compound skill into multiple skills."""
        split_into = decision.get('split_into', [])
        if not split_into:
            return {'status': 'error', 'error': 'SPLIT decision missing split_into array'}
        
        try:
            # Get all posting_skills rows with this raw_skill_name
            self.cursor.execute("""
                SELECT posting_skill_id, posting_id, importance, weight, proficiency
                FROM posting_skills
                WHERE LOWER(raw_skill_name) = LOWER(%s)
                  AND skill_id IS NULL
            """, (raw_skill_name,))
            
            original_rows = self.cursor.fetchall()
            if not original_rows:
                return {'status': 'warning', 'message': 'No rows to split'}
            
            created_count = 0
            skill_ids_used = []
            
            for original in original_rows:
                for skill_spec in split_into:
                    skill_id = skill_spec.get('skill_id')
                    
                    # If new skill needed, create it
                    if not skill_id and skill_spec.get('new_skill_name'):
                        new_name = skill_spec['new_skill_name']
                        canonical = new_name.upper().replace(' ', '_')
                        
                        # Check if exists
                        self.cursor.execute(
                            "SELECT skill_id FROM skill_aliases WHERE UPPER(skill_name) = %s",
                            (canonical,)
                        )
                        existing = self.cursor.fetchone()
                        if existing:
                            skill_id = existing['skill_id']
                        else:
                            self.cursor.execute("""
                                INSERT INTO skill_aliases (skill_name, display_name, skill_alias, created_by)
                                VALUES (%s, %s, %s, 'wf3002_taxonomy_saver')
                                RETURNING skill_id
                            """, (canonical, new_name, new_name.lower()))
                            skill_id = self.cursor.fetchone()['skill_id']
                            
                            # Add to hierarchy if parent specified
                            if skill_spec.get('parent_skill_id'):
                                self.cursor.execute("""
                                    INSERT INTO skill_hierarchy (skill_id, parent_skill_id, created_by)
                                    VALUES (%s, %s, 'wf3002_taxonomy_saver')
                                    ON CONFLICT DO NOTHING
                                """, (skill_id, skill_spec['parent_skill_id']))
                    
                    if skill_id:
                        # Create new posting_skill row (or update if first in split)
                        if skill_id not in skill_ids_used:
                            skill_ids_used.append(skill_id)
                        
                        # Insert new row for this skill
                        self.cursor.execute("""
                            INSERT INTO posting_skills 
                                (posting_id, skill_id, raw_skill_name, importance, weight, proficiency, extracted_by)
                            VALUES (%s, %s, %s, %s, %s, %s, 'wf3002_split')
                            ON CONFLICT (posting_id, skill_id) DO NOTHING
                        """, (
                            original['posting_id'],
                            skill_id,
                            raw_skill_name,  # Keep original for tracing
                            original['importance'],
                            original['weight'],
                            original['proficiency']
                        ))
                        created_count += self.cursor.rowcount
                
                # Delete the original compound row
                self.cursor.execute(
                    "DELETE FROM posting_skills WHERE posting_skill_id = %s",
                    (original['posting_skill_id'],)
                )
            
            # Mark as reviewed in pending table
            self._mark_pending_reviewed(raw_skill_name, 'approved')
            
            self.conn.commit()
            
            return {
                'status': 'success',
                'action': 'SPLIT',
                'raw_skill_name': raw_skill_name,
                'split_into_skill_ids': skill_ids_used,
                'original_rows_processed': len(original_rows),
                'new_rows_created': created_count
            }
            
        except Exception as e:
            self.conn.rollback()
            return {'status': 'error', 'error': str(e)}
    
    def _apply_skip(self, decision: dict, raw_skill_name: str) -> dict:
        """Mark skill as invalid (not a real skill)."""
        try:
            # We don't have an 'invalid' column - let's just delete these
            # Or we could add extracted_by = 'wf3002_skipped' as a marker
            self.cursor.execute("""
                UPDATE posting_skills
                SET extracted_by = 'wf3002_skipped', updated_at = NOW()
                WHERE LOWER(raw_skill_name) = LOWER(%s)
                  AND skill_id IS NULL
            """, (raw_skill_name,))
            
            rows_updated = self.cursor.rowcount
            
            # Mark as rejected in pending table (not a real skill)
            self._mark_pending_reviewed(raw_skill_name, 'rejected')
            
            self.conn.commit()
            
            return {
                'status': 'success',
                'action': 'SKIP',
                'raw_skill_name': raw_skill_name,
                'reason': decision.get('reasoning', 'Not a real skill'),
                'rows_marked': rows_updated
            }
            
        except Exception as e:
            self.conn.rollback()
            return {'status': 'error', 'error': str(e)}


def main():
    """CLI entry point."""
    load_dotenv()
    
    # Read input from stdin
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            pass
    
    # Expected input:
    # {
    #   "raw_skill_name": "Machine Learning",
    #   "decision": {"decision": "ALIAS", "skill_id": 60, ...}
    # }
    
    raw_skill_name = input_data.get('raw_skill_name')
    
    # Handle various input formats
    # Format 1: {"raw_skill_name": "X", "decision": {"decision": "ALIAS", ...}}
    # Format 2: {"raw_skill_name": "X", "decision": "ALIAS", "skill_id": 60}
    decision = input_data.get('decision')
    if isinstance(decision, str):
        # Flat format - decision type is a string, other fields at top level
        decision = {
            'decision': decision,
            'skill_id': input_data.get('skill_id'),
            'new_skill_name': input_data.get('new_skill_name'),
            'parent_skill_id': input_data.get('parent_skill_id'),
            'split_into': input_data.get('split_into'),
            'reasoning': input_data.get('reasoning'),
            'confidence': input_data.get('confidence')
        }
    elif decision is None:
        # No nested decision - use input_data directly
        decision = input_data
    
    if not raw_skill_name:
        print(json.dumps({'status': 'error', 'error': 'Missing raw_skill_name'}))
        return
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', 'base_yoga_secure_2025')
    )
    
    try:
        saver = SkillTaxonomySaver(conn)
        result = saver.apply_decision(decision, raw_skill_name)
        print(json.dumps(result, indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
