#!/usr/bin/env python3
"""
Summary Extract - Thick Actor for Job Posting Summary Extraction

Extracts structured summary from job posting description.
Uses same model as posting_facets__row_C (qwen2.5-coder:7b) for GPU efficiency.
Validates extraction via word overlap (summary words must exist in source).

LANGUAGE HANDLING:
- For English postings: summarize job_description directly
- For non-English postings: summarize job_description_en (must exist)
- Output (extracted_summary) is ALWAYS in English

This ensures downstream actors don't need translation logic.

Pull architecture pattern:
1. Receive subject from pull_daemon (posting_id in input)
2. Detect language or use existing source_language
3. If non-English, require job_description_en (translated by interrogator)
4. Call LLM via Ollama to extract summary
5. Validate: summary words must exist in source (word overlap check)
6. Retry once if hallucinations detected
7. Save to postings.extracted_summary (always English)

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Posting] --> B{Has description?}
    B -->|No| Z1[⏭️ SKIP: NO_DESCRIPTION]
    B -->|Yes| C{English?}
    C -->|Yes| D[Use job_description]
    C -->|No| E{Has job_description_en?}
    E -->|No| Z2[⏭️ SKIP: NO_TRANSLATION]
    E -->|Yes| F[Use job_description_en]
    D --> G[🤖 LLM Extract Summary]
    F --> G
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
Date: 2026-01-15 (updated 2026-01-19)
"""

import sys
from pathlib import Path

import psycopg2.extras
import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.text_utils import detect_language

# Config
TASK_TYPE_ID = 3335  # session_a_extract_summary
INSTRUCTION_ID = 3328  # Extract with gemma3:1b (but we'll use qwen2.5-coder:7b)
OLLAMA_URL = 'http://localhost:11434/api/generate'

# Model - same as lily_cps_extract for GPU efficiency (directive #14)
MODEL = "qwen2.5-coder:7b"

# Validation settings
WORD_OVERLAP_THRESHOLD = 0.5  # 50% of words in a sentence must be in source
MIN_WORD_LENGTH = 4  # Ignore short words (the, and, etc.)
MAX_RETRIES = 1  # Retry once with stricter prompt if hallucinations detected

# Bad data patterns - if LLM says this, input was insufficient
BAD_DATA_PATTERNS = [
    'not specified in the given text',
    'not specified in the text',
    'not mentioned in the text',
    'not provided in the text',
    'information not available',
    'cannot be determined from',
]

# Translation prompt for non-English job postings
TRANSLATION_PROMPT = '''Translate this job posting to English. Preserve all formatting, structure, and meaning exactly.
Do not add any commentary or explanation. Output ONLY the English translation.

{text}'''


class SummaryExtractActor:
    """Thick actor for extracting job posting summaries."""
    
    def __init__(self, db_conn=None, auto_translate: bool = True):
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = None  # Will be set when needed
            self._owns_connection = False
        self.input_data = None
        self.auto_translate = auto_translate  # If True, translate non-English descriptions
        # Track LLM calls for auditability (stored in tickets.output.llm_calls)
        self._llm_calls = []
    
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    def process(self) -> dict:
        """Main entry point called by pull_daemon."""
        posting_id = self.input_data.get('subject_id') or self.input_data.get('posting_id')
        
        if not posting_id:
            return {'error': 'No posting_id in input', 'success': False}
        
        try:
            # 1. Fetch posting data
            posting = self._get_posting(posting_id)
            if not posting:
                return {'error': f'Posting {posting_id} not found', 'success': False}
            
            # 2. Check for description (preflight)
            description = posting.get('job_description')
            if not description or len(description.strip()) < 100:
                return {
                    'success': False,
                    'skip_reason': 'NO_DESCRIPTION',
                    'error': f'Posting {posting_id} has insufficient description ({len(description) if description else 0} chars)',
                    'posting_id': posting_id
                }
            
            # 3. Determine language and get English source text
            source_language = posting.get('source_language')
            if not source_language:
                source_language = detect_language(description)
                self._save_language(posting_id, source_language)
            
            # Use English source for summarization (output is always English)
            if source_language == 'en':
                english_source = description
            else:
                english_source = posting.get('job_description_en')
                if not english_source:
                    # Auto-translate if enabled
                    if self.auto_translate:
                        english_source = self._translate_to_english(description)
                        if english_source and len(english_source) > 100:
                            self._save_translation(posting_id, english_source)
                        else:
                            return {
                                'success': False,
                                'skip_reason': 'TRANSLATION_FAILED',
                                'error': f'Translation failed for {source_language} posting {posting_id}',
                                'posting_id': posting_id
                            }
                    else:
                        return {
                            'success': False,
                            'skip_reason': 'NO_TRANSLATION',
                            'error': f'Posting {posting_id} is {source_language} but has no job_description_en',
                            'posting_id': posting_id
                        }
            
            # 4. Get instruction template
            template = self._get_instruction_template()
            if not template:
                return {'error': 'Instruction template not found', 'success': False}
            
            # 4. Extract and validate with retry loop
            response = None
            hallucinations = []
            validation_passed = False
            retries = 0
            
            while retries <= MAX_RETRIES:
                # Build prompt (stricter on retry)
                if retries == 0:
                    prompt = template.replace('{variations_param_1}', english_source)
                else:
                    # Stricter prompt on retry - emphasize no hallucinations
                    prompt = self._get_strict_prompt(template, english_source, hallucinations)
                
                response = self._call_llm(prompt, purpose=f'summary_extract_attempt_{retries}')
                
                if not response or len(response.strip()) < 50:
                    return {
                        'error': 'Empty or too short LLM response',
                        'success': False,
                        'response_length': len(response) if response else 0,
                        'llm_calls': self._llm_calls
                    }
                
                # 5. Semantic validation against English source
                validation_passed, hallucinations = self._validate_semantic_containment(
                    source=english_source, 
                    summary=response
                )
                
                if validation_passed:
                    break
                
                retries += 1
            
            # 5b. Check for bad data patterns (LLM couldn't extract)
            bad_data_warnings = self._detect_bad_data(response)
            
            # 6. Save to postings (with warning if validation failed)
            self._save_summary(posting_id, response)
            
            result = {
                'success': True,
                'posting_id': posting_id,
                'source_language': source_language,
                'summary_length': len(response),
                'summary_preview': response[:200] + '...' if len(response) > 200 else response,
                'validation_passed': validation_passed,
                'retries': retries,
                'llm_calls': self._llm_calls,
                'bad_data_warnings': bad_data_warnings
            }
            
            if not validation_passed:
                result['warning'] = 'Saved with ungrounded claims'
                result['hallucinations'] = hallucinations
            
            if bad_data_warnings:
                result['warning'] = result.get('warning', '') + '; Bad input data detected'
                result['bad_data_count'] = len(bad_data_warnings)
            
            return result
            
        except Exception as e:
            return {'error': str(e), 'success': False, 'llm_calls': self._llm_calls}
    
    def _detect_bad_data(self, response: str) -> list[str]:
        """Detect if LLM response indicates bad/insufficient input data."""
        warnings = []
        response_lower = response.lower()
        for pattern in BAD_DATA_PATTERNS:
            if pattern in response_lower:
                warnings.append(pattern)
        return warnings
    
    def _get_posting(self, posting_id: int) -> dict | None:
        """Fetch posting data for summary extraction."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT posting_id, job_title, job_description,
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
    
    def _translate_to_english(self, text: str) -> str | None:
        """Translate text to English using LLM."""
        prompt = TRANSLATION_PROMPT.replace('{text}', text)
        return self._call_llm(prompt, 'translate_to_english')
    
    def _save_translation(self, posting_id: int, english_text: str):
        """Save English translation."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings SET job_description_en = %s WHERE posting_id = %s
        """, (english_text, posting_id))
        self.conn.commit()
    
    def _get_instruction_template(self) -> str | None:
        """Fetch instruction template from database, with fallback."""
        # First try database
        try:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
    
    def _call_llm(self, prompt: str, purpose: str = 'summary_extract') -> str:
        """Call LLM via Ollama and track for auditability."""
        import time
        start_time = time.time()
        
        temperature, seed = self._get_llm_settings()
        
        response = requests.post(OLLAMA_URL, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'seed': seed,
                'num_predict': 2048  # Enough for summary + translation
            }
        }, timeout=240)  # 4 min timeout for large docs
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        response_text = response.json().get('response', '')
        
        # Track for auditability
        self._llm_calls.append({
            'purpose': purpose,
            'model': MODEL,
            'prompt_chars': len(prompt),
            'response_chars': len(response_text),
            'elapsed_ms': elapsed_ms,
            'temperature': temperature,
            'seed': seed,
            'prompt': prompt,
            'response': response_text
        })
        
        return response_text
    
    def _get_llm_settings(self) -> tuple:
        """Get LLM settings. Uses defaults since task_types table may not exist."""
        # Default settings for summary extraction - low temperature for consistency
        return 0.1, 42
    
    def _save_summary(self, posting_id: int, summary: str):
        """Save extracted summary to postings table."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings
            SET extracted_summary = %s
            WHERE posting_id = %s
        """, (summary.strip(), posting_id))
        self.conn.commit()
    
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
    parser.add_argument('--source', type=str, help='Filter by source (e.g., arbeitsagentur)')
    parser.add_argument('--batch', type=int, default=0, help='Process N postings in batch mode')
    parser.add_argument('--no-translate', action='store_true', help='Skip translation (require job_description_en)')
    args = parser.parse_args()
    
    with get_connection() as conn:
        actor = SummaryExtractActor(conn, auto_translate=not args.no_translate)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if args.posting_id:
            # Single posting mode
            actor.input_data = {'posting_id': args.posting_id}
            result = actor.process()
            print(f"Result: {result}")
        else:
            # Batch mode
            limit = args.batch if args.batch > 0 else 1
            
            # Build query with optional source filter
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
                print(f"No postings need summary extraction{f' for source={args.source}' if args.source else ''}")
                return
            
            print(f"Processing {len(rows)} postings...")
            success = 0
            failed = 0
            skipped = 0
            
            for i, row in enumerate(rows, 1):
                actor.input_data = {'posting_id': row['posting_id']}
                result = actor.process()
                
                if result.get('success'):
                    success += 1
                    print(f"  [{i}/{len(rows)}] ✅ {row['posting_id']}")
                elif result.get('skip_reason'):
                    skipped += 1
                    print(f"  [{i}/{len(rows)}] ⏭️  {row['posting_id']}: {result.get('skip_reason')}")
                else:
                    failed += 1
                    print(f"  [{i}/{len(rows)}] ❌ {row['posting_id']}: {result.get('error', 'Unknown')}")
            
            print(f"\nDone: {success} success, {skipped} skipped, {failed} failed")


if __name__ == '__main__':
    main()
