#!/usr/bin/env python3
"""
Lily CPS Extract - Extract Competency Proof Stack from Job Postings

Extracts structured competencies from job postings using a two-model approach:
- Lily (qwen2.5-coder:7b) extracts the CPS JSON
- Sage (qwen2.5:7b) grades the extraction
- If Sage fails it, Lily retries with feedback (max 3 attempts)

Input:  postings.posting_id (via work_query where no CPS exists)
Output: posting_facets rows (skill, experience, certificate, track_record, etc.)

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Posting] --> B{Preflight OK?}
    B -->|No summary| Z1[⏭️ SKIP: NO_SUMMARY]
    B -->|OK| C[🌸 Lily Extract]
    C --> D{Valid JSON?}
    D -->|No| Z2[❌ FAIL: JSON parse error]
    D -->|Yes| E[🌿 Sage Grade]
    E --> F{Contradiction?}
    F -->|Yes| G[🔄 Sage Retry]
    G --> E
    F -->|No| H{Pass?}
    H -->|Yes| I[💾 Save to posting_facets]
    I --> J[✅ SUCCESS]
    H -->|No| K{Attempts < 3?}
    K -->|No| L[⚠️ PARTIAL: Save anyway with warning]
    K -->|Yes| M[🔄 Lily Retry with Feedback]
    M --> E
```

Usage:
    # Via pull_daemon (normal):
    python3 core/pull_daemon.py
    
    # Direct test:
    python3 actors/posting_facets__row_C.py <posting_id>

Author: Arden
Date: 2026-01-16
Task Type ID: 9383
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

# ============================================================================
# CONFIGURATION
# ============================================================================
TASK_TYPE_ID = 9383
LILY_INSTRUCTION_ID = 3579
SAGE_INSTRUCTION_ID = 3580
RETRY_INSTRUCTION_ID = 3581

OLLAMA_URL = 'http://localhost:11434/api/generate'

# Models (per directive #24 - cross-model QA)
LILY_MODEL = "qwen2.5-coder:7b"  # Extractor
SAGE_MODEL = "qwen2.5:7b"        # Grader

MAX_RETRIES = 3


# ============================================================================
# ACTOR CLASS
# ============================================================================
class LilyCpsExtractActor:
    """
    Extract CPS competencies from job postings using Lily/Sage feedback loop.
    
    Three-Phase Structure (Directive #21):
    1. PREFLIGHT: Validate posting has summary and title
    2. PROCESS: Lily extracts → Sage grades → retry if needed
    3. QA: Validate output structure, normalize weights
    """
    
    def __init__(self, db_conn=None):
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = None  # Will be set when needed
            self._owns_connection = False
        self.input_data = None
        self._llm_calls = []  # Track all LLM calls for auditability
        self._llm_settings = None  # Cached from task_types
    
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================
    def process(self) -> dict:
        """Main entry point called by pull_daemon."""
        posting_id = self.input_data.get('subject_id') or self.input_data.get('posting_id')
        
        if not posting_id:
            return {'error': 'No posting_id in input', 'success': False}
        
        try:
            # === PREFLIGHT ===
            preflight_result = self._preflight(posting_id)
            if preflight_result:
                return preflight_result
            
            posting = self._get_posting(posting_id)
            
            # === PROCESS: Lily/Sage feedback loop ===
            lily_template = self._get_instruction_template(LILY_INSTRUCTION_ID)
            if not lily_template:
                return {'error': 'Lily instruction template not found', 'success': False}
            
            # Initial extraction
            prompt = self._build_lily_prompt(lily_template, posting)
            raw_output = self._call_llm(prompt, LILY_MODEL, 'lily_extract')
            cps_json = self._parse_json(raw_output)
            
            if not cps_json:
                return {
                    'error': 'JSON parse error on initial extraction',
                    'success': False,
                    'raw_output': raw_output[:500],
                    'llm_calls': self._llm_calls
                }
            
            # Sage grading loop
            sage_history = []
            attempt = 1
            
            while attempt <= MAX_RETRIES:
                # Grade with Sage
                sage_prompt = self._build_sage_prompt(posting, cps_json)
                sage_response = self._call_llm(sage_prompt, SAGE_MODEL, f'sage_grade_{attempt}')
                sage_grade = self._parse_json(sage_response)
                
                if not sage_grade:
                    sage_history.append({'attempt': attempt, 'sage_error': 'Invalid JSON'})
                    break
                
                # Check for contradiction
                contradiction = self._check_contradiction(sage_grade)
                if contradiction:
                    sage_history.append({'attempt': attempt, 'contradiction': contradiction})
                    # Give Sage one retry
                    retry_msg = f"\n\nYou listed {contradiction} as both missing AND hallucinated. That's a contradiction. Fix it."
                    sage_response = self._call_llm(sage_prompt + retry_msg, SAGE_MODEL, f'sage_contradiction_{attempt}')
                    sage_grade = self._parse_json(sage_response)
                    if not sage_grade:
                        break
                
                verdict = sage_grade.get('verdict', 'pass')
                sage_history.append({
                    'attempt': attempt,
                    'verdict': verdict,
                    'confidence': sage_grade.get('confidence', 5),
                    'missing': sage_grade.get('missing_skills', []),
                    'hallucinated': sage_grade.get('hallucinated_skills', [])
                })
                
                if verdict == 'pass':
                    break
                
                if attempt >= MAX_RETRIES:
                    break
                
                # Lily retry with feedback
                retry_prompt = self._build_retry_prompt(posting, cps_json, sage_grade)
                retry_response = self._call_llm(retry_prompt, LILY_MODEL, f'lily_retry_{attempt}')
                new_cps = self._parse_json(retry_response)
                
                if new_cps:
                    cps_json = new_cps
                
                attempt += 1
            
            # === QA: Normalize and validate ===
            cps_json = self._normalize_weights(cps_json)
            qa_issues = self._qa_validate(cps_json)
            
            # === SAVE ===
            rows = self._flatten_cps_to_rows(posting_id, cps_json)
            count = self._insert_competencies(rows)
            
            final_verdict = sage_history[-1].get('verdict', 'unknown') if sage_history else 'no_grading'
            
            return {
                'success': True,
                'competencies': count,
                'domain': cps_json.get('domain'),
                'seniority_level': cps_json.get('seniority_level'),
                'skillset_count': len(cps_json.get('skillset', [])),
                'sage_attempts': len(sage_history),
                'sage_final_verdict': final_verdict,
                'sage_history': sage_history,
                'qa_issues': qa_issues,
                'qa_passed': len(qa_issues) == 0,
                'llm_calls': self._llm_calls,
                '_consistency': '1/1'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'success': False,
                'llm_calls': self._llm_calls
            }
    
    # ========================================================================
    # PREFLIGHT
    # ========================================================================
    def _preflight(self, posting_id: int) -> Optional[dict]:
        """Validate posting has required data. Returns error dict or None if OK."""
        posting = self._get_posting(posting_id)
        
        if not posting:
            return {'error': f'Posting {posting_id} not found', 'success': False, 'skip_reason': 'NOT_FOUND'}
        
        summary = posting.get('extracted_summary')
        if not summary or len(summary.strip()) < 50:
            return {
                'error': f'Posting {posting_id} has no/insufficient summary',
                'success': False,
                'skip_reason': 'NO_SUMMARY',
                'posting_id': posting_id
            }
        
        if not posting.get('job_title'):
            return {
                'error': f'Posting {posting_id} has no job_title',
                'success': False,
                'skip_reason': 'NO_TITLE',
                'posting_id': posting_id
            }
        
        return None
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    def _get_posting(self, posting_id: int) -> Optional[dict]:
        """Fetch posting data."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT posting_id, job_title, COALESCE(source, 'unknown') as company,
                   competency_keywords::text as skill_keywords,
                   extracted_summary
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    
    def _get_instruction_template(self, instruction_id: int) -> Optional[str]:
        """Fetch instruction template from database."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT input_template FROM instructions WHERE instruction_id = %s",
            (instruction_id,)
        )
        row = cur.fetchone()
        return row['input_template'] if row else None
    
    def _get_llm_settings(self) -> tuple:
        """Fetch temperature, seed from task_types table."""
        if self._llm_settings:
            return self._llm_settings
        
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT llm_temperature, llm_seed FROM task_types WHERE task_type_id = %s",
            (TASK_TYPE_ID,)
        )
        row = cur.fetchone()
        if row:
            self._llm_settings = (float(row['llm_temperature'] or 0), int(row['llm_seed'] or 42))
        else:
            self._llm_settings = (0.0, 42)
        return self._llm_settings
    
    # ========================================================================
    # PROMPT BUILDING
    # ========================================================================
    def _build_lily_prompt(self, template: str, posting: dict) -> str:
        """Build Lily's extraction prompt."""
        return (template
            .replace('{company}', posting['company'])
            .replace('{job_title}', posting['job_title'])
            .replace('{skill_keywords}', posting['skill_keywords'] or '[]')
            .replace('{extracted_summary}', posting['extracted_summary'] or ''))
    
    def _build_sage_prompt(self, posting: dict, cps_json: dict) -> str:
        """Build Sage's grading prompt."""
        template = self._get_instruction_template(SAGE_INSTRUCTION_ID)
        if not template:
            template = self._get_sage_fallback()
        
        return (template
            .replace('{job_title}', posting['job_title'])
            .replace('{company}', posting['company'])
            .replace('{extracted_summary}', posting['extracted_summary'] or '')
            .replace('{extraction}', json.dumps(cps_json, indent=2)))
    
    def _build_retry_prompt(self, posting: dict, cps_json: dict, sage_grade: dict) -> str:
        """Build Lily's retry prompt with Sage's feedback."""
        template = self._get_instruction_template(RETRY_INSTRUCTION_ID)
        if not template:
            template = self._get_retry_fallback()
        
        def format_skills(skills_list):
            result = []
            for s in skills_list:
                if isinstance(s, dict):
                    result.append(s.get('skill', s.get('name', str(s))))
                else:
                    result.append(str(s))
            return ', '.join(result) if result else 'none'
        
        return (template
            .replace('{job_title}', posting['job_title'])
            .replace('{company}', posting['company'])
            .replace('{extracted_summary}', posting['extracted_summary'] or '')
            .replace('{missing_skills}', format_skills(sage_grade.get('missing_skills', [])))
            .replace('{hallucinated_skills}', format_skills(sage_grade.get('hallucinated_skills', [])))
            .replace('{issues}', '; '.join(sage_grade.get('issues', [])) or 'none')
            .replace('{suggested_seniority}', str(sage_grade.get('suggested_seniority') or 'no change'))
            .replace('{suggested_domain}', sage_grade.get('suggested_domain') or 'no change')
            .replace('{previous_extraction}', json.dumps(cps_json, indent=2)))
    
    # ========================================================================
    # LLM
    # ========================================================================
    def _call_llm(self, prompt: str, model: str, purpose: str) -> str:
        """Call LLM via Ollama and track for auditability."""
        start_time = time.time()
        temperature, seed = self._get_llm_settings()
        
        response = requests.post(OLLAMA_URL, json={
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'seed': seed,
                'num_predict': 4096
            }
        }, timeout=240)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        response_text = response.json().get('response', '')
        
        self._llm_calls.append({
            'purpose': purpose,
            'model': model,
            'prompt_chars': len(prompt),
            'response_chars': len(response_text),
            'elapsed_ms': elapsed_ms,
            'temperature': temperature,
            'seed': seed
        })
        
        return response_text
    
    def _parse_json(self, response: str) -> Optional[dict]:
        """Parse JSON from LLM response, handling common issues."""
        text = response.strip()
        
        # Strip markdown fences
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()
        
        # Fix range values: "1-3" → 1
        text = re.sub(r':\s*(\d+)-\d+\s*([,}\]])', r': \1\2', text)
        
        # Find JSON object
        if not text.startswith('{'):
            start = text.find('{')
            if start != -1:
                text = text[start:]
        
        # Find matching closing brace
        if text.startswith('{'):
            depth = 0
            end = 0
            for i, c in enumerate(text):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > 0:
                text = text[:end]
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def _check_contradiction(self, sage_grade: dict) -> list:
        """Check if Sage listed same skill as both missing AND hallucinated."""
        def get_name(item):
            if isinstance(item, dict):
                return item.get('skill', item.get('name', '')).lower().strip()
            return str(item).lower().strip()
        
        missing = set(get_name(s) for s in sage_grade.get('missing_skills', []) if get_name(s))
        hallucinated = set(get_name(s) for s in sage_grade.get('hallucinated_skills', []) if get_name(s))
        
        return list(missing & hallucinated)
    
    # ========================================================================
    # QA
    # ========================================================================
    def _normalize_weights(self, cps_json: dict) -> dict:
        """Normalize skillset weights to sum to exactly 100."""
        skillset = cps_json.get('skillset', [])
        if not skillset:
            return cps_json
        
        total = sum(s.get('weight', 0) for s in skillset)
        
        if total == 0:
            weight_each = 100 // len(skillset)
            remainder = 100 - (weight_each * len(skillset))
            for i, skill in enumerate(skillset):
                skill['weight'] = weight_each + (1 if i < remainder else 0)
        elif total != 100:
            scale = 100.0 / total
            running_total = 0
            for i, skill in enumerate(skillset):
                if i == len(skillset) - 1:
                    skill['weight'] = 100 - running_total
                else:
                    new_weight = round(skill.get('weight', 0) * scale)
                    skill['weight'] = max(1, new_weight)
                    running_total += skill['weight']
        
        return cps_json
    
    def _qa_validate(self, cps_json: dict) -> list:
        """Validate extraction quality."""
        issues = []
        skillset = cps_json.get('skillset', [])
        
        if len(skillset) == 0:
            issues.append('NO_SKILLS: Zero skills extracted')
        elif len(skillset) > 25:
            issues.append(f'EXCESSIVE_SKILLS: {len(skillset)} skills')
        
        total_weight = sum(s.get('weight', 0) for s in skillset)
        if total_weight != 100 and len(skillset) > 0:
            issues.append(f'WEIGHT_SUM: Total weight {total_weight} != 100')
        
        if not cps_json.get('domain'):
            issues.append('MISSING_DOMAIN: No domain specified')
        
        return issues
    
    # ========================================================================
    # SAVE
    # ========================================================================
    def _flatten_cps_to_rows(self, posting_id: int, cps_json: dict) -> list:
        """Flatten CPS JSON to posting_facets rows."""
        rows = []
        
        domain = cps_json.get('domain')
        seniority = cps_json.get('seniority')
        experience_setting = cps_json.get('experienceSetting')
        experience_role = cps_json.get('experienceRole')
        confidence = cps_json.get('confidence')
        
        skillset = cps_json.get('skillset', [])
        
        for comp in skillset:
            skill_name = comp.get('skill_name', '')
            if skill_name:
                skill_name = skill_name.replace('_', ' ').replace('-', ' ').lower().strip()
                if skill_name.endswith(' skills'):
                    skill_name = skill_name[:-7]
                elif skill_name.endswith(' skill'):
                    skill_name = skill_name[:-6]
            
            if not skill_name:
                continue
            
            experience_years = comp.get('experience_years')
            if experience_years is not None:
                try:
                    experience_years = int(experience_years)
                    if experience_years < 0 or experience_years > 50:
                        experience_years = None
                except (ValueError, TypeError):
                    experience_years = None
            
            importance = self._normalize_importance(comp.get('importance'))
            
            rows.append({
                'posting_id': posting_id,
                'industry_domain': domain,
                'seniority_raw': seniority,
                'experience_setting': experience_setting,
                'experience_role': experience_role,
                'skill_owl_name': skill_name,
                'experience_years': experience_years,
                'certificate': comp.get('certificate') or None,
                'track_record': comp.get('track_record') or None,
                'weight': comp.get('weight', 0),
                'alternatives': comp.get('alternatives'),
                'importance': importance,
                'confidence': confidence,
                'tags': comp.get('tags', []),
                'raw_requirement': None,
                'source_phrase': comp.get('source_phrase'),
                'inferred': comp.get('inferred', False),
                'reasoning': comp.get('reasoning'),
                'extracted_by': 'lily_cps_v2'
            })
        
        return rows
    
    def _normalize_importance(self, importance: str) -> str:
        """Normalize importance to standard values."""
        if not importance:
            return 'preferred'
        
        importance = importance.lower().strip()
        mapping = {
            'critical': 'essential',
            'essential': 'essential',
            'required': 'required',
            'high': 'required',
            'important': 'required',
            'preferred': 'preferred',
            'medium': 'preferred',
            'nice_to_have': 'nice_to_have',
            'nice-to-have': 'nice_to_have',
            'low': 'nice_to_have',
            'bonus': 'bonus',
            'optional': 'nice_to_have',
        }
        return mapping.get(importance, 'preferred')
    
    def _insert_competencies(self, rows: list) -> int:
        """Insert competency rows into posting_facets."""
        if not rows:
            return 0
        
        cur = self.conn.cursor()
        
        insert_sql = """
            INSERT INTO posting_facets (
                posting_id, industry_domain, seniority_raw, experience_setting, experience_role,
                skill_owl_name, experience_years, certificate, track_record,
                weight, alternatives,
                importance, confidence, tags, raw_requirement,
                source_phrase, inferred, reasoning,
                extracted_by
            ) VALUES (
                %(posting_id)s, %(industry_domain)s, %(seniority_raw)s, %(experience_setting)s, %(experience_role)s,
                %(skill_owl_name)s, %(experience_years)s, %(certificate)s, %(track_record)s,
                %(weight)s, %(alternatives)s,
                %(importance)s, %(confidence)s, %(tags)s, %(raw_requirement)s,
                %(source_phrase)s, %(inferred)s, %(reasoning)s,
                %(extracted_by)s
            )
        """
        
        count = 0
        for row in rows:
            cur.execute(insert_sql, row)
            count += 1
        
        self.conn.commit()
        return count
    
    # ========================================================================
    # FALLBACK PROMPTS (if DB lookup fails)
    # ========================================================================
    def _get_sage_fallback(self) -> str:
        return """You are Sage, a QA reviewer. Grade Lily's skill extraction.

RULES:
1. PASS if major skills captured, even with gaps
2. FAIL only for genuinely wrong information
3. Every missing skill needs a quote from the posting
4. Every hallucinated skill needs reasoning why it can't be inferred

Output JSON:
{
  "verdict": "pass" or "fail",
  "confidence": 1-10,
  "missing_skills": [{"skill": "name", "quote": "exact quote"}],
  "hallucinated_skills": [{"skill": "name", "reason": "why not inferable"}],
  "issues": ["specific issues"],
  "suggested_seniority": null or 1-7,
  "suggested_domain": null or correct domain
}

Job: {job_title} at {company}
Summary: {extracted_summary}
Extraction: {extraction}"""

    def _get_retry_fallback(self) -> str:
        return """You are Lily. Your previous extraction failed QA.

Issues found:
- Missing: {missing_skills}
- Hallucinated: {hallucinated_skills}
- Problems: {issues}
- Suggested seniority: {suggested_seniority}
- Suggested domain: {suggested_domain}

Fix the extraction. Same JSON format.

Job: {job_title} at {company}
Summary: {extracted_summary}

Previous (fix this): {previous_extraction}"""


# ============================================================================
# DIRECT EXECUTION
# ============================================================================
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 posting_facets__row_C.py <posting_id>")
        sys.exit(1)
    
    posting_id = int(sys.argv[1])
    
    with get_connection() as conn:
        actor = LilyCpsExtractActor(db_conn=conn)
        actor.input_data = {'posting_id': posting_id, 'subject_id': posting_id}
        result = actor.process()
        print(json.dumps(result, indent=2, default=str))
