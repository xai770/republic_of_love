#!/usr/bin/env python3
"""
owl_pending__atomize_U - Atomize compound skill phrases into atomic skills

PURPOSE:
Take compound phrases in owl_pending (e.g., "German skills, experience with 
Finance, PC Tools Deluxe Power user") and split them into atomic skills 
that can be matched against owl_names.

PREREQUISITE: owl_pending items with status='pending'

Input:  owl_pending (pending_id, raw_value) where status='pending'
Output: owl_pending.atomized_skills (JSON array of atomic skills)
        + owl_pending.status → 'atomized'

Flow Diagram:
```mermaid
flowchart TD
    A[📋 owl_pending item] --> B{Length ≤ 25 chars?}
    B -->|Yes - already atomic| C[Keep as-is]
    B -->|No - compound| D[🤖 LLM Atomize]
    D --> E{Valid atomics?}
    E -->|No| Z1[⏭️ SKIP: no_atomics]
    E -->|Yes| F[Save atomized_skills]
    C --> G[status='atomized']
    F --> G
    G --> H[✅ SUCCESS]
```

PIPELINE POSITION:
```
owl_pending (compound) → [THIS ACTOR] → owl_pending.atomized_skills
                                            ↓
                         owl_names__row_C (match each atomic)
```

LINEAGE:
- Each atomized skill carries source_hash = md5(raw_value)
- Enables verification: "did the source change since atomization?"

RAQ Config:
- state_tables: owl_pending.atomized_skills
- compare_output_field: output->>'atomized_skills'

Usage:
    # Via turing-harness:
    ./tools/turing/turing-harness run owl_pending__atomize_U --input '{"pending_id": 123}'
    
    # Standalone:
    python3 actors/owl_pending__atomize_U.py 123
    python3 actors/owl_pending__atomize_U.py --qa

Author: Arden
Date: 2026-01-19
Task Type ID: TBD (will create)
"""

import json
import re
import hashlib
import time
from typing import Dict, Any, Optional, List

import psycopg2
import psycopg2.extras
import requests

# ============================================================================
# SETUP
# ============================================================================

import os
from core.database import get_connection
from core.text_utils import clean_json_from_llm

from core.logging_config import get_logger
logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
TASK_TYPE_ID = 1306  # owl_pending_auto_triage

from config.settings import OLLAMA_GENERATE_URL as OLLAMA_URL
MODEL = "qwen2.5-coder:7b"

# Threshold for "already atomic" - skip LLM for short items
ATOMIC_LENGTH_THRESHOLD = 25

# Known atomic patterns that don't need LLM
ATOMIC_PATTERNS = [
    r'^[A-Za-z0-9#\+\.]+$',  # Single word like "Python", "C++", "C#", ".NET"
    r'^[A-Za-z0-9]+ [A-Za-z0-9]+$',  # Two words like "Machine Learning"
]

# Atomization prompt
ATOMIZE_PROMPT = '''Extract atomic skills from this compound phrase. Output ONLY a JSON array of lowercase skill names.

RULES:
1. Split compound skills: "Python/Django" → ["python", "django"]
2. Remove qualifiers: "5+ years Java experience" → ["java"]
3. Remove soft skill fluff: "Excellent communication" → [] (unless specific like "technical writing")
4. Keep compound terms together: "machine learning" (not ["machine", "learning"])
5. Normalize: lowercase, no special chars except underscore
6. One word per skill when possible, two words max for compound terms
7. If nothing extractable, return ["NONE"]

EXAMPLES:
- "German skills, Finance experience, PC Tools" → ["german", "finance", "pc_tools"]
- "Advanced knowledge of MS Excel and PowerPoint" → ["excel", "powerpoint"]
- "Strong communication and teamwork" → ["NONE"]
- "Python/Django/Flask development" → ["python", "django", "flask"]
- "Experience with AWS, GCP or Azure" → ["aws", "gcp", "azure"]

INPUT:
{raw_value}

OUTPUT (JSON array only):'''


# ============================================================================
# ACTOR CLASS
# ============================================================================
class OwlPendingAtomizeU:
    """
    Atomize compound skill phrases into atomic skills.
    
    Short items (≤25 chars) are assumed atomic and passed through.
    Longer items go through LLM atomization.
    
    Includes lineage tracking via source_hash.
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
        self._llm_calls: List[Dict] = []
    
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    def process(self) -> Dict[str, Any]:
        """Main entry point. Called by pull_daemon or harness."""
        pending_id = self.input_data.get('pending_id') or self.input_data.get('subject_id')
        
        if not pending_id:
            return {'success': False, 'error': 'No pending_id in input'}
        
        try:
            # Fetch the pending item
            item = self._fetch_pending(pending_id)
            if not item:
                return {'success': False, 'error': f'Pending item {pending_id} not found'}
            
            raw_value = item['raw_value']
            
            # Compute lineage hash
            source_hash = hashlib.md5(raw_value.encode()).hexdigest()[:16]
            
            # Check if already atomic (short or matches pattern)
            if self._is_atomic(raw_value):
                atomics = [self._normalize_skill(raw_value)]
                method = 'passthrough'
            else:
                # LLM atomization
                atomics = self._atomize_llm(raw_value)
                method = 'llm'
                
                if not atomics or atomics == ['NONE']:
                    # Nothing extractable - mark as skipped
                    self._update_pending(pending_id, status='skipped', 
                                        atomized_skills=None, 
                                        resolution_notes='no_extractable_skills')
                    return {
                        'success': True,
                        'pending_id': pending_id,
                        'skip_reason': 'no_extractable_skills',
                        'raw_value': raw_value,
                        'llm_calls': self._llm_calls,
                    }
            
            # Filter out NONE and empty strings
            atomics = [a for a in atomics if a and a != 'NONE']
            
            if not atomics:
                self._update_pending(pending_id, status='skipped',
                                    atomized_skills=None,
                                    resolution_notes='no_valid_atomics')
                return {
                    'success': True,
                    'pending_id': pending_id,
                    'skip_reason': 'no_valid_atomics',
                    'raw_value': raw_value,
                    'llm_calls': self._llm_calls,
                }
            
            # Build atomized_skills with lineage
            atomized_skills = {
                'atomics': atomics,
                'source_hash': source_hash,
                'method': method,
            }
            
            # Save
            self._update_pending(pending_id, status='atomized',
                                atomized_skills=atomized_skills)
            
            return {
                'success': True,
                'pending_id': pending_id,
                'raw_value': raw_value,
                'atomics': atomics,
                'count': len(atomics),
                'method': method,
                'source_hash': source_hash,
                'llm_calls': self._llm_calls,
            }
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'pending_id': pending_id,
                'llm_calls': self._llm_calls,
            }
    
    def _is_atomic(self, value: str) -> bool:
        """Check if value is already atomic (no need for LLM)."""
        if len(value) <= ATOMIC_LENGTH_THRESHOLD:
            # Short enough, check patterns
            for pattern in ATOMIC_PATTERNS:
                if re.match(pattern, value):
                    return True
            # Even if no pattern match, short items with no commas/slashes are atomic
            if not any(sep in value for sep in [',', '/', ';', ' and ', ' or ']):
                return True
        return False
    
    def _normalize_skill(self, value: str) -> str:
        """Normalize a skill name to standard form."""
        result = value.strip()
        
        # Special cases for programming languages
        special_cases = {
            'c++': 'cpp',
            'c#': 'csharp',
            '.net': 'dotnet',
            'f#': 'fsharp',
            'objective-c': 'objective_c',
            'node.js': 'nodejs',
            'vue.js': 'vuejs',
            'react.js': 'reactjs',
            'next.js': 'nextjs',
            'express.js': 'expressjs',
        }
        
        lower = result.lower()
        if lower in special_cases:
            return special_cases[lower]
        
        # Lowercase
        result = lower
        # Replace special chars with underscore
        result = re.sub(r'[^a-z0-9]+', '_', result)
        # Remove leading/trailing underscores
        result = result.strip('_')
        return result
    
    def _atomize_llm(self, raw_value: str) -> List[str]:
        """Use LLM to atomize compound phrase."""
        prompt = ATOMIZE_PROMPT.replace('{raw_value}', raw_value)
        
        response = self._call_llm(prompt)
        if not response:
            return []
        
        # Parse JSON array from response
        cleaned = clean_json_from_llm(response)
        
        # Find array
        match = re.search(r'\[.*?\]', cleaned, re.DOTALL)
        if not match:
            return []
        
        try:
            atomics = json.loads(match.group())
            # Normalize each atomic
            return [self._normalize_skill(a) for a in atomics if isinstance(a, str)]
        except json.JSONDecodeError:
            return []
    
    def _fetch_pending(self, pending_id: int) -> Optional[Dict]:
        """Fetch owl_pending item."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT pending_id, owl_type, raw_value, status
            FROM owl_pending
            WHERE pending_id = %s
        """, (pending_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    
    def _update_pending(self, pending_id: int, status: str, 
                       atomized_skills: Optional[Dict] = None,
                       resolution_notes: str = None):
        """Update owl_pending with atomization results."""
        cur = self.conn.cursor()
        
        # We need to add atomized_skills column if it doesn't exist
        # For now, store in resolution_notes as JSON
        notes = json.dumps({
            'atomized_skills': atomized_skills,
            'notes': resolution_notes,
        }) if atomized_skills or resolution_notes else None
        
        cur.execute("""
            UPDATE owl_pending
            SET status = %s,
                resolution_notes = %s,
                processed_at = NOW()
            WHERE pending_id = %s
        """, (status, notes, pending_id))
        self.conn.commit()
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call Ollama LLM."""
        start_time = time.time()
        
        try:
            response = requests.post(OLLAMA_URL, json={
                'model': MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0,
                    'seed': 42,
                    'num_predict': 512,
                }
            }, timeout=60)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            result = response.json().get('response', '')
            
            self._llm_calls.append({
                'purpose': 'atomize',
                'model': MODEL,
                'prompt_chars': len(prompt),
                'response_chars': len(result),
                'elapsed_ms': elapsed_ms,
            })
            
            return result.strip()
            
        except Exception as e:
            self._llm_calls.append({
                'purpose': 'atomize',
                'error': str(e),
            })
            return None
    
    # ========================================================================
    # QA REPORT
    # ========================================================================
    
    def qa_report(self, sample_size: int = 50) -> Dict:
        """Generate QA report for atomization."""
        from datetime import datetime
        
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get atomized items
        cur.execute("""
            SELECT pending_id, raw_value, resolution_notes, status
            FROM owl_pending
            WHERE status IN ('atomized', 'skipped')
            ORDER BY processed_at DESC
            LIMIT %s
        """, (sample_size,))
        
        samples = cur.fetchall()
        
        if not samples:
            return {'status': 'no_data', 'message': 'No atomized items found'}
        
        results = []
        for sample in samples:
            notes = json.loads(sample['resolution_notes']) if sample['resolution_notes'] else {}
            atomized = notes.get('atomized_skills', {})
            atomics = atomized.get('atomics', []) if atomized else []
            
            results.append({
                'pending_id': sample['pending_id'],
                'raw_value': sample['raw_value'],
                'status': sample['status'],
                'atomics': atomics,
                'count': len(atomics),
                'method': atomized.get('method') if atomized else None,
            })
        
        atomized = [r for r in results if r['status'] == 'atomized']
        skipped = [r for r in results if r['status'] == 'skipped']
        
        return {
            'status': 'ok',
            'generated_at': datetime.now().isoformat(),
            'sample_size': len(samples),
            'atomized_count': len(atomized),
            'skipped_count': len(skipped),
            'avg_atomics_per_item': sum(r['count'] for r in atomized) / len(atomized) if atomized else 0,
            'samples': results[:20],  # First 20 for display
        }
    
    def print_qa_report(self, sample_size: int = 50):
        """Print QA report in markdown format."""
        report = self.qa_report(sample_size)
        
        if report['status'] == 'no_data':
            logger.error("%s", report['message'])
            return
        
        logger.info("# QA Report: Skill Atomizer")
        logger.info("Generated: %s", report['generated_at'])
        logger.info("## Summary")
        logger.info("| Metric | Value |")
        logger.info("|--------|-------|")
        logger.info("| Sample size |%s|", report['sample_size'])
        logger.info("| Atomized |%s|", report['atomized_count'])
        logger.info("| Skipped |%s|", report['skipped_count'])
        logger.info("| Avg atomics per item |%.1f|", report['avg_atomics_per_item'])
        logger.info("## Samples")
        for r in report['samples'][:10]:
            logger.info("\n**%s %s**", r['raw_value'][:60], '...' if len(r['raw_value']) > 60 else '')
            logger.info("Status: %s", r['status'])
            if r['atomics']:
                logger.info("Atomics: %s", r['atomics'])


# ============================================================================
# MAIN
# ============================================================================
def main():
    """
    Test the atomizer directly.
    
    Usage:
        python3 actors/owl_pending__atomize_U.py              # random pending
        python3 actors/owl_pending__atomize_U.py 12345        # specific pending_id
        python3 actors/owl_pending__atomize_U.py --qa         # QA report
        python3 actors/owl_pending__atomize_U.py --test       # test on samples without saving
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Skill atomizer')
    parser.add_argument('pending_id', nargs='?', type=int, help='Pending ID to process')
    parser.add_argument('--qa', action='store_true', help='Run QA report')
    parser.add_argument('--test', action='store_true', help='Test mode - show results without saving')
    parser.add_argument('--sample', type=int, default=50, help='Sample size for QA')
    args = parser.parse_args()
    
    with get_connection() as conn:
        actor = OwlPendingAtomizeU(conn)
        
        if args.qa:
            actor.print_qa_report(args.sample)
            return
        
        if args.test:
            # Test mode - run on samples but don't save
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT pending_id, raw_value, LENGTH(raw_value) as len
                FROM owl_pending
                WHERE status = 'pending'
                ORDER BY LENGTH(raw_value) DESC
                LIMIT 10
            """)
            samples = cur.fetchall()
            
            logger.info("# Atomization Test (dry run)\n")
            for sample in samples:
                logger.info("##%s %s", sample['raw_value'][:70], '...' if len(sample['raw_value']) > 70 else '')
                logger.info("Length: %s chars", sample['len'])
                
                # Check if atomic
                if actor._is_atomic(sample['raw_value']):
                    logger.info("→ **Passthrough** (already atomic)")
                    logger.info("→ Normalized: `%s`", actor._normalize_skill(sample['raw_value']))
                else:
                    atomics = actor._atomize_llm(sample['raw_value'])
                    logger.info("→ **LLM atomized**: %s", atomics)
            return
        
        # Process mode
        pending_id = args.pending_id
        
        if not pending_id:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT pending_id FROM owl_pending
                WHERE status = 'pending'
                ORDER BY RANDOM()
                LIMIT 1
            """)
            row = cur.fetchone()
            pending_id = row['pending_id'] if row else None
        
        if pending_id:
            actor.input_data = {'pending_id': pending_id}
            result = actor.process()
            
            logger.info("%s", '='*60)
            logger.info("Result for pending_id %s:", pending_id)
            logger.info("%s", json.dumps(result, indent=2, default=str))
            logger.info("%s", '='*60)
        else:
            logger.info("No pending items found")


if __name__ == '__main__':
    main()
