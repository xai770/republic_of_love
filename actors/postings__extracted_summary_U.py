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
WORD_OVERLAP_THRESHOLD = 0.5  # 50% of words in a sentence must be in source
MIN_WORD_LENGTH = 4  # Ignore short words (the, and, etc.)


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
        """Extract summary using LLM with word-overlap validation."""
        description = data['description']
        template = data['template']
        
        # Build prompt (stricter on retry if feedback provided)
        if feedback:
            prompt = self._get_strict_prompt(template, description, feedback)
        else:
            prompt = template.replace('{variations_param_1}', description)
        
        response = self.call_llm(prompt, model=MODEL, temperature=0.1, timeout=240)
        
        if not response or len(response.strip()) < 50:
            return {
                'success': False,
                'error': 'Empty or too short LLM response',
                'response_length': len(response) if response else 0,
            }
        
        # Semantic validation against source
        validation_passed, hallucinations = self._validate_semantic_containment(
            source=description, summary=response)
        
        bad_data_warnings = [p for p in BAD_DATA_PATTERNS if p in response.lower()]
        
        result = {
            'success': True,
            'summary': response.strip(),
            'summary_length': len(response),
            'validation_passed': validation_passed,
            'bad_data_warnings': bad_data_warnings,
        }
        
        if not validation_passed:
            result['hallucinations'] = hallucinations
        
        return result
    
    def _qa_check(self, data: dict, result: dict) -> dict:
        """Check word overlap validation passed."""
        if result.get('validation_passed', True):
            return {'passed': True}
        
        hallucinations = result.get('hallucinations', [])
        return {
            'passed': False,
            'reason': f'{len(hallucinations)} ungrounded claims',
            'feedback': hallucinations,
        }
    
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
    
    def _get_strict_prompt(self, template: str, description: str, hallucinations: list) -> str:
        """Build stricter prompt for retry, emphasizing no hallucinations."""
        base_prompt = template.replace('{variations_param_1}', description)
        
        warning = """
IMPORTANT: Your previous response contained claims not found in the source text.
The following statements were NOT grounded in the original posting:
"""
        for h in hallucinations[:3]:  # Show max 3 examples
            warning += f"- {h}\n"
        
        warning += """
Extract ONLY information that appears in the original text. Do NOT infer or add details.
If information is not explicitly stated, write "Not specified" for that field.

"""
        return warning + base_prompt
    
    def _validate_semantic_containment(self, source: str, summary: str) -> tuple[bool, list[str]]:
        """
        Check that significant words in summary exist in source.
        
        Simple and fast: if the LLM is extracting (not generating), the words
        should exist in the source. No embeddings needed.
        
        Returns (passed, list_of_hallucinations)
        """
        import re
        
        # Build set of significant words from source (4+ chars, lowercase)
        source_words = set(re.findall(r'\b[a-zA-Z]{' + str(MIN_WORD_LENGTH) + r',}\b', source.lower()))
        
        if not source_words:
            return True, []  # No source to compare against
        
        # Split summary into sentences
        sentences = re.split(r'[.!?\n]|\s*-\s+', summary)
        
        hallucinations = []
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Skip short sentences and template labels
            if len(sentence) < 20:
                continue
            if re.match(r'^(Role|Company|Location|Job ID|Key Responsibilities|Requirements|Details):?\s*$', sentence, re.IGNORECASE):
                continue
            if re.match(r'^===.*===$', sentence):
                continue
            # Skip template phrases
            if 'not specified' in sentence.lower() or 'n/a' in sentence.lower():
                continue
            
            # Extract significant words from sentence
            sentence_words = set(re.findall(r'\b[a-zA-Z]{' + str(MIN_WORD_LENGTH) + r',}\b', sentence.lower()))
            
            if not sentence_words:
                continue
            
            # Check overlap
            found_words = sentence_words & source_words
            overlap = len(found_words) / len(sentence_words)
            
            if overlap < WORD_OVERLAP_THRESHOLD:
                hallucinations.append(sentence)
        
        return len(hallucinations) == 0, hallucinations


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
