#!/usr/bin/env python3
"""
owl_names__row_C - Lucy: The Lookup

PURPOSE:
Lucy does exact matching. For each owl_pending item, she searches owl_names
for a case-insensitive match. If found, she creates an alias linking the
raw text to the existing entity. If not found, she marks it lucy_passed
for Alma to do fuzzy matching.

Lucy is a script. Scripts don't hallucinate. She's fast, deterministic, RAQ-friendly.

PREREQUISITE: None - Lucy is the first Keeper in the taxonomy pipeline.

Input:  owl_pending (pending_id, raw_value, owl_type) via work_query
Output: 
  - Match found: owl_names entry + owl_pending.status='merged'
  - No match: owl_pending.status='lucy_passed' (Alma's inbox)

Flow Diagram:
```mermaid
flowchart TD
    A[📋 owl_pending item] --> B{Exact match<br/>in owl_names?}
    B -->|No match| Z1[status='lucy_passed'<br/>→ Alma's inbox]
    B -->|Found| C[Create owl_names entry]
    C --> D[status='merged']
    D --> E[✅ DONE]
```

NO LLM NEEDED - Pure SQL matching. Fast, deterministic, RAQ-friendly.

PIPELINE POSITION:
```
Lucy's work_query:  WHERE status = 'pending'
Alma's work_query:  WHERE status = 'lucy_passed'
Carl's work_query:  WHERE status = 'alma_passed'
```

RAQ Config:
- state_tables: owl_names, owl_pending  
- compare_output_field: output->>'owl_id'

Usage:
    # Via turing-harness:
    ./tools/turing/turing-harness run owl_names__row_C --input '{"pending_id": 123}'
    
    # Standalone:
    python3 actors/owl_names__row_C.py 123

Author: Arden
Date: 2026-01-19
Task Type ID: 9385
"""

import json
import sys
from typing import Dict, Any, Optional

import psycopg2
import psycopg2.extras

# ============================================================================
# SETUP
# ============================================================================

from core.database import get_connection
from core.constants import Status

# ============================================================================
# CONFIGURATION
# ============================================================================
TASK_TYPE_ID = 9385  # owl_names__row_C


# ============================================================================
# ACTOR CLASS
# ============================================================================
class OwlNamesRowC:
    """
    Match owl_pending items to existing OWL entities and create owl_names entries.
    
    This is a NO-LLM actor - pure database matching.
    
    Logic:
    1. Fetch owl_pending item by pending_id
    2. Search owl_names for exact match (case-insensitive)
    3. If found: 
       - Create new owl_names entry (name_type='verbatim')
       - Update owl_pending: status='merged', resolved_owl_id=matched_id
    4. If not found: Leave pending (owl__row_C will handle classification)
    """
    
    def __init__(self, db_conn=None):
        """Initialize with database connection."""
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = get_connection()
            self._owns_connection = True
        self.input_data: Dict[str, Any] = {}
    
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    def process(self) -> Dict[str, Any]:
        """
        Main entry point. Called by pull_daemon.
        
        Returns:
            Dict with:
            - success: bool
            - _consistency: str (e.g., '1/1')
            - owl_id: int (if matched)
            - match_type: 'exact' or 'no_match'
        """
        pending_id = self.input_data.get('pending_id') or self.input_data.get('subject_id')
        
        if not pending_id:
            return {'success': False, 'error': 'No pending_id in input'}
        
        try:
            # PHASE 1: PREFLIGHT
            preflight = self._preflight(pending_id)
            if not preflight['ok']:
                return {
                    'success': False,
                    'skip_reason': preflight['reason'],
                    'error': preflight.get('message'),
                    'pending_id': pending_id,
                }
            
            pending = preflight['data']
            
            # PHASE 2: MATCH
            match_result = self._find_match(pending['raw_value'])
            
            if not match_result['found']:
                # No match - hand off to Alma (fuzzy matching)
                self._update_pending_for_alma(pending_id)
                return {
                    'success': True,
                    '_consistency': '1/1',
                    'pending_id': pending_id,
                    'match_type': 'no_match',
                    'raw_value': pending['raw_value'],
                    'message': 'No exact match - passing to Alma',
                }
            
            # PHASE 3: SAVE
            owl_id = match_result['owl_id']
            
            # Check if this exact name already exists (avoid duplicate)
            if self._name_already_exists(owl_id, pending['raw_value']):
                # Name already linked - just update owl_pending status
                self._update_pending_status(pending_id, owl_id, 'already_linked')
                return {
                    'success': True,
                    '_consistency': '1/1',
                    'pending_id': pending_id,
                    'owl_id': owl_id,
                    'match_type': 'already_linked',
                    'canonical_name': match_result['canonical_name'],
                }
            
            # Create new owl_names entry
            self._create_owl_name(
                owl_id=owl_id,
                display_name=pending['raw_value'],
                name_type='verbatim',
                provenance={'source': 'owl_names__row_C', 'pending_id': pending_id}
            )
            
            # Update owl_pending status
            self._update_pending_status(pending_id, owl_id, 'matched')
            
            return {
                'success': True,
                '_consistency': '1/1',
                'pending_id': pending_id,
                'owl_id': owl_id,
                'match_type': 'exact',
                'canonical_name': match_result['canonical_name'],
                'matched_via': match_result['matched_display_name'],
            }
            
        except Exception as e:
            self.conn.rollback()
            return {
                'success': False,
                'error': str(e),
                'pending_id': pending_id,
            }
    
    # ========================================================================
    # PREFLIGHT
    # ========================================================================
    
    def _preflight(self, pending_id: int) -> Dict:
        """Validate owl_pending item exists and is pending."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT pending_id, owl_type, raw_value, status, source_context
            FROM owl_pending
            WHERE pending_id = %s
        """, (pending_id,))
        
        row = cur.fetchone()
        
        if not row:
            return {'ok': False, 'reason': 'NOT_FOUND', 'message': f'Pending {pending_id} not found'}
        
        if row['status'] != 'pending':
            return {
                'ok': False, 
                'reason': 'ALREADY_PROCESSED', 
                'message': f"Status is '{row['status']}', not 'pending'"
            }
        
        if not row['raw_value'] or len(row['raw_value'].strip()) < 2:
            return {'ok': False, 'reason': 'EMPTY_VALUE', 'message': 'raw_value is empty or too short'}
        
        return {'ok': True, 'data': dict(row)}
    
    # ========================================================================
    # MATCHING
    # ========================================================================
    
    def _find_match(self, raw_value: str) -> Dict:
        """
        Search owl_names for exact case-insensitive match.
        
        Returns:
            {'found': False} or
            {'found': True, 'owl_id': int, 'canonical_name': str, 'matched_display_name': str}
        """
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Exact match (case-insensitive) in owl_names
        cur.execute("""
            SELECT n.owl_id, n.display_name, o.canonical_name
            FROM owl_names n
            JOIN owl o ON n.owl_id = o.owl_id
            WHERE LOWER(n.display_name) = LOWER(%s)
            LIMIT 1
        """, (raw_value,))
        
        row = cur.fetchone()
        
        if row:
            return {
                'found': True,
                'owl_id': row['owl_id'],
                'canonical_name': row['canonical_name'],
                'matched_display_name': row['display_name'],
            }
        
        return {'found': False}
    
    def _name_already_exists(self, owl_id: int, display_name: str) -> bool:
        """Check if this exact owl_id + display_name combination exists."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 1 FROM owl_names
            WHERE owl_id = %s AND LOWER(display_name) = LOWER(%s)
        """, (owl_id, display_name))
        return cur.fetchone() is not None
    
    # ========================================================================
    # SAVE
    # ========================================================================
    
    def _create_owl_name(self, owl_id: int, display_name: str, name_type: str, provenance: Dict):
        """Insert new owl_names row."""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO owl_names (owl_id, display_name, name_type, provenance, created_by)
            VALUES (%s, %s, %s, %s, 'owl_names__row_C')
            ON CONFLICT (owl_id, language, display_name) DO UPDATE
            SET observation_count = owl_names.observation_count + 1
        """, (owl_id, display_name, name_type, json.dumps(provenance)))
        self.conn.commit()
    
    def _update_pending_status(self, pending_id: int, owl_id: int, match_type: str):
        """Mark owl_pending as merged (Lucy found exact match)."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE owl_pending
            SET status = 'merged',
                resolved_owl_id = %s,
                processed_at = NOW(),
                processed_by = 'owl_names__row_C',
                resolution_notes = %s
            WHERE pending_id = %s
        """, (owl_id, f'Matched via {match_type}', pending_id))
        self.conn.commit()

    def _update_pending_for_alma(self, pending_id: int):
        """Mark owl_pending as lucy_passed (no exact match, hand to Alma)."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE owl_pending
            SET status = 'lucy_passed',
                processed_at = NOW(),
                processed_by = 'owl_names__row_C',
                resolution_notes = 'No exact match - needs fuzzy matching'
            WHERE pending_id = %s
        """, (pending_id,))
        self.conn.commit()


# ============================================================================
# CLI ENTRY POINT
# ============================================================================
def main():
    """CLI entry point for standalone testing and harness execution."""
    
    # Check if input is coming via stdin (harness mode)
    if not sys.stdin.isatty():
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            try:
                input_data = json.loads(sys.stdin.read())
                with get_connection() as conn:
                    actor = OwlNamesRowC(db_conn=conn)
                    actor.input_data = input_data
                    result = actor.process()
                    print(json.dumps(result, default=str))
                    return
            except json.JSONDecodeError:
                pass  # Fall through to argv handling
    
    # CLI mode
    if len(sys.argv) < 2:
        print("Usage: python3 owl_names__row_C.py <pending_id>")
        print("       python3 owl_names__row_C.py --sample 5")
        sys.exit(1)
    
    with get_connection() as conn:
        actor = OwlNamesRowC(db_conn=conn)
        
        if sys.argv[1] == '--sample':
            # Get random pending items that have matches
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT pending_id FROM owl_pending op
                WHERE status = 'pending'
                  AND EXISTS (SELECT 1 FROM owl_names n WHERE LOWER(n.display_name) = LOWER(op.raw_value))
                ORDER BY RANDOM()
                LIMIT %s
            """, (count,))
            pending_ids = [row['pending_id'] for row in cur.fetchall()]
            
            for pid in pending_ids:
                actor.input_data = {'pending_id': pid}
                result = actor.process()
                print(f"\n--- pending_id={pid} ---")
                print(json.dumps(result, indent=2, default=str))
        else:
            pending_id = int(sys.argv[1])
            actor.input_data = {'pending_id': pending_id}
            result = actor.process()
            print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
