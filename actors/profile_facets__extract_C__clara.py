#!/usr/bin/env python3
"""
profile_facets__extract_C.py - Clara the Facet Finder

PURPOSE:
Extract CPS facets from a single job in profile_work_history.
Each job is processed independently, producing profile_facets rows.

CPS DIMENSIONS:
- Skill: Core capability (Contract Compliance, ServiceNow, Python)
- Experience: Skill + years
- Certificate: Formal credential (ITIL, SAP certified)
- Track Record: Quantified achievement (€2M savings, 200+ team)
- Domain: Industry context (Banking, Television, Pharma)
- Seniority: Level (Lead, Manager, VP, Global)
- Setting: Environment (Global team, CTO office, EMEA)
- Role: Job function (Vendor Manager, Producer)

INPUT:
    work_history_id from profile_work_history table

OUTPUT:
    Rows in profile_facets table

WORKFLOW:
    profile_work_history → Clara → profile_facets

Author: Arden
Date: 2026-01-21
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection
from core.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# PROMPT
# ============================================================================
CLARA_PROMPT = """You are Clara, an expert at extracting career facets from job descriptions.

JOB TO ANALYZE:
Title: {job_title}
Company: {company_name}
Period: {start_date} to {end_date}
Description: {job_description}

Extract ALL facets from this job. Be thorough but precise.

FACET TYPES TO EXTRACT:

1. SKILLS - Specific capabilities (not vague terms)
   ✓ "Contract Compliance", "ServiceNow", "SAP CLM", "Python"
   ✗ "Management" (too vague), "Good communication" (soft skill fluff)

2. TRACK RECORDS - Quantified achievements with numbers
   ✓ "€2M savings p.a.", "200+ team members", "70+ contracts"
   ✗ "Improved processes" (no number)

3. CERTIFICATES - Formal credentials mentioned or implied
   ✓ "ITIL", "SAP certified", "CMM"

4. DOMAINS - Industry/sector context
   ✓ "Banking", "Pharma", "Television", "IT Procurement"

5. SENIORITY - Level indicators
   ✓ "Lead", "Global", "VP", "Manager", "Senior"

6. SETTINGS - Work environment context
   ✓ "Global team", "EMEA", "CTO office", "Group-wide"

7. ROLES - Job function categories
   ✓ "Vendor Manager", "Software Category Manager", "Producer"

OUTPUT FORMAT (valid JSON array only, no markdown):
[
  {{"type": "skill", "value": "Contract Compliance", "evidence": "Project lead Contract Compliance"}},
  {{"type": "skill", "value": "ServiceNow", "evidence": "PoE records to ServiceNow/SAM Pro"}},
  {{"type": "track_record", "value": "€2M savings p.a.", "evidence": "generating ca. 2M€ systematic savings"}},
  {{"type": "domain", "value": "Banking", "evidence": "Deutsche Bank"}},
  {{"type": "seniority", "value": "Lead", "evidence": "Project Lead, Team Lead"}},
  {{"type": "certificate", "value": "CMM", "evidence": "process framework according to CMM"}}
]

RULES:
1. Extract 5-15 facets per job (more for complex roles)
2. Evidence must be a quote or near-quote from the description
3. Skills should be specific tools, methods, or domains - not generic
4. Track records MUST have numbers
5. Output ONLY the JSON array - no explanation, no markdown

Extract facets now:"""


# ============================================================================
# ACTOR CLASS
# ============================================================================
class ProfileFacetsExtractor:
    """
    Clara - Extract CPS facets from profile_work_history entries.
    """
    
    def __init__(self, db_conn=None, model: str = "qwen2.5:7b"):
        self._owns_connection = db_conn is None
        self.conn = db_conn
        self.model = model
        self.input_data = {}
        
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    def _get_connection(self):
        if self.conn is None:
            self.conn = get_connection().__enter__()
        return self.conn
    
    def get_work_history(self, work_history_id: int) -> Optional[Dict]:
        """Load a single work history entry."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT wh.*, p.full_name
            FROM profile_work_history wh
            JOIN profiles p ON wh.profile_id = p.profile_id
            WHERE wh.work_history_id = %s
        """, (work_history_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    
    def call_llm(self, prompt: str) -> str:
        """Call Ollama API."""
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["response"]
    
    def parse_facets(self, llm_output: str) -> List[Dict]:
        """Parse JSON from LLM output."""
        # Try to find JSON array in output
        text = llm_output.strip()
        
        # Remove markdown if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        # Find array bounds
        start = text.find('[')
        end = text.rfind(']') + 1
        
        if start == -1 or end == 0:
            logger.warning(f"No JSON array found in output: {text[:200]}")
            return []
        
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Text was: {text[start:end][:500]}")
            return []
    
    def save_facets(self, profile_id: int, work_history_id: int, facets: List[Dict]):
        """Save extracted facets to profile_facets table."""
        conn = self._get_connection()
        cur = conn.cursor()
        
        for facet in facets:
            facet_type = facet.get('type', '')
            value = facet.get('value', '')
            evidence = facet.get('evidence', '')
            
            # Map facet type to column
            if facet_type == 'skill':
                cur.execute("""
                    INSERT INTO profile_facets 
                    (profile_id, work_history_id, skill_name, evidence, extracted_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (profile_id, work_history_id, value, evidence, 'clara'))
            
            elif facet_type == 'track_record':
                cur.execute("""
                    INSERT INTO profile_facets 
                    (profile_id, work_history_id, track_record, evidence, extracted_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (profile_id, work_history_id, value, evidence, 'clara'))
            
            elif facet_type == 'certificate':
                cur.execute("""
                    INSERT INTO profile_facets 
                    (profile_id, work_history_id, certificate, evidence, extracted_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (profile_id, work_history_id, value, evidence, 'clara'))
            
            elif facet_type == 'domain':
                cur.execute("""
                    INSERT INTO profile_facets 
                    (profile_id, work_history_id, industry_domain, evidence, extracted_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (profile_id, work_history_id, value, evidence, 'clara'))
            
            elif facet_type == 'seniority':
                cur.execute("""
                    INSERT INTO profile_facets 
                    (profile_id, work_history_id, seniority, evidence, extracted_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (profile_id, work_history_id, value, evidence, 'clara'))
            
            elif facet_type == 'setting':
                cur.execute("""
                    INSERT INTO profile_facets 
                    (profile_id, work_history_id, experience_setting, evidence, extracted_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (profile_id, work_history_id, value, evidence, 'clara'))
            
            elif facet_type == 'role':
                cur.execute("""
                    INSERT INTO profile_facets 
                    (profile_id, work_history_id, experience_role, evidence, extracted_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (profile_id, work_history_id, value, evidence, 'clara'))
        
        conn.commit()
        return len(facets)
    
    def process(self, work_history_id: int = None) -> Dict[str, Any]:
        """
        Main entry point. Extract facets from a work history entry.
        """
        # Get work_history_id from input_data if not provided
        if work_history_id is None:
            work_history_id = self.input_data.get('work_history_id')
        
        if not work_history_id:
            return {"status": "error", "message": "No work_history_id provided"}
        
        # Load work history
        job = self.get_work_history(work_history_id)
        if not job:
            return {"status": "error", "message": f"Work history {work_history_id} not found"}
        
        # Format dates
        start_date = str(job.get('start_date', 'unknown'))[:10]
        end_date = str(job.get('end_date', 'present'))[:10] if job.get('end_date') else 'present'
        
        # Build prompt
        prompt = CLARA_PROMPT.format(
            job_title=job.get('job_title', ''),
            company_name=job.get('company_name', ''),
            start_date=start_date,
            end_date=end_date,
            job_description=job.get('job_description', '')
        )
        
        # Call LLM
        logger.info(f"Extracting facets for: {job.get('job_title')} @ {job.get('company_name')}")
        llm_output = self.call_llm(prompt)
        
        # Parse facets
        facets = self.parse_facets(llm_output)
        
        if not facets:
            return {
                "status": "error", 
                "message": "No facets extracted",
                "raw_output": llm_output[:500]
            }
        
        # Save facets
        count = self.save_facets(job['profile_id'], work_history_id, facets)
        
        return {
            "status": "success",
            "work_history_id": work_history_id,
            "job_title": job.get('job_title'),
            "facets_extracted": count,
            "facets": facets
        }


# ============================================================================
# CLI
# ============================================================================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Clara - Extract facets from work history')
    parser.add_argument('work_history_id', type=int, nargs='?', help='Work history ID to process')
    parser.add_argument('--profile', type=int, help='Process all jobs for a profile')
    parser.add_argument('--model', default='qwen2.5:7b', help='LLM model to use')
    parser.add_argument('--dry-run', action='store_true', help='Show prompt without calling LLM')
    
    args = parser.parse_args()
    
    if args.profile:
        # Process all jobs for a profile
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT work_history_id, job_title, company_name 
                FROM profile_work_history 
                WHERE profile_id = %s
                ORDER BY start_date DESC
            """, (args.profile,))
            jobs = cur.fetchall()
            
            print(f"Processing {len(jobs)} jobs for profile {args.profile}\n")
            
            clara = ProfileFacetsExtractor(db_conn=conn, model=args.model)
            
            for job in jobs:
                result = clara.process(job['work_history_id'])
                print(f"  {job['job_title'][:40]:<40} → {result.get('facets_extracted', 0)} facets")
    
    elif args.work_history_id:
        # Process single job
        clara = ProfileFacetsExtractor(model=args.model)
        
        if args.dry_run:
            job = clara.get_work_history(args.work_history_id)
            if job:
                start_date = str(job.get('start_date', 'unknown'))[:10]
                end_date = str(job.get('end_date', 'present'))[:10] if job.get('end_date') else 'present'
                prompt = CLARA_PROMPT.format(
                    job_title=job.get('job_title', ''),
                    company_name=job.get('company_name', ''),
                    start_date=start_date,
                    end_date=end_date,
                    job_description=job.get('job_description', '')
                )
                print(prompt)
            else:
                print(f"Work history {args.work_history_id} not found")
        else:
            result = clara.process(args.work_history_id)
            print(json.dumps(result, indent=2, default=str))
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
