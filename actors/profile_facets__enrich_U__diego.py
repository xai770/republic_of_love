#!/usr/bin/env python3
"""
profile_facets__enrich_U__diego.py - Diego the Enabler

PURPOSE:
Add implied/enabler skills that people don't mention because they seem "basic".
If you were a Global Software Compliance Manager at Deutsche Bank, you OBVIOUSLY:
- Used SharePoint, Confluence, JIRA
- Did Excel pivot tables and PowerPoint decks  
- Managed via Teams/video conferencing
- Knew contract negotiation

This is a RULE-BASED enrichment step, not LLM. Fast and deterministic.

INPUT:
    profile_facets rows for a work_history_id (from Clara)

OUTPUT:
    Additional profile_facets rows with inferred=true

WORKFLOW:
    Clara (explicit) → Diego (implied) → complete facet picture

Author: Arden
Date: 2026-01-21
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection
from core.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# LOAD ENABLER CONFIG
# ============================================================================
CONFIG_PATH = PROJECT_ROOT / "config" / "enabler_skills.json"

def load_enabler_config() -> Dict:
    """Load the enabler skills knowledge base."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    else:
        logger.warning(f"Enabler config not found at {CONFIG_PATH}")
        return {}


# ============================================================================
# ACTOR CLASS
# ============================================================================
class DiegoEnricher:
    """
    Diego - Adds implied/enabler skills based on Clara's facets.
    
    Rules:
    1. Look at domain → add universal domain tools
    2. Look at seniority → add seniority-typical skills
    3. Look at role → add role-typical skills  
    4. Look at existing skills → add triggered skills
    5. Look at setting → add setting-typical skills
    
    All added facets get inferred=true, type='skill_implied'
    """
    
    def __init__(self, db_conn=None):
        self._owns_connection = db_conn is None
        self.conn = db_conn
        self.config = load_enabler_config()
        
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    def _get_connection(self):
        if self.conn is None:
            self.conn = get_connection().__enter__()
        return self.conn
    
    def get_existing_facets(self, work_history_id: int) -> List[Dict]:
        """Get Clara's facets for this work history entry."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT skill_name, track_record, certificate, 
                   industry_domain, seniority, experience_setting, experience_role,
                   evidence, confidence, extracted_by
            FROM profile_facets
            WHERE work_history_id = %s
        """, (work_history_id,))
        
        # Convert to standardized format
        facets = []
        for row in cur.fetchall():
            row = dict(row)
            if row.get('skill_name'):
                facets.append({'facet_type': 'skill', 'value': row['skill_name']})
            if row.get('track_record'):
                facets.append({'facet_type': 'track_record', 'value': row['track_record']})
            if row.get('certificate'):
                facets.append({'facet_type': 'certificate', 'value': row['certificate']})
            if row.get('industry_domain'):
                facets.append({'facet_type': 'domain', 'value': row['industry_domain']})
            if row.get('seniority'):
                facets.append({'facet_type': 'seniority', 'value': row['seniority']})
            if row.get('experience_setting'):
                facets.append({'facet_type': 'setting', 'value': row['experience_setting']})
            if row.get('experience_role'):
                facets.append({'facet_type': 'role', 'value': row['experience_role']})
        
        return facets
    
    def get_work_history(self, work_history_id: int) -> Optional[Dict]:
        """Get work history metadata."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM profile_work_history
            WHERE work_history_id = %s
        """, (work_history_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    
    def extract_signals(self, existing_facets: List[Dict], work_history: Dict) -> Dict:
        """
        Extract signal values from existing facets.
        Returns: {domain: str, seniority: str, roles: [str], skills: [str], settings: [str]}
        """
        signals = {
            'domain': None,
            'seniority': None,
            'roles': [],
            'skills': [],
            'settings': []
        }
        
        for facet in existing_facets:
            ftype = facet['facet_type']
            value = facet['value'].lower()
            
            if ftype == 'domain':
                signals['domain'] = value
            elif ftype == 'seniority':
                signals['seniority'] = value
            elif ftype == 'role':
                signals['roles'].append(value)
            elif ftype == 'skill':
                signals['skills'].append(value)
            elif ftype == 'setting':
                signals['settings'].append(value)
        
        # Infer from job metadata if not in facets
        if work_history:
            title = (work_history.get('job_title') or '').lower()
            company = (work_history.get('company_name') or '').lower()
            description = (work_history.get('job_description') or '').lower()
            
            # Infer domain from company/title/description
            if not signals['domain']:
                # Banking
                if any(bank in company for bank in ['bank', 'deutsche bank', 'dresdner', 'commerzbank']):
                    signals['domain'] = 'banking'
                # Pharma
                elif any(pharma in company for pharma in ['novartis', 'roche', 'pfizer', 'pharma']):
                    signals['domain'] = 'pharma'
                # Television/Media
                elif any(tv in company for tv in ['zdf', 'ard', 'television', 'broadcaster', 'film']):
                    signals['domain'] = 'television'
                elif any(tv in title for tv in ['producer', 'director', 'editor']):
                    if any(media in description for media in ['video', 'film', 'documentary', 'television']):
                        signals['domain'] = 'television'
            
            # Infer seniority from title
            if not signals['seniority']:
                if 'global' in title:
                    signals['seniority'] = 'global'
                elif 'vp' in title or 'vice president' in title:
                    signals['seniority'] = 'vp'
                elif 'director' in title:
                    signals['seniority'] = 'director'
                elif 'manager' in title:
                    signals['seniority'] = 'manager'
                elif 'lead' in title:
                    signals['seniority'] = 'lead'
            
            # Infer role from title
            if 'producer' in title:
                signals['roles'].append('producer')
            if 'vendor' in title:
                signals['roles'].append('vendor manager')
            if 'category' in title:
                signals['roles'].append('category manager')
        
        return signals
    
    def find_enabler_skills(self, signals: Dict) -> Set[str]:
        """Apply rules to find enabler skills."""
        enablers: Set[str] = set()
        
        # 1. Domain-based enablers
        if signals['domain']:
            domain_config = self.config.get('by_domain', {}).get(signals['domain'], {})
            
            # Universal tools for domain
            enablers.update(domain_config.get('universal', []))
            
            # Management tools if manager/director level
            if signals['seniority'] in ('manager', 'director', 'vp', 'global'):
                enablers.update(domain_config.get('management', []))
            
            # Tech tools if any tech-related facets
            tech_indicators = ['software', 'it', 'technology', 'system', 'data']
            if any(ind in ' '.join(signals['skills']) for ind in tech_indicators):
                enablers.update(domain_config.get('technology', []))
            
            # Procurement tools
            procurement_indicators = ['vendor', 'procurement', 'sourcing', 'contract', 'category']
            if any(ind in ' '.join(signals['skills'] + signals['roles']) for ind in procurement_indicators):
                enablers.update(domain_config.get('procurement', []))
        
        # 2. Seniority-based enablers
        if signals['seniority']:
            seniority_skills = self.config.get('by_seniority', {}).get(signals['seniority'], [])
            enablers.update(seniority_skills)
        
        # 3. Role-based enablers
        for role in signals['roles']:
            for role_key, role_skills in self.config.get('by_role', {}).items():
                if role_key in role or role in role_key:
                    enablers.update(role_skills)
        
        # 4. Skill-triggered enablers
        for skill in signals['skills']:
            for trigger, triggered_skills in self.config.get('by_skill_trigger', {}).items():
                if trigger in skill or skill in trigger:
                    enablers.update(triggered_skills)
        
        # 5. Setting-based enablers
        for setting in signals['settings']:
            for setting_key, setting_skills in self.config.get('by_setting', {}).items():
                if setting_key in setting or any(word in setting for word in setting_key.split()):
                    enablers.update(setting_skills)
        
        # Don't add skills that already exist
        existing_skills = set(s.lower() for s in signals['skills'])
        enablers = enablers - existing_skills
        
        return enablers
    
    def process(self, work_history_id: int, dry_run: bool = True) -> Dict:
        """
        Process a work history entry: find and optionally insert enabler skills.
        
        Args:
            work_history_id: The work history entry to enrich
            dry_run: If True, just return what would be added (no DB writes)
            
        Returns:
            {
                'work_history_id': int,
                'existing_facets': int,
                'enabler_skills_found': [str],
                'facets_added': int (0 if dry_run)
            }
        """
        work_history = self.get_work_history(work_history_id)
        if not work_history:
            return {'error': f'Work history {work_history_id} not found'}
        
        existing_facets = self.get_existing_facets(work_history_id)
        signals = self.extract_signals(existing_facets, work_history)
        enabler_skills = self.find_enabler_skills(signals)
        
        result = {
            'work_history_id': work_history_id,
            'job_title': work_history.get('job_title'),
            'signals': signals,
            'existing_facets': len(existing_facets),
            'enabler_skills_found': sorted(enabler_skills),
            'facets_added': 0
        }
        
        if not dry_run and enabler_skills:
            conn = self._get_connection()
            cur = conn.cursor()
            
            profile_id = work_history['profile_id']
            
            for skill in enabler_skills:
                # Determine evidence based on which rule triggered it
                evidence = self._determine_evidence(skill, signals)
                
                cur.execute("""
                    INSERT INTO profile_facets 
                    (profile_id, work_history_id, skill_name, evidence, confidence, extracted_by)
                    VALUES (%s, %s, %s, %s, 0.7, 'diego')
                    ON CONFLICT DO NOTHING
                """, (profile_id, work_history_id, skill, evidence))
                result['facets_added'] += 1
                result['facets_added'] += 1
            
            conn.commit()
        
        return result
    
    def _determine_evidence(self, skill: str, signals: Dict) -> str:
        """Generate evidence string explaining why we inferred this skill."""
        parts = []
        
        if signals['domain']:
            parts.append(f"domain: {signals['domain']}")
        if signals['seniority']:
            parts.append(f"seniority: {signals['seniority']}")
        if signals['roles']:
            parts.append(f"roles: {', '.join(signals['roles'][:2])}")
        
        return f"Implied by {'; '.join(parts)}" if parts else "Implied by job context"
    
    def enrich_profile(self, profile_id: int, dry_run: bool = True) -> Dict:
        """Enrich all work history entries for a profile."""
        conn = self._get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT work_history_id 
            FROM profile_work_history 
            WHERE profile_id = %s
            ORDER BY start_date DESC
        """, (profile_id,))
        
        work_history_ids = [row['work_history_id'] for row in cur.fetchall()]
        
        results = []
        total_enablers = set()
        total_added = 0
        
        for wh_id in work_history_ids:
            result = self.process(wh_id, dry_run=dry_run)
            results.append(result)
            total_enablers.update(result.get('enabler_skills_found', []))
            total_added += result.get('facets_added', 0)
        
        return {
            'profile_id': profile_id,
            'jobs_processed': len(results),
            'total_enabler_skills': sorted(total_enablers),
            'total_facets_added': total_added,
            'dry_run': dry_run,
            'by_job': results
        }


# ============================================================================
# CLI
# ============================================================================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Diego - Add implied/enabler skills')
    parser.add_argument('--work-history-id', '-w', type=int, help='Process single work history')
    parser.add_argument('--profile-id', '-p', type=int, help='Process all jobs for profile')
    parser.add_argument('--commit', action='store_true', help='Actually insert (default: dry run)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    if not args.work_history_id and not args.profile_id:
        parser.print_help()
        print("\n❌ Specify --work-history-id or --profile-id")
        return 1
    
    with get_connection() as conn:
        diego = DiegoEnricher(db_conn=conn)
        
        if args.profile_id:
            result = diego.enrich_profile(args.profile_id, dry_run=not args.commit)
            
            print(f"\n{'📋 DRY RUN' if result['dry_run'] else '✅ COMMITTED'}")
            print(f"Profile: {result['profile_id']}")
            print(f"Jobs processed: {result['jobs_processed']}")
            print(f"Total enabler skills found: {len(result['total_enabler_skills'])}")
            
            if args.verbose:
                print("\n📦 Enabler skills to add:")
                for skill in result['total_enabler_skills']:
                    print(f"  • {skill}")
                
                print("\n📊 By job:")
                for job in result['by_job']:
                    title = job.get('job_title', 'Unknown')[:50]
                    count = len(job.get('enabler_skills_found', []))
                    print(f"  {title}: +{count} enablers")
            
            if not result['dry_run']:
                print(f"\n✅ Added {result['total_facets_added']} facets to profile_facets")
            else:
                print(f"\n💡 Run with --commit to actually add these {len(result['total_enabler_skills'])} skills")
        
        else:
            result = diego.process(args.work_history_id, dry_run=not args.commit)
            print(json.dumps(result, indent=2, default=str))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
