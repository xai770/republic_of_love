#!/usr/bin/env python3
"""
Summary Extract - Thick Actor for Job Posting Summary Extraction

Extracts structured summary from job posting description.
Uses qwen2.5-coder:7b for efficient GPU processing.
Validates extraction via word overlap (summary words must exist in source).

NOTE: This actor is only used for Deutsche Bank postings (see turing_fetch.sh).
For AA postings, we embed job_description directly without summarization.

DB postings are fluffy/marketing-heavy, so we extract the core info first.

Pull architecture pattern:
1. Receive subject from pull_daemon (posting_id in input)
2. Call LLM via Ollama to extract summary from job_description
3. Validate: summary words must exist in source (word overlap check)
4. Retry once if hallucinations detected
5. Save to postings.extracted_summary

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Posting] --> B{Has description?}
    B -->|No| Z1[⏭️ SKIP: NO_DESCRIPTION]
    B -->|Yes| G[🤖 LLM Extract Summary]
    G --> H{Non-empty result?}
    G --> H{Non-empty result?}
    H -->|No| Z3[❌ FAIL: Empty response]
    H -->|Yes| I[🔍 Word Overlap Check]
    I --> J{>50% words in source?}
    J -->|Yes| K[💾 Save to postings]
    J -->|No| L{Retry count < 1?}
    L -->|Yes| G
    L -->|No| M[⚠️ Save with warning]
    M --> K
    K --> N[✅ SUCCESS]
```

Author: Arden
Date: 2026-01-15 (updated 2026-02-03 - removed translation logic)
"""

import os
import re
import psycopg2.extras
import requests

from core.base_actor import ProcessingActor, BAD_DATA_PATTERNS
from core.logging_config import get_logger

logger = get_logger(__name__)

# Config
INSTRUCTION_ID = 3328  # Extract with gemma3:1b (but we'll use qwen2.5-coder:7b)

# Model - same as lily_cps_extract for GPU efficiency (directive #14)
MODEL = "qwen2.5-coder:7b"

# Validation settings
MIN_SUMMARY_LENGTH = 50   # Minimum summary length in chars
MAX_SUMMARY_LENGTH = 5000  # Maximum summary length in chars


class SummaryExtractActor(ProcessingActor):
    """Thick actor for extracting job posting summaries.
    
    Uses ProcessingActor's 3-phase structure:
      1. Preflight: check description exists and is long enough
      2. Work: LLM extraction with word-overlap validation
      3. Save: write to postings.extracted_summary
    """
    
    TASK_TYPE_ID = 3335
    MAX_RETRIES = 1
    
    # ========================================================================
    # PHASE 1: PREFLIGHT
    # ========================================================================
    
    def _preflight(self, subject_id: int) -> dict:
        """Check posting exists and has sufficient description."""
        posting = self._get_posting(subject_id)
        if not posting:
            return {'ok': False, 'reason': 'NOT_FOUND', 'message': f'Posting {subject_id} not found'}
        
        description = posting.get('job_description')
        if not description or len(description.strip()) < 100:
            return {
                'ok': False,
                'reason': 'NO_DESCRIPTION',
                'message': f'Posting {subject_id} has insufficient description ({len(description) if description else 0} chars)',
            }
        
        template = self._get_instruction_template()
        if not template:
            return {'ok': False, 'reason': 'NO_TEMPLATE', 'message': 'Instruction template not found'}
        
        return {'ok': True, 'data': {'posting': posting, 'template': template, 'description': description}}
    
    # ========================================================================
    # PHASE 2: PROCESS
    # ========================================================================
    
    def _do_work(self, data: dict, feedback=None) -> dict:
        """Extract summary using LLM."""
        description = data['description']
        template = data['template']
        
        prompt = template.replace('{variations_param_1}', description)
        
        response = self.call_llm(prompt, model=MODEL, temperature=0.1, timeout=240)
        
        if not response or len(response.strip()) < MIN_SUMMARY_LENGTH:
            return {
                'success': False,
                'error': 'Empty or too short LLM response',
                'response_length': len(response) if response else 0,
            }
        
        bad_data_warnings = [p for p in BAD_DATA_PATTERNS if p in response.lower()]
        
        return {
            'success': True,
            'summary': response.strip(),
            'summary_length': len(response),
            'bad_data_warnings': bad_data_warnings,
        }
    
    def _qa_check(self, data: dict, result: dict) -> dict:
        """Check summary is reasonable (length, no bad patterns).
        
        Note: Word-overlap validation was removed 2026-02-16 because
        DB postings are German but summaries are English — legitimate
        translations were being flagged as 'hallucinations'.
        """
        summary = result.get('summary', '')
        bad = result.get('bad_data_warnings', [])
        if bad:
            return {'passed': False, 'reason': f'Bad data patterns: {bad}', 'feedback': bad}
        if len(summary) > MAX_SUMMARY_LENGTH:
            return {'passed': False, 'reason': f'Summary too long ({len(summary)} chars)'}
        return {'passed': True}
    
    # ========================================================================
    # PHASE 3: SAVE
    # ========================================================================
    
    def _save_result(self, subject_id: int, result: dict) -> None:
        """Save extracted summary to postings table."""
        cur = self.cursor()
        cur.execute("""
            UPDATE postings SET extracted_summary = %s WHERE posting_id = %s
        """, (result['summary'], subject_id))
        self.commit()
    
    def _get_posting(self, posting_id: int) -> dict | None:
        """Fetch posting data for summary extraction."""
        cur = self.cursor()
        cur.execute("""
            SELECT posting_id, job_title, job_description
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    
    def _get_instruction_template(self) -> str | None:
        """Fetch instruction template from database, with fallback."""
        try:
            cur = self.cursor()
            cur.execute(
                "SELECT input_template FROM instructions WHERE instruction_id = %s",
                (INSTRUCTION_ID,)
            )
            row = cur.fetchone()
            if row and row.get('input_template'):
                return row['input_template']
        except Exception:
            pass
        
        # Fallback: hardcoded summary extraction prompt
        return '''Summarize this job posting in English. Extract and present ONLY factual information about:
1. Job Title and Role
2. Required Skills and Qualifications  
3. Experience Requirements
4. Key Responsibilities
5. Location and Work Type
6. Salary/Benefits (if mentioned)

Use clear, concise bullet points. Do NOT add information not present in the original text.
If something is not specified, do not mention it at all.

Job Posting:
{variations_param_1}

Summary:'''
    


# Entry point for test harness
def main():
    """Run actor with batch processing support."""
    import argparse
    from core.database import get_connection
    
    parser = argparse.ArgumentParser(description='Extract summaries from job postings')
    parser.add_argument('posting_id', nargs='?', type=int, help='Single posting ID to process')
    parser.add_argument('--source', type=str, help='Filter by source (e.g., deutsche_bank)')
    parser.add_argument('--batch', type=int, default=0, help='Process N postings in batch mode')
    args = parser.parse_args()
    
    with get_connection() as conn:
        actor = SummaryExtractActor(conn)
        try:
            cur = actor.cursor()
            
            if args.posting_id:
                actor.input_data = {'posting_id': args.posting_id}
                result = actor.process()
                logger.info("Result: %s", result)
            else:
                limit = args.batch if args.batch > 0 else 1
                
                source_filter = "AND source = %s" if args.source else ""
                query = f"""
                    SELECT posting_id FROM postings 
                    WHERE extracted_summary IS NULL 
                      AND job_description IS NOT NULL
                      AND LENGTH(job_description) > 100
                      {source_filter}
                    ORDER BY posting_id
                    LIMIT %s
                """
                
                if args.source:
                    cur.execute(query, (args.source, limit))
                else:
                    cur.execute(query, (limit,))
                
                rows = cur.fetchall()
                
                if not rows:
                    logger.info("No postings need summary extraction %s",
                                f' for source={args.source}' if args.source else '')
                    return
                
                logger.info("Processing %s postings...", len(rows))
                success = failed = skipped = 0
                
                for i, row in enumerate(rows, 1):
                    actor.input_data = {'posting_id': row['posting_id']}
                    result = actor.process()
                    
                    if result.get('success'):
                        success += 1
                    elif result.get('skip_reason'):
                        skipped += 1
                    else:
                        failed += 1
                    actor.log_progress(i, len(rows), f"{success} ok, {skipped} skip, {failed} fail")
                
                logger.info("Done: %s success, %s skipped, %s failed", success, skipped, failed)
        finally:
            actor.cleanup()


if __name__ == '__main__':
    main()
