#!/usr/bin/env python3
"""
[Actor Name] - [One line description]

PURPOSE:
[What this actor does in 2-3 sentences. What triggers it, what it produces.]

PREREQUISITE: [What must run before this, if any]
This actor uses [input_column] from [prerequisite_actor] because:
  - [Reason 1]
  - [Reason 2]

Input:  [table].[column] (via work_query where [condition])
Output: [table].[column(s)]

Output Fields:
    - success: bool - Whether processing completed successfully
    - [field]: [type] - [description]
    - skip_reason: str - Reason for skipping if not processed
    - error: str - Error message if failed

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Subject] --> B{Preflight OK?}
    B -->|Bad data| Z1[⏭️ SKIP: reason]
    B -->|OK| C[🔄 Process]
    C --> D{Success?}
    D -->|No| Z2[❌ FAIL: error]
    D -->|Yes| E[🔍 QA Check]
    E --> F{QA Pass?}
    F -->|No| G{Retry?}
    G -->|Yes| C
    G -->|No| Z3[⚠️ FAIL: QA failed]
    F -->|Yes| H[💾 Save]
    H --> I[✅ SUCCESS]
```

PIPELINE POSITION:
[Where this fits in the posting pipeline. What triggers downstream cascade.]
```
job_description → extracted_summary → embedding → matching
                  [before me]         [THIS ACTOR]  [after me]
```

RAQ Config:
- state_tables: [table].[column]
- compare_output_field: output->>'[field]'

Usage:
    # Via turing-raq (recommended):
    ./tools/turing/turing-raq start [actor_name] --count 20
    
    # Direct test:
    ./tools/turing/turing-harness run [actor_name] --input '{"posting_id": 123}'
    
    # Standalone:
    python3 [this_file].py [subject_id]

Author: [Your name]
Date: [YYYY-MM-DD]
Task Type ID: [ID from task_types table]

---
TOOLS INTEGRATION (from tools/turing/):

These tools expect a specific contract from thick actors:

turing-harness:
    - Tests actors without turing_daemon
    - Expects: class with process() method, __init__(db_conn=None)
    - Example: ./tools/turing/turing-harness run my_actor --input '{"posting_id": 123}'
    - Use --sample N for random samples

turing-raq:
    - RAQ workflow: start → status → reset
    - ./tools/turing/turing-raq start my_actor --count 20 --runs 3
    - Uses task_types.raq_config: {"state_tables": [...], "compare_output_field": "..."}
    - Auto-backs up state before reset

turing-dashboard:
    - Live TUI for monitoring
    - Watchdog mode: ./tools/turing/turing-dashboard -W 30 -r -c 20
    - Features: circuit breaker, auto-restart, cascade detection

turing-hash-scripts:
    - Run after ANY code change: ./tools/turing/turing-hash-scripts --update
    
turing_daemon contract:
    - Finds class with process() method
    - Sets actor.input_data before calling process()
    - Expects output dict with 'success': True/False
    - Optional '_consistency': 'N/N' for RAQ tracking

---
CODING RULES (moved from Turing_project_directives.md - these only matter when writing code):

INFRASTRUCTURE RULES:
#7  - Task-type-agnostic infrastructure
      turing_daemon.py must NOT contain task-type-specific logic.
      The daemon is generic; task types are data.

#8  - Data is the queue
      Don't maintain shadow tables. Find work via work_query SQL.

#9  - Use constants, not string literals
      Import from core/constants.py: Status, Fields, OwlTypes
      A typo in an import fails loudly; a typo in a string literal fails at 3am.

#10 - Optimize then scale
      Run on constrained hardware first. Slowness reveals waste.

THICK ACTOR RULES:
#11 - Thick actors are first-class citizens
      One script does fetch→LLM→save. Valid permanent pattern.
      Execution in tickets, prompts in instructions, logic as Mermaid.

#12 - Thick actor naming: {table}__{attribute}_{CRUD}.py
      __ separates table from attribute
      _C = Create, _U = Update, _D = Delete, _CU = Upsert
      row = whole-row operations
      Examples: postings__extracted_summary_U.py, postings__embedding_U.py

#13 - Belt & Suspenders (three phases)
      Pre-flight: Validate input, skip bad data
      Process: Do the work
      QA: Validate output, retry or flag

LLM RULES:
#14 - LLM Repeatability
      temperature=0, fixed seed from task_types (NEVER hardcode)

#15 - Semantic threshold at 7B
      Tasks requiring semantic reasoning need 7B+ parameter models.
      Test edge cases before selecting.

#16 - Extract, don't classify
      When LLMs oscillate, ask "what's the number?" not "which category?"
      Derive labels in code.

#17 - Consult the model
      When an LLM behaves inconsistently, ask it to explain why.
      Models diagnose their own failures.

#18 - Cross-model QA
      For critical extractions: one model extracts, another grades.
      Self-grading fails.

#19 - LLM deployment process
      Five phases: (1) llm_chat manual tests, (2) model benchmark,
      (3) matrix test, (4) RAQ 100%, (5) production with live QA.

RAQ BEST PRACTICES:
- P90 cutoff: Reject inputs beyond 90th percentile size. Outliers overwhelm models.
- Failure tracking: Actors must increment processing_failures on subject when they fail.
- Edge case marking: When skipping (oversized, malformed), write marker to output column.
- Quote verification: For extractions, verify quotes exist in source. Filters hallucinations.
- Language normalization: Non-English inputs should be translated before extraction.

CORE UTILITIES (core/):
- core/text_utils.py: normalize_for_match, detect_language, verify_quote_in_source, clean_json_from_llm
- core/database.py: get_connection() context manager - NEVER hardcode connection strings
- core/constants.py: Status, Fields, OwlTypes - USE THESE, not string literals

---
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import psycopg2
import psycopg2.extras
import requests

# ============================================================================
# SETUP - Standard boilerplate
# ============================================================================

from core.database import get_connection, get_connection_raw, return_connection
from core.constants import Status, Fields, OwlTypes  # USE THESE, not strings
from core.logging_config import get_logger

logger = get_logger(__name__)

# For text processing (quote verification, language detection):
# from core.text_utils import normalize_for_match, detect_language, verify_quote_in_source, clean_json_from_llm

# ============================================================================
# DATABASE CONNECTION NOTES
# ============================================================================
# get_connection()     - Context manager, use with `with get_connection() as conn:`
# get_connection_raw() - For actors/CLI, returns conn directly. MUST call return_connection(conn) when done!
# return_connection()  - Return connection to pool (don't call conn.close()!)

import os

# ============================================================================
# CONFIGURATION
# ============================================================================
TASK_TYPE_ID = None  # TODO: Set after creating task_type in DB
INSTRUCTION_ID = None  # TODO: Set if using instructions table for prompt

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
MODEL = "qwen2.5-coder:7b"  # Standard model for extraction tasks

# Input limits (P90 cutoff - reject outliers that overwhelm models)
MAX_INPUT_LENGTH = 8000  # Adjust based on your input type

# Retry settings
MAX_RETRIES = 1  # Retry once with stricter prompt if QA fails

# Bad data patterns - if LLM says this, INPUT was insufficient (skip, don't fail)
BAD_DATA_PATTERNS = [
    'not specified in the given text',
    'not specified in the text',
    'not mentioned in the text',
    'not provided in the text',
    'information not available',
    'cannot be determined from',
]

# Your extraction prompt (or load from instructions table)
EXTRACTION_PROMPT = '''Your prompt here.

INPUT:
{input_text}

Return ONLY valid JSON.'''


# ============================================================================
# ACTOR CLASS
# ============================================================================
class YourActorName:
    """
    [Actor description]
    
    Three-Phase Structure (Directive #12 - Belt & Suspenders):
    1. PREFLIGHT: Validate input, skip bad data early
    2. PROCESS: Do the actual work (LLM call, computation)
    3. QA: Validate output, retry or flag issues
    
    Best Practices:
    - Use constants: Status.COMPLETED not 'completed'
    - Use Fields: output[Fields.OWL_ID] not output['owl_id']
    - Return dict with 'success': True/False
    - Include '_consistency': 'N/N' for RAQ tracking
    - Track LLM calls in self._llm_calls for auditability
    - Commit after writes, rollback on errors
    
    Anti-Patterns:
    - DON'T hardcode connection strings (use get_connection())
    - DON'T hardcode temperature/seed (read from task_types)
    - DON'T print() for logging (return in output dict)
    - DON'T catch Exception and continue silently
    - DON'T create queue tables (use work_query)
    """
    
    def __init__(self, db_conn=None):
        """Initialize with database connection."""
        self.conn = db_conn or get_connection_raw()
        self._owns_conn = db_conn is None  # Track if we need to return it
        self.input_data: Dict[str, Any] = {}
        
        # Track LLM calls for auditability (stored in tickets.output.llm_calls)
        self._llm_calls: List[Dict] = []
    
    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================
    
    def process(self) -> Dict[str, Any]:
        """
        Main entry point. Called by turing_daemon.
        
        Returns:
            Dict with at minimum:
            - success: bool
            - _consistency: str (e.g., '1/1', '3/3')
            - Any output fields for ticket.output
            - llm_calls: list (for auditability)
        """
        subject_id = self.input_data.get('subject_id')
        
        if not subject_id:
            return {'success': False, 'error': 'No subject_id in input'}
        
        try:
            # ----------------------------------------------------------------
            # PHASE 1: PREFLIGHT - Is the data any good?
            # ----------------------------------------------------------------
            preflight = self._preflight(subject_id)
            if not preflight['ok']:
                # Skip, don't fail - bad input is not actor's fault
                return {
                    'success': False,
                    'skip_reason': preflight['reason'],
                    'error': preflight.get('message', preflight['reason']),
                    'subject_id': subject_id,
                }
            
            data = preflight['data']
            
            # ----------------------------------------------------------------
            # PHASE 2: PROCESS - Do the work (with retry loop for QA failures)
            # ----------------------------------------------------------------
            result = None
            qa_passed = False
            attempts = 0
            qa_feedback = None
            
            while attempts <= MAX_RETRIES and not qa_passed:
                attempts += 1
                
                # Process (with optional feedback from previous QA failure)
                result = self._do_work(data, feedback=qa_feedback)
                
                if not result.get('success'):
                    # Processing itself failed - don't retry
                    return {
                        'success': False,
                        'error': result.get('error', 'Processing failed'),
                        'subject_id': subject_id,
                        'llm_calls': self._llm_calls,
                    }
                
                # ----------------------------------------------------------------
                # PHASE 3: QA - Is the output any good?
                # ----------------------------------------------------------------
                qa_result = self._qa_check(data, result)
                
                if qa_result['passed']:
                    qa_passed = True
                else:
                    qa_feedback = qa_result.get('feedback')
                    if attempts > MAX_RETRIES:
                        return {
                            'success': False,
                            'error': f"QA failed after {attempts} attempts: {qa_result.get('reason')}",
                            'subject_id': subject_id,
                            'qa_issues': qa_result.get('issues', []),
                            'llm_calls': self._llm_calls,
                        }
            
            # ----------------------------------------------------------------
            # SAVE & RETURN SUCCESS
            # ----------------------------------------------------------------
            self._save_result(subject_id, result)
            
            return {
                'success': True,
                '_consistency': '1/1',  # RAQ: "1 of 1 item processed"
                'subject_id': subject_id,
                'llm_calls': self._llm_calls,
                # Add your output fields here
            }
            
        except Exception as e:
            self.conn.rollback()
            return {
                'success': False,
                'error': str(e),
                'subject_id': subject_id,
                'llm_calls': self._llm_calls,
            }
    
    # ========================================================================
    # PHASE 1: PREFLIGHT
    # ========================================================================
    
    def _preflight(self, subject_id: int) -> Dict:
        """
        Validate input data before processing.
        
        Returns:
            {'ok': True, 'data': {...}} or
            {'ok': False, 'reason': 'SKIP_CODE', 'message': '...'}
            
        Common skip reasons:
            NO_PREREQUISITE - Upstream actor hasn't run yet
            NO_DESCRIPTION - Input text too short/missing
            OVERSIZED - Input beyond P90 cutoff
            ALREADY_PROCESSED - Idempotency check
        """
        # Fetch input data
        data = self._fetch_data(subject_id)
        
        if not data:
            return {'ok': False, 'reason': 'NOT_FOUND', 'message': f'Subject {subject_id} not found'}
        
        # Check for prerequisite (if this actor depends on upstream output)
        # Example: requirements extractor needs extracted_summary
        prerequisite = data.get('extracted_summary')  # or whatever upstream produces
        if not prerequisite:
            return {
                'ok': False,
                'reason': 'NO_PREREQUISITE',
                'message': f'Subject {subject_id} missing prerequisite (run upstream actor first)',
            }
        
        # Check input size (P90 cutoff - directive: reject outliers)
        input_text = data.get('input_column') or prerequisite
        if len(input_text) > MAX_INPUT_LENGTH:
            return {
                'ok': False,
                'reason': 'OVERSIZED',
                'message': f'Input too long ({len(input_text)} chars > {MAX_INPUT_LENGTH})',
            }
        
        if len(input_text.strip()) < 100:
            return {
                'ok': False,
                'reason': 'NO_DESCRIPTION',
                'message': f'Insufficient input text ({len(input_text)} chars)',
            }
        
        return {'ok': True, 'data': data}
    
    def _fetch_data(self, subject_id: int) -> Optional[Dict]:
        """Fetch input data from database."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT *
            FROM your_table
            WHERE id = %s
        """, (subject_id,))
        return cur.fetchone()
    
    # ========================================================================
    # PHASE 2: PROCESS
    # ========================================================================
    
    def _do_work(self, data: Dict, feedback: Optional[str] = None) -> Dict:
        """
        Core processing logic.
        
        Args:
            data: Input data from preflight
            feedback: Optional feedback from previous QA failure (for retry)
            
        Returns:
            {'success': True, 'result': {...}} or
            {'success': False, 'error': '...'}
        """
        # Build prompt
        prompt = self._build_prompt(data, feedback)
        
        # Get LLM settings from task_types (directive #13)
        temp, seed = self._get_llm_settings()
        
        # Call LLM
        response = self._call_llm(prompt, temperature=temp, seed=seed)
        
        if not response:
            return {'success': False, 'error': 'Empty LLM response'}
        
        # Check for bad data patterns (input insufficient)
        response_lower = response.lower()
        for pattern in BAD_DATA_PATTERNS:
            if pattern in response_lower:
                return {'success': False, 'error': f'Input insufficient: {pattern}'}
        
        # Parse response
        try:
            parsed = self._parse_response(response)
            return {'success': True, 'result': parsed, 'raw_response': response}
        except Exception as e:
            return {'success': False, 'error': f'Parse error: {e}'}
    
    def _build_prompt(self, data: Dict, feedback: Optional[str] = None) -> str:
        """Build prompt for LLM. Override for your use case."""
        # Option 1: Get template from instructions table
        template = self._get_instruction_template()
        
        if template:
            prompt = template.replace('{input}', data.get('input_text', ''))
        else:
            # Option 2: Inline prompt
            prompt = f"""Extract information from the following text:

{data.get('input_text', '')}

Return your response as JSON.
"""
        
        # Add feedback from previous QA failure
        if feedback:
            prompt = f"""IMPORTANT: Previous attempt failed QA with this feedback:
{feedback}

Please address these issues in your response.

---

{prompt}"""
        
        return prompt
    
    def _parse_response(self, response: str) -> Dict:
        """Parse LLM response. Override for your output format."""
        # Try JSON first
        try:
            # Handle markdown code blocks
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0]
            else:
                json_str = response
            
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            # Return as plain text
            return {'text': response.strip()}
    
    # ========================================================================
    # PHASE 3: QA
    # ========================================================================
    
    def _qa_check(self, input_data: Dict, result: Dict) -> Dict:
        """
        Validate output quality.
        
        Returns:
            {'passed': True} or
            {'passed': False, 'reason': '...', 'issues': [...], 'feedback': '...'}
            
        Common QA patterns:
        1. Required fields present
        2. Quote verification (extracted quotes exist in source)
        3. Cross-model grading (directive #17)
        """
        output = result.get('result', {})
        
        # Pattern 1: Check for required fields
        required_fields = ['field1', 'field2']
        missing = [f for f in required_fields if not output.get(f)]
        
        if missing:
            return {
                'passed': False,
                'reason': 'MISSING_FIELDS',
                'issues': [f'Missing: {f}' for f in missing],
                'feedback': f'Your response is missing these required fields: {missing}',
            }
        
        # Pattern 2: Quote verification (for extraction tasks)
        # Ensures LLM didn't hallucinate - quotes must exist in source
        # from core.text_utils import verify_quote_in_source
        # source_text = input_data.get('extracted_summary', '')
        # for item in output.get('requirements', []):
        #     quote = item.get('quote', '')
        #     if not verify_quote_in_source(quote, source_text, threshold=0.85):
        #         # Quote not found - either hallucination or source gap
        #         issues.append(f'Quote not in source: {quote[:50]}...')
        
        # Pattern 3: Cross-model grading (directive #17)
        # For critical extractions, have a second model grade the output
        # grader_result = self._call_grader_model(input_data, output)
        # if grader_result['verdict'] == 'fail':
        #     return {'passed': False, 'reason': 'GRADER_FAILED', ...}
        
        return {'passed': True}
    
    # ========================================================================
    # QA REPORT (--qa mode)
    # ========================================================================
    
    def qa_report(self, sample_size: int = 50) -> Dict[str, Any]:
        """
        Generate QA report for this actor's completed work.
        
        Override this method with actor-specific validation logic.
        
        Default implementation provides:
        - Sample of completed tasks
        - Basic statistics (success rate, timing)
        - Override _qa_validate_sample() for custom validation
        
        Usage:
            ./actors/your_actor.py --qa [--sample N]
            
        Returns:
            Dict with report data suitable for markdown output
        """
        import re
        from datetime import datetime
        
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get completed tickets for this actor
        # Schema: tickets has actor_id (FK to actors), not task_type_id
        cur.execute("""
            SELECT t.ticket_id, t.subject_id, t.input, t.output,
                   EXTRACT(EPOCH FROM (t.completed_at - t.started_at)) * 1000 as processing_time_ms,
                   t.created_at
            FROM tickets t
            JOIN actors a ON t.actor_id = a.actor_id
            WHERE a.script_path LIKE %s
              AND t.status = 'completed'
            ORDER BY RANDOM()
            LIMIT %s
        """, (f'%{Path(__file__).name}%', sample_size))
        
        samples = cur.fetchall()
        
        if not samples:
            return {
                'status': 'no_data',
                'message': f'No completed tickets found for actor {self.__class__.__name__}',
            }
        
        # Validate each sample
        results = []
        for sample in samples:
            validation = self._qa_validate_sample(sample)
            results.append({
                'subject_id': sample['subject_id'],
                'ticket_id': sample['ticket_id'],
                'processing_time_ms': float(sample['processing_time_ms']) if sample.get('processing_time_ms') else 0,
                **validation
            })
        
        # Compute statistics
        passed = [r for r in results if r.get('passed', False)]
        failed = [r for r in results if not r.get('passed', False)]
        times = [r['processing_time_ms'] for r in results if r.get('processing_time_ms', 0) > 0]
        
        report = {
            'status': 'ok',
            'generated_at': datetime.now().isoformat(),
            'actor_name': self.__class__.__name__,
            'sample_size': len(samples),
            'passed': len(passed),
            'failed': len(failed),
            'pass_rate': len(passed) / len(samples) if samples else 0,
            'avg_time_ms': sum(times) / len(times) if times else 0,
            'failures': [
                {'subject_id': r['subject_id'], 'reason': r.get('reason', 'unknown')}
                for r in failed[:10]  # Show top 10 failures
            ],
            'samples': results,
        }
        
        return report
    
    def _qa_validate_sample(self, sample: Dict) -> Dict:
        """
        Validate a single completed task sample.
        
        Override this method with actor-specific validation:
        - Grounding checks (does output match source?)
        - Schema validation (required fields present?)
        - Business rules (values in expected ranges?)
        
        Args:
            sample: Dict with ticket_id, subject_id, input, output, etc.
            
        Returns:
            {'passed': True} or {'passed': False, 'reason': '...', 'details': ...}
        """
        # Default: just check output exists and has success=True
        output = sample.get('output', {})
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except (json.JSONDecodeError, ValueError):
                return {'passed': False, 'reason': 'invalid_json_output'}
        
        if not output:
            return {'passed': False, 'reason': 'empty_output'}
        
        if not output.get('success', True):  # Default True for non-standard outputs
            return {'passed': False, 'reason': output.get('error', 'success=False')}
        
        return {'passed': True}
    
    def print_qa_report(self, sample_size: int = 50):
        """Print QA report in markdown format."""
        report = self.qa_report(sample_size)
        
        if report['status'] == 'no_data':
            logger.error("%s", report['message'])
            return
        
        logger.info("# QA Report: %s", self.__class__.__name__)
        logger.info("Generated: %s", report['generated_at'])
        logger.info("Actor: %s", report['actor_name'])
        logger.info("## Summary")
        logger.info("| Metric | Value |")
        logger.info("|--------|-------|")
        logger.info("| Sample size |%s|", report['sample_size'])
        logger.info("| Passed |%s (%.1%) |", report['passed'], report['pass_rate'])
        logger.info("| Failed |%s|", report['failed'])
        logger.info("| Avg processing time |%.0fms |", report['avg_time_ms'])
        
        if report['failures']:
            logger.info("## Failures (top 10)")
            for f in report['failures']:
                logger.info("**%s**: %s", f['subject_id'], f['reason'])
        
        logger.info("*Run with `--qa --sample N` to adjust sample size*")
    
    # ========================================================================
    # SAVE
    # ========================================================================
    
    def _save_result(self, subject_id: int, result: Dict):
        """Save results to database."""
        output = result.get('result', {})
        
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE your_table
            SET output_column = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (json.dumps(output), subject_id))
        self.conn.commit()
    
    # ========================================================================
    # LLM HELPERS
    # ========================================================================
    
    def _get_llm_settings(self) -> Tuple[float, int]:
        """
        Fetch LLM temperature and seed from task_types table.
        
        Directive #13: Never hardcode - read from database.
        """
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT llm_temperature, llm_seed FROM task_types WHERE task_type_id = %s",
            (self.input_data.get('task_type_id', TASK_TYPE_ID),)
        )
        row = cur.fetchone()
        if row:
            return float(row['llm_temperature'] or 0), int(row['llm_seed'] or 42)
        return 0.0, 42
    
    def _get_instruction_template(self) -> Optional[str]:
        """Fetch prompt template from instructions table."""
        if not INSTRUCTION_ID:
            return None
            
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT input_template FROM instructions WHERE instruction_id = %s",
            (INSTRUCTION_ID,)
        )
        row = cur.fetchone()
        return row['input_template'] if row else None
    
    def _call_llm(
        self,
        prompt: str,
        model: str = None,
        temperature: float = 0.0,
        seed: int = 42,
        num_predict: int = 4096,
    ) -> Optional[str]:
        """
        Call Ollama LLM and return response.
        
        Tracks call in self._llm_calls for auditability.
        """
        model = model or MODEL
        
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': temperature,
                        'seed': seed,
                        'num_predict': num_predict,
                    }
                },
                timeout=300
            )
            response.raise_for_status()
            
            result = response.json()
            output = result.get('response', '')
            
            # Track for auditability
            self._llm_calls.append({
                'model': model,
                'prompt_chars': len(prompt),
                'response_chars': len(output),
                'temperature': temperature,
                'seed': seed,
            })
            
            return output.strip()
            
        except Exception as e:
            self._llm_calls.append({
                'model': model,
                'error': str(e),
            })
            return None


# ============================================================================
# STANDALONE TEST
# ============================================================================
def main():
    """
    Test the actor directly (not via turing_daemon).
    
    Usage:
        python3 actors/your_actor.py              # random subject
        python3 actors/your_actor.py 12345        # specific subject_id
        python3 actors/your_actor.py --qa         # QA report (50 samples)
        python3 actors/your_actor.py --qa --sample 100  # QA with custom sample
        
    Or use turing-harness for better control:
        ./tools/turing/turing-harness run your_actor --input '{"posting_id": 12345}'
        ./tools/turing/turing-harness run your_actor --sample 5
    """
    import argparse
    from core.database import get_connection
    
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('subject_id', nargs='?', type=int, help='Subject ID to process')
    parser.add_argument('--qa', action='store_true', help='Run QA report on completed tasks')
    parser.add_argument('--sample', type=int, default=50, help='Sample size for QA report')
    args = parser.parse_args()
    
    conn = get_connection()
    actor = YourActorName(conn)
    
    # QA mode
    if args.qa:
        actor.print_qa_report(args.sample)
        conn.close()
        return
    
    # Process mode
    subject_id = args.subject_id
    
    if not subject_id:
        # Find a test subject (modify query for your table)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id FROM your_table
            WHERE prerequisite_column IS NOT NULL  -- has upstream data
              AND output_column IS NULL            -- not yet processed
            LIMIT 1
        """)
        row = cur.fetchone()
        subject_id = row['id'] if row else None
    
    if subject_id:
        actor.input_data = {
            'subject_id': subject_id,
            'posting_id': subject_id,  # For compatibility
            'task_type_id': TASK_TYPE_ID,
        }
        result = actor.process()
        logger.info("%s", '='*60)
        logger.info("Result for subject %s:", subject_id)
        logger.info("Success: %s", result.get('success'))
        if result.get('error'):
            logger.error("Error: %s", result.get('error'))
        if result.get('skip_reason'):
            logger.info("Skip: %s", result.get('skip_reason'))
        logger.info("%s", json.dumps(result, indent=2, default=str)[:2000])
        logger.info("%s", '='*60)
    else:
        logger.info("No test subjects found")
    
    conn.close()


if __name__ == '__main__':
    main()
