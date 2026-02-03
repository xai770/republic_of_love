#!/usr/bin/env python3
"""
Requirements Extract - Extract Job Requirements as Exact Quotes

PURPOSE:
Extract ONLY the requirements from extracted_summary - skills, experience,
qualifications, certifications. Output as EXACT QUOTES from the summary.
No benefits, DEI language, marketing fluff.

PREREQUISITE: postings__extracted_summary_U.py must run first!
This actor uses extracted_summary (not job_description) for:
  - 81% smaller input = faster LLM calls
  - Bidirectional QA: if quote not in summary, summary missed something

This is the preprocessing step BEFORE posting_facets__row_C.py (CPS).
The output should be a clean list of requirements that can be parsed into CPS.

Input:  postings.posting_id (via work_query where no requirements extracted)
Output: postings.extracted_requirements

Output Fields:
    - success: bool - Whether extraction completed successfully
    - posting_id: int - The posting that was processed
    - source_language: str - Detected language code (en, de, etc.)
    - requirements_count: int - Number of verified requirements extracted
    - rejected_count: int - Number of quotes that failed verification
    - requirements_json: str - JSON array of verified requirements
    - skip_reason: str - Reason for skipping if not processed
    - error: str - Error message if failed

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Posting] --> B{Has extracted_summary?}
    B -->|No| Z1[⏭️ SKIP: NO_SUMMARY]
    B -->|Yes| C[🤖 LLM Extract Requirements]
    C --> D{Valid JSON?}
    D -->|No| Z2[❌ FAIL: JSON parse error]
    D -->|Yes| E[🔍 Quote Verification]
    E --> F{Quote in summary?}
    F -->|Yes| G[✅ Keep]
    F -->|No| H[❌ Reject - summary gap?]
    G --> I[💾 Save verified only]
    H --> I
    I --> J[✅ SUCCESS]
```

NOTE: extracted_summary is ALWAYS in English (guaranteed by postings__extracted_summary_U.py).
No translation logic needed here.

RAQ Config:
- state_tables: postings.extracted_requirements
- compare_output_field: output->>'requirements_json'

Author: Arden  
Date: 2026-01-18
Task Type ID: 9384
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import psycopg2.extras
import requests

# ============================================================================
# SETUP
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection
from core.text_utils import (
    normalize_for_match,
    detect_language, 
    verify_quote_in_source,
    clean_json_from_llm
)

# ============================================================================
# CONFIGURATION
# ============================================================================
TASK_TYPE_ID = 9384  # requirements_extract in task_types
OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = "qwen2.5-coder:7b"  # Same as lily_cps for GPU efficiency
MAX_SUMMARY_LENGTH = 3000  # Summaries avg ~1070 chars; P99 cutoff

# The extraction prompt - focused on EXACT QUOTES only
EXTRACTION_PROMPT = '''You are a requirements extractor. Your job is to find and quote EXACTLY every requirement and key detail from this job posting.

EXTRACT:
- Required skills (programming languages, tools, frameworks)
- Required experience (years, domains, specific achievements)
- Required qualifications (degrees, certifications, licenses)
- Required soft skills (leadership, communication, etc.)
- Required languages (German, English, etc.)
- Key responsibilities (main duties of the role)
- Compensation/salary (if mentioned)
- Benefits (if specific and notable)

DO NOT EXTRACT:
- Company descriptions or marketing language
- DEI statements or equal opportunity language  
- Application instructions
- Vague phrases like "team player" unless specific context

OUTPUT FORMAT:
Return a JSON array where each element is an object with:
- "quote": the EXACT text from the job posting (copy-paste, do not paraphrase)
- "type": one of "skill", "experience", "qualification", "language", "soft_skill", "responsibility", "salary", "benefit"

CRITICAL: Every "quote" MUST be findable in the summary text via string search.
Do not paraphrase. Do not summarize. Copy the exact words.

---
JOB POSTING SUMMARY:
{extracted_summary}
---

Return ONLY a valid JSON array, no markdown formatting.'''

# Translation prompt for non-English postings
TRANSLATION_PROMPT = '''Translate this job posting to English. Preserve all formatting, structure, and meaning exactly.
Do not add or remove any information. This is for requirements extraction, so accuracy is critical.

---
ORIGINAL TEXT:
{text}
---

ENGLISH TRANSLATION:'''


# ============================================================================
# ACTOR CLASS
# ============================================================================
class RequirementsExtractActor:
    """
    Extract job requirements as exact quotes from job postings.
    
    Three-Phase Structure:
    1. PREFLIGHT: Validate posting, detect language, translate if needed
    2. PROCESS: LLM extracts requirements from English text
    3. QA: Strict verification - keep only quotes found in source
    """
    
    def __init__(self, db_conn=None):
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = None  # Will be set when needed
            self._owns_connection = False
        self.input_data = None
        self._llm_calls = []
    
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================
    def process(self) -> dict:
        """Main entry point called by pull_daemon or test harness."""
        posting_id = self.input_data.get('subject_id') or self.input_data.get('posting_id')
        
        if not posting_id:
            return {'error': 'No posting_id in input', 'success': False}
        
        try:
            # === PHASE 1: PREFLIGHT ===
            posting = self._get_posting(posting_id)
            if not posting:
                return {'error': f'Posting {posting_id} not found', 'success': False}
            
            # REQUIRE extracted_summary (postings__extracted_summary_U.py must run first)
            summary = posting.get('extracted_summary', '')
            if not summary or len(summary.strip()) < 100:
                return {
                    'success': False,
                    'skip_reason': 'NO_SUMMARY',
                    'error': f'Posting {posting_id} has no extracted_summary (run postings__extracted_summary_U.py first)',
                    'posting_id': posting_id
                }
            
            # Reject oversized summaries (should be rare)
            if len(summary) > MAX_SUMMARY_LENGTH:
                self._mark_edge_case(posting_id, 'oversized_summary', len(summary))
                return {
                    'success': False,
                    'skip_reason': 'OVERSIZED_SUMMARY',
                    'error': f'Posting {posting_id} summary too long ({len(summary)} chars)',
                    'posting_id': posting_id
                }
            
            # Get language info for reporting (summary is always English)
            source_language = posting.get('source_language') or 'en'
            
            # extracted_summary is ALWAYS in English (guaranteed by summary extractor)
            # No translation logic needed here
            
            # === PHASE 2: PROCESS ===
            prompt = EXTRACTION_PROMPT.replace('{extracted_summary}', summary)
            raw_response = self._call_llm(prompt, 'extract_requirements')
            
            requirements = self._parse_json_array(raw_response)
            if requirements is None:
                self._increment_failures(posting_id)
                return {
                    'success': False,
                    'error': 'Failed to parse JSON from LLM response',
                    'posting_id': posting_id,
                    'llm_calls': self._llm_calls
                }
            
            # === PHASE 3: QA - Strict verification ===
            # Only keep quotes that exist in the summary
            # If quote not found, it may indicate a gap in the summary
            verified_requirements = self._verify_quotes_strict(requirements, summary)
            
            if not verified_requirements:
                self._increment_failures(posting_id)
                return {
                    'success': False,
                    'error': 'No verified requirements extracted',
                    'posting_id': posting_id,
                    'raw_count': len(requirements),
                    'llm_calls': self._llm_calls
                }
            
            # === SAVE ===
            requirements_json = json.dumps(verified_requirements, ensure_ascii=False)
            self._save_requirements(posting_id, requirements_json)
            
            rejected_count = len(requirements) - len(verified_requirements)
            
            return {
                'success': True,
                'posting_id': posting_id,
                'source_language': source_language,
                'requirements_count': len(verified_requirements),
                'requirements_json': requirements_json,
                'rejected_count': rejected_count,
                'llm_calls': self._llm_calls,
            }
            
        except Exception as e:
            import traceback
            self._increment_failures(posting_id)
            return {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'success': False,
                'llm_calls': self._llm_calls
            }
    
    # ========================================================================
    # LANGUAGE DETECTION & TRANSLATION
    # ========================================================================
    
    def _detect_language(self, text: str) -> str:
        """Detect language - delegates to shared utility."""
        return detect_language(text)
    
    def _translate_to_english(self, text: str) -> str:
        """Translate text to English using LLM."""
        prompt = TRANSLATION_PROMPT.replace('{text}', text)
        return self._call_llm(prompt, 'translate_to_english')
    
    # ========================================================================
    # QUOTE VERIFICATION
    # ========================================================================
    
    def _verify_quotes_strict(self, requirements: list, source: str) -> list:
        """
        Strict verification: only keep quotes found in source.
        No fuzzy matching, no retries. Found = keep, not found = reject.
        """
        verified = []
        
        for req in requirements:
            if not isinstance(req, dict) or 'quote' not in req:
                continue
            
            quote = req.get('quote', '')
            if not quote or len(quote) < 10:
                continue
            
            # Use shared verification utility
            if verify_quote_in_source(quote, source):
                verified.append(req)
        
        return verified
    
    # ========================================================================
    # DATABASE HELPERS
    # ========================================================================
    
    def _get_posting(self, posting_id: int) -> dict | None:
        """Fetch posting data including extracted_summary and language fields."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT posting_id, job_title, extracted_summary, 
                   source_language, job_description_en
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    
    def _save_language(self, posting_id: int, language: str):
        """Save detected language."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings SET source_language = %s WHERE posting_id = %s
        """, (language, posting_id))
        self.conn.commit()
    
    def _save_translation(self, posting_id: int, english_text: str):
        """Save English translation."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings SET job_description_en = %s WHERE posting_id = %s
        """, (english_text, posting_id))
        self.conn.commit()
    
    def _save_requirements(self, posting_id: int, requirements_json: str):
        """Save extracted requirements to postings table."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings
            SET extracted_requirements = %s
            WHERE posting_id = %s
        """, (requirements_json, posting_id))
        self.conn.commit()
    
    def _increment_failures(self, posting_id: int):
        """Increment processing_failures so work_query eventually skips this posting."""
        try:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE postings
                SET processing_failures = COALESCE(processing_failures, 0) + 1
                WHERE posting_id = %s
            """, (posting_id,))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
    
    def _mark_edge_case(self, posting_id: int, reason: str, value):
        """Mark posting as edge case so it's skipped but documented."""
        try:
            cur = self.conn.cursor()
            edge_case_json = json.dumps([{"type": "edge_case", "reason": reason, "value": value}])
            cur.execute("""
                UPDATE postings SET extracted_requirements = %s WHERE posting_id = %s
            """, (edge_case_json, posting_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
    
    # ========================================================================
    # LLM HELPERS
    # ========================================================================
    
    def _call_llm(self, prompt: str, purpose: str) -> str:
        """Call LLM and track for auditability."""
        start_time = time.time()
        
        temperature, seed = self._get_llm_settings()
        
        response = requests.post(OLLAMA_URL, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'seed': seed,
                'num_predict': 8192 if 'translate' in purpose else 4096
            }
        }, timeout=300)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        response_text = response.json().get('response', '')
        
        self._llm_calls.append({
            'purpose': purpose,
            'model': MODEL,
            'prompt_chars': len(prompt),
            'response_chars': len(response_text),
            'elapsed_ms': elapsed_ms
        })
        
        return response_text
    
    def _get_llm_settings(self) -> tuple:
        """Get temperature/seed from task_types (or defaults)."""
        if not TASK_TYPE_ID:
            return 0.0, 42
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT llm_temperature, llm_seed FROM task_types WHERE task_type_id = %s",
            (TASK_TYPE_ID,)
        )
        row = cur.fetchone()
        if row:
            return float(row['llm_temperature'] or 0), int(row['llm_seed'] or 42)
        return 0.0, 42
    
    def _parse_json_array(self, text: str) -> list | None:
        """Parse JSON array from LLM response using shared utility."""
        cleaned = clean_json_from_llm(text)
        if not cleaned:
            return None
        
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if not match:
            return None
        
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    
    # ========================================================================
    # QA REPORT (--qa mode)
    # ========================================================================
    
    def qa_report(self, sample_size: int = 50) -> dict:
        """
        Generate QA report for requirements extraction.
        
        Validates:
        1. Grounding: Do extracted requirements appear in source text?
        2. Coverage: Are we extracting reasonable number of requirements?
        3. Type distribution: Are requirement types balanced?
        
        Returns dict suitable for markdown output.
        """
        from datetime import datetime
        
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get completed extractions with source data
        cur.execute("""
            SELECT 
                p.posting_id,
                p.extracted_requirements,
                p.extracted_summary,
                COALESCE(p.job_description_en, p.job_description) as source_text,
                p.source_language,
                EXTRACT(EPOCH FROM (tl.completed_at - tl.started_at)) * 1000 as processing_time_ms,
                tl.created_at
            FROM postings p
            JOIN tickets tl ON tl.subject_id = p.posting_id
            WHERE tl.task_type_id = %s
              AND tl.status = 'completed'
              AND p.extracted_requirements IS NOT NULL
              AND NOT p.invalidated
            ORDER BY RANDOM()
            LIMIT %s
        """, (TASK_TYPE_ID, sample_size))
        
        samples = cur.fetchall()
        
        if not samples:
            return {'status': 'no_data', 'message': 'No completed extractions found'}
        
        results = []
        type_counts = {}
        
        for sample in samples:
            validation = self._qa_validate_sample(sample)
            results.append(validation)
            
            # Track requirement type distribution
            for rtype in validation.get('types', []):
                type_counts[rtype] = type_counts.get(rtype, 0) + 1
        
        # Compute statistics
        grounding_scores = [r['grounding_score'] for r in results if 'grounding_score' in r]
        req_counts = [r['requirements_count'] for r in results if 'requirements_count' in r]
        times = [float(s['processing_time_ms']) for s in samples if s['processing_time_ms']]
        
        poor_grounding = [r for r in results if r.get('grounding_score', 1) < 0.5]
        
        return {
            'status': 'ok',
            'generated_at': datetime.now().isoformat(),
            'task_type_id': TASK_TYPE_ID,
            'sample_size': len(samples),
            'grounding': {
                'avg_score': sum(grounding_scores) / len(grounding_scores) if grounding_scores else 0,
                'perfect': len([s for s in grounding_scores if s >= 1.0]),
                'poor': len(poor_grounding),
                'threshold': 0.5,
            },
            'requirements': {
                'avg_count': sum(req_counts) / len(req_counts) if req_counts else 0,
                'min': min(req_counts) if req_counts else 0,
                'max': max(req_counts) if req_counts else 0,
            },
            'type_distribution': type_counts,
            'timing': {
                'avg_ms': sum(times) / len(times) if times else 0,
                'min_ms': min(times) if times else 0,
                'max_ms': max(times) if times else 0,
            },
            'poor_grounding_samples': [
                {
                    'posting_id': r['posting_id'],
                    'grounding_score': r['grounding_score'],
                    'ungrounded': r.get('ungrounded_quotes', [])[:3],
                }
                for r in poor_grounding[:5]
            ],
            'samples': results,
        }
    
    def _qa_validate_sample(self, sample: dict) -> dict:
        """
        Validate a single extraction sample.
        
        Checks:
        1. Requirements are grounded in source text (word overlap)
        2. Reasonable number of requirements extracted
        """
        posting_id = sample['posting_id']
        source_text = sample.get('extracted_summary') or sample.get('source_text') or ''
        
        # Handle both raw JSON string and already-parsed list
        raw_requirements = sample['extracted_requirements']
        if raw_requirements is None:
            requirements = []
        elif isinstance(raw_requirements, list):
            requirements = raw_requirements
        else:
            try:
                requirements = json.loads(raw_requirements)
            except json.JSONDecodeError:
                return {
                    'posting_id': posting_id,
                    'passed': False,
                    'reason': 'invalid_json',
                }
        
        if not requirements:
            return {
                'posting_id': posting_id,
                'passed': True,
                'requirements_count': 0,
                'grounding_score': 1.0,
                'types': [],
            }
        
        # Build source word set for grounding check
        source_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', source_text.lower()))
        
        grounded = 0
        ungrounded_quotes = []
        types = []
        
        for req in requirements:
            if not isinstance(req, dict):
                continue
                
            quote = req.get('quote', '')
            rtype = req.get('type', 'unknown')
            types.append(rtype)
            
            # Check if quote words are in source
            quote_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', quote.lower()))
            if not quote_words:
                continue
                
            overlap = len(quote_words & source_words) / len(quote_words)
            if overlap >= 0.5:  # 50% word overlap threshold
                grounded += 1
            else:
                ungrounded_quotes.append(quote[:80])
        
        grounding_score = grounded / len(requirements) if requirements else 1.0
        
        return {
            'posting_id': posting_id,
            'passed': grounding_score >= 0.5,
            'requirements_count': len(requirements),
            'grounding_score': grounding_score,
            'grounded': grounded,
            'ungrounded': len(requirements) - grounded,
            'ungrounded_quotes': ungrounded_quotes,
            'types': types,
        }
    
    def print_qa_report(self, sample_size: int = 50):
        """Print QA report in markdown format."""
        report = self.qa_report(sample_size)
        
        if report['status'] == 'no_data':
            print(f"❌ {report['message']}")
            return
        
        print(f"# QA Report: Requirements Extraction")
        print(f"Generated: {report['generated_at']}")
        print(f"Task Type ID: {report['task_type_id']}")
        print()
        
        print("## 📊 Grounding Statistics")
        print("| Metric | Value |")
        print("|--------|-------|")
        g = report['grounding']
        print(f"| Sample size | {report['sample_size']} |")
        print(f"| Average grounding score | {g['avg_score']:.1%} |")
        print(f"| Perfect grounding (100%) | {g['perfect']} ({100*g['perfect']/report['sample_size']:.1f}%) |")
        print(f"| Poor grounding (<50%) | {g['poor']} ({100*g['poor']/report['sample_size']:.1f}%) |")
        print(f"| QA threshold | {g['threshold']:.0%} |")
        print()
        
        print("## 📋 Requirements Statistics")
        print("| Metric | Value |")
        print("|--------|-------|")
        r = report['requirements']
        print(f"| Average per posting | {r['avg_count']:.1f} |")
        print(f"| Min | {r['min']} |")
        print(f"| Max | {r['max']} |")
        print()
        
        print("## 🏷️ Type Distribution")
        print("| Type | Count |")
        print("|------|-------|")
        for rtype, count in sorted(report['type_distribution'].items(), key=lambda x: -x[1]):
            print(f"| {rtype} | {count} |")
        print()
        
        print("## ⏱️ Performance")
        print("| Metric | Value |")
        print("|--------|-------|")
        t = report['timing']
        print(f"| Average time | {t['avg_ms']:.0f}ms |")
        print(f"| Min time | {t['min_ms']:.0f}ms |")
        print(f"| Max time | {t['max_ms']:.0f}ms |")
        print()
        
        if report['poor_grounding_samples']:
            print("## ⚠️ Poor Grounding Samples")
            for s in report['poor_grounding_samples']:
                print(f"\n### posting_id={s['posting_id']} ({s['grounding_score']:.0%})")
                print("Ungrounded quotes:")
                for q in s['ungrounded']:
                    print(f"- \"{q}...\"")
        
        print()
        print("---")
        print("*Run with `--qa --sample N` to adjust sample size*")


# ============================================================================
# TEST HARNESS
# ============================================================================
def main():
    """
    Test the actor directly on a sample posting.
    
    Usage:
        python3 actors/postings__extracted_requirements_U.py           # random posting
        python3 actors/postings__extracted_requirements_U.py 12345     # specific posting
        python3 actors/postings__extracted_requirements_U.py --qa      # QA report (50 samples)
        python3 actors/postings__extracted_requirements_U.py --qa --sample 100  # larger sample
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Requirements extraction actor')
    parser.add_argument('posting_id', nargs='?', type=int, help='Posting ID to process')
    parser.add_argument('--qa', action='store_true', help='Run QA report on completed extractions')
    parser.add_argument('--sample', type=int, default=50, help='Sample size for QA report')
    args = parser.parse_args()
    
    with get_connection() as conn:
        actor = RequirementsExtractActor(conn)
        
        # QA mode
        if args.qa:
            actor.print_qa_report(args.sample)
            return
        
        # Process mode
        posting_id = args.posting_id
        
        if not posting_id:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT posting_id FROM postings 
                WHERE job_description IS NOT NULL
                  AND LENGTH(job_description) > 500
                  AND invalidated = FALSE
                ORDER BY RANDOM()
                LIMIT 1
            """)
            row = cur.fetchone()
            if not row:
                print("No suitable postings found")
                return
            posting_id = row['posting_id']
        
        print(f"Testing requirements extraction on posting {posting_id}...")
        print("=" * 60)
        
        actor.input_data = {'posting_id': posting_id}
        result = actor.process()
        
        print(f"\nSuccess: {result.get('success')}")
        print(f"Source Language: {result.get('source_language', '?')}")
        print(f"Requirements count: {result.get('requirements_count', 0)}")
        print(f"Rejected count: {result.get('rejected_count', 0)}")
        
        if result.get('success'):
            print("\n--- EXTRACTED REQUIREMENTS ---")
            reqs = json.loads(result.get('requirements_json', '[]'))
            for i, req in enumerate(reqs, 1):
                print(f"\n{i}. [{req.get('type', '?')}]")
                quote = req.get('quote', '')
                print(f"   \"{quote[:100]}...\"" if len(quote) > 100 else f"   \"{quote}\"")
        else:
            print(f"\nError: {result.get('error')}")
        
        if result.get('llm_calls'):
            print("\n--- LLM CALLS ---")
            for call in result['llm_calls']:
                print(f"  {call['purpose']}: {call['elapsed_ms']}ms")


if __name__ == '__main__':
    main()
