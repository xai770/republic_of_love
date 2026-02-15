"""
BaseActor — Foundation class for all actors in the turing pipeline.

Provides:
    - Connection lifecycle management (try/finally cleanup)
    - Consistent subject_id extraction
    - Progress logging helpers
    - Transaction discipline (commit/rollback helpers)
    - Signal handling for graceful shutdown
    - Standard CLI scaffolding

Two subclasses for the two actor flavors:
    - ProcessingActor: daemon-driven, per-subject (preflight → process → QA)
    - SourceActor: cron-driven, batch fetchers that create subjects

Usage:
    class MyActor(ProcessingActor):
        def _preflight(self, subject_id):
            ...
        def _do_work(self, data, feedback=None):
            ...
        def _save_result(self, subject_id, result):
            ...

    # Daemon instantiation:
    actor = MyActor(db_conn=conn_from_daemon)
    actor.input_data = {"subject_id": 123, ...}
    result = actor.process()

    # Standalone:
    actor = MyActor()  # creates own connection
    ...
    actor.cleanup()    # returns connection to pool

Author: Copilot
Date: 2026-02-15
"""

import json
import os
import signal
import time
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
import requests

from core.database import get_connection_raw, return_connection
from core.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# SHARED CONSTANTS
# ============================================================================

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'

# Bad data patterns — if LLM says this, input was insufficient (skip, don't fail)
BAD_DATA_PATTERNS = [
    'not specified in the given text',
    'not specified in the text',
    'not mentioned in the text',
    'not provided in the text',
    'information not available',
    'cannot be determined from',
]

# Default retry settings
DEFAULT_MAX_RETRIES = 1
DEFAULT_MAX_INPUT_LENGTH = 8000


# ============================================================================
# BASE ACTOR
# ============================================================================

class BaseActor:
    """
    Foundation for all actors.
    
    Handles DB connection lifecycle, subject ID normalization,
    progress logging, and transaction helpers.
    
    CRITICAL: Always use cleanup() or a try/finally block to
    ensure the DB connection is returned to the pool.
    """
    
    # Subclass should set these
    ACTOR_ID: Optional[str] = None
    TASK_TYPE_ID: Optional[int] = None
    
    def __init__(self, db_conn=None):
        """
        Initialize with optional database connection.
        
        Args:
            db_conn: Connection from daemon/pool. If None, creates own.
        """
        self.conn = db_conn or get_connection_raw()
        self._owns_conn = db_conn is None
        self.input_data: Dict[str, Any] = {}
        self._llm_calls: List[Dict] = []
        self._progress_last_log = time.time()
        
        # Install signal handlers for graceful cleanup (standalone mode only)
        if self._owns_conn:
            self._original_sigterm = signal.getsignal(signal.SIGTERM)
            self._original_sigint = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
    
    # ========================================================================
    # CONNECTION LIFECYCLE
    # ========================================================================
    
    def cleanup(self):
        """
        Return connection to pool if we own it.
        
        MUST be called in a finally block. Never rely on __del__.
        """
        if self._owns_conn and self.conn and not self.conn.closed:
            try:
                self.conn.rollback()  # Release any open transaction
            except Exception:
                pass
            return_connection(self.conn)
            self.conn = None
        
        # Restore original signal handlers
        if self._owns_conn:
            try:
                signal.signal(signal.SIGTERM, self._original_sigterm)
                signal.signal(signal.SIGINT, self._original_sigint)
            except (ValueError, OSError):
                pass  # Not in main thread
    
    def _signal_handler(self, signum, frame):
        """Handle SIGTERM/SIGINT: clean up connection before exit."""
        sig_name = signal.Signals(signum).name
        logger.warning("Received %s — cleaning up connection", sig_name)
        self.cleanup()
        raise SystemExit(128 + signum)
    
    # ========================================================================
    # SUBJECT ID
    # ========================================================================
    
    @property
    def subject_id(self) -> Optional[int]:
        """
        Extract subject_id from input_data, checking common key names.
        
        Daemon sets input_data with 'subject_id' from work_query.
        Some actors use 'posting_id' or 'pending_id' directly.
        """
        for key in ('subject_id', 'posting_id', 'pending_id', 'interaction_id'):
            val = self.input_data.get(key)
            if val is not None:
                return int(val)
        return None
    
    # ========================================================================
    # DB HELPERS
    # ========================================================================
    
    def cursor(self, dict_cursor: bool = True):
        """Get a cursor. Dict cursor by default."""
        if dict_cursor:
            return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return self.conn.cursor()
    
    def commit(self):
        """Commit current transaction."""
        self.conn.commit()
    
    def rollback(self):
        """Rollback current transaction."""
        self.conn.rollback()
    
    # ========================================================================
    # PROGRESS LOGGING
    # ========================================================================
    
    def log_progress(self, current: int, total: int, extra: str = "",
                     interval: float = 5.0):
        """
        Log progress at most every `interval` seconds.
        
        Args:
            current: Current item number (1-based)
            total: Total items
            extra: Additional info string
            interval: Minimum seconds between progress logs
        """
        now = time.time()
        # Always log the last item
        if now - self._progress_last_log >= interval or current == total:
            pct = (current / total * 100) if total > 0 else 0
            msg = f"[{current}/{total}] {pct:.0f}%"
            if extra:
                msg += f" — {extra}"
            logger.info(msg)
            self._progress_last_log = now
    
    # ========================================================================
    # LLM HELPERS
    # ========================================================================
    
    def call_llm(self, prompt: str, model: str = None,
                 temperature: float = 0, seed: int = 42,
                 timeout: int = 60) -> Optional[str]:
        """
        Call Ollama LLM and track the call for auditability.
        
        Args:
            prompt: The prompt text
            model: Model name (default: read from task_types or qwen2.5:7b)
            temperature: Temperature (default: 0 for repeatability)
            seed: Random seed (default: 42)
            timeout: Request timeout in seconds
            
        Returns:
            Response text or None on failure
        """
        model = model or self._get_model()
        start = time.time()
        
        call_record = {
            'model': model,
            'prompt_length': len(prompt),
            'temperature': temperature,
            'seed': seed,
        }
        
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': temperature,
                        'seed': seed,
                    }
                },
                timeout=timeout
            )
            resp.raise_for_status()
            
            result = resp.json().get('response', '')
            call_record['response_length'] = len(result)
            call_record['duration_ms'] = int((time.time() - start) * 1000)
            call_record['success'] = True
            self._llm_calls.append(call_record)
            return result
            
        except Exception as e:
            call_record['error'] = str(e)
            call_record['duration_ms'] = int((time.time() - start) * 1000)
            call_record['success'] = False
            self._llm_calls.append(call_record)
            logger.error("LLM call failed: %s", e)
            return None
    
    def _get_model(self) -> str:
        """Get model name from task_types or default."""
        if self.TASK_TYPE_ID:
            try:
                cur = self.cursor()
                cur.execute("""
                    SELECT llm_settings->>'model' AS model
                    FROM task_types WHERE task_type_id = %s
                """, (self.TASK_TYPE_ID,))
                row = cur.fetchone()
                if row and row.get('model'):
                    return row['model']
            except Exception:
                pass
        return "qwen2.5:7b"
    
    def parse_json_response(self, text: str) -> Optional[Dict]:
        """
        Extract JSON from LLM response text.
        
        Handles common patterns: ```json blocks, leading/trailing text, etc.
        """
        if not text:
            return None
        
        # Try direct parse first
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try extracting from ```json ... ``` blocks
        import re
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Try finding first { ... } or [ ... ]
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
        
        return None
    
    def is_bad_data_response(self, text: str) -> bool:
        """Check if LLM response indicates insufficient input data."""
        if not text:
            return True
        text_lower = text.lower()
        return any(p in text_lower for p in BAD_DATA_PATTERNS)


# ============================================================================
# PROCESSING ACTOR — daemon-driven, per-subject
# ============================================================================

class ProcessingActor(BaseActor):
    """
    Actor that processes one subject at a time via turing_daemon.
    
    Three-phase structure (Belt & Suspenders):
    1. PREFLIGHT: Validate input, skip bad data
    2. PROCESS: Do the work
    3. QA: Validate output, retry or flag
    
    Subclasses MUST implement:
        _preflight(subject_id) -> {'ok': bool, 'data': ..., 'reason': ...}
        _do_work(data, feedback=None) -> {'success': bool, ...}
        _save_result(subject_id, result) -> None
    
    Optionally override:
        _qa_check(data, result) -> {'passed': bool, 'reason': ...}
        MAX_RETRIES: int (default: 1)
    """
    
    MAX_RETRIES = DEFAULT_MAX_RETRIES
    MAX_INPUT_LENGTH = DEFAULT_MAX_INPUT_LENGTH
    
    def process(self) -> Dict[str, Any]:
        """
        Main entry point. Called by turing_daemon.
        
        Runs preflight → work → QA with retry loop.
        """
        sid = self.subject_id
        
        if not sid:
            return {'success': False, 'error': 'No subject_id in input_data'}
        
        try:
            # Phase 1: PREFLIGHT
            preflight = self._preflight(sid)
            if not preflight.get('ok'):
                return {
                    'success': False,
                    'skip_reason': preflight.get('reason', 'PREFLIGHT_FAILED'),
                    'error': preflight.get('message', preflight.get('reason', 'Preflight failed')),
                    'subject_id': sid,
                }
            
            data = preflight.get('data')
            
            # Phase 2: PROCESS (with retry on QA failure)
            result = None
            qa_feedback = None
            
            for attempt in range(1, self.MAX_RETRIES + 2):
                result = self._do_work(data, feedback=qa_feedback)
                
                if not result or not result.get('success'):
                    return {
                        'success': False,
                        'error': (result or {}).get('error', 'Processing failed'),
                        'subject_id': sid,
                        'llm_calls': self._llm_calls,
                    }
                
                # Phase 3: QA
                qa = self._qa_check(data, result)
                if qa.get('passed', True):
                    break
                
                qa_feedback = qa.get('feedback')
                if attempt > self.MAX_RETRIES:
                    return {
                        'success': False,
                        'error': f"QA failed after {attempt} attempts: {qa.get('reason')}",
                        'subject_id': sid,
                        'qa_issues': qa.get('issues', []),
                        'llm_calls': self._llm_calls,
                    }
            
            # SAVE
            self._save_result(sid, result)
            
            return {
                'success': True,
                '_consistency': '1/1',
                'subject_id': sid,
                'llm_calls': self._llm_calls,
                **(result or {}),
            }
            
        except Exception as e:
            self.rollback()
            return {
                'success': False,
                'error': str(e),
                'subject_id': sid,
                'llm_calls': self._llm_calls,
            }
    
    # ---- Subclass hooks ----
    
    def _preflight(self, subject_id: int) -> Dict:
        """
        Validate input. Return {'ok': True, 'data': ...} or {'ok': False, 'reason': ...}.
        """
        raise NotImplementedError("Subclass must implement _preflight()")
    
    def _do_work(self, data: Any, feedback: Optional[str] = None) -> Dict:
        """
        Do the actual work. Return {'success': True, ...}.
        """
        raise NotImplementedError("Subclass must implement _do_work()")
    
    def _qa_check(self, data: Any, result: Dict) -> Dict:
        """
        Validate output. Return {'passed': True} or {'passed': False, 'reason': ..., 'feedback': ...}.
        Default: pass-through (no QA).
        """
        return {'passed': True}
    
    def _save_result(self, subject_id: int, result: Dict) -> None:
        """
        Save processing result to database.
        """
        raise NotImplementedError("Subclass must implement _save_result()")
    
    # ---- QA Report ----
    
    def qa_report(self, sample_size: int = 20) -> Dict:
        """
        Run QA on a sample of recent outputs.
        
        Override _qa_validate_sample() for custom validation.
        """
        return self._qa_validate_sample(sample_size)
    
    def _qa_validate_sample(self, sample_size: int) -> Dict:
        """Override this for custom QA validation."""
        return {'sample_size': sample_size, 'message': 'No QA validation implemented'}


# ============================================================================
# SOURCE ACTOR — cron-driven batch fetchers
# ============================================================================

class SourceActor(BaseActor):
    """
    Actor that creates/upserts subjects in batch (e.g., AA fetcher, DB fetcher).
    
    These run via cron/shell script, not the daemon.
    They create postings rather than processing them.
    
    Subclasses implement:
        fetch() -> Dict with stats
    """
    
    def fetch(self) -> Dict:
        """Main entry point for source actors."""
        raise NotImplementedError("Subclass must implement fetch()")
    
    def batch_upsert(self, table: str, conflict_column: str,
                     conflict_where: str, rows: List[Dict],
                     update_columns: List[str],
                     batch_size: int = 500) -> Dict:
        """
        Generic batch upsert using ON CONFLICT.
        
        Args:
            table: Target table name
            conflict_column: Column for ON CONFLICT
            conflict_where: WHERE clause for partial index
            rows: List of dicts with column: value pairs
            update_columns: Columns to update on conflict
            batch_size: Commit every N rows
            
        Returns:
            Stats dict with 'new' and 'existing' counts
        """
        if not rows:
            return {'new': 0, 'existing': 0}
        
        stats = {'new': 0, 'existing': 0, 'errors': 0}
        columns = list(rows[0].keys())
        
        cur = self.cursor(dict_cursor=False)
        
        for batch_start in range(0, len(rows), batch_size):
            batch = rows[batch_start:batch_start + batch_size]
            values = [tuple(row[c] for c in columns) for row in batch]
            
            placeholders = ', '.join(['%s'] * len(columns))
            update_set = ', '.join(
                f"{c} = EXCLUDED.{c}" for c in update_columns
            )
            
            try:
                results = psycopg2.extras.execute_values(
                    cur,
                    f"""
                    INSERT INTO {table} ({', '.join(columns)})
                    VALUES %s
                    ON CONFLICT ({conflict_column})
                        WHERE {conflict_where}
                    DO UPDATE SET {update_set}
                    RETURNING (xmax = 0) AS was_inserted
                    """,
                    values,
                    fetch=True,
                )
                
                batch_new = sum(1 for r in results if r[0])
                stats['new'] += batch_new
                stats['existing'] += len(results) - batch_new
                self.commit()
                
                self.log_progress(
                    min(batch_start + batch_size, len(rows)), len(rows),
                    f"+{batch_new} new"
                )
                
            except Exception as e:
                self.rollback()
                stats['errors'] += len(batch)
                logger.error("Batch upsert error at %d-%d: %s",
                             batch_start, batch_start + len(batch), e)
        
        return stats


# ============================================================================
# CLI HELPERS
# ============================================================================

def run_actor_cli(actor_class, description: str = "Actor CLI"):
    """
    Standard CLI entry point for any actor.
    
    Provides:
        python3 actor.py <subject_id>          — process one subject
        python3 actor.py --qa                    — run QA report
        python3 actor.py --qa --sample 50        — QA on 50 items
    
    Handles connection cleanup automatically via try/finally.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('subject_id', nargs='?', type=int,
                        help='Subject ID to process')
    parser.add_argument('--qa', action='store_true',
                        help='Run QA report instead of processing')
    parser.add_argument('--sample', type=int, default=20,
                        help='QA sample size (default: 20)')
    
    args = parser.parse_args()
    
    actor = actor_class()
    try:
        if args.qa:
            report = actor.qa_report(args.sample)
            print(json.dumps(report, indent=2, default=str))
        elif args.subject_id:
            actor.input_data = {'subject_id': args.subject_id}
            result = actor.process()
            print(json.dumps(result, indent=2, default=str))
        else:
            parser.print_help()
    finally:
        actor.cleanup()
