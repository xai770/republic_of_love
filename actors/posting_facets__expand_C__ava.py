#!/usr/bin/env python3
"""
posting_facets__expand_C__ava - Expand posting competency_keywords to posting_facets

PURPOSE:
Extract competency_keywords from postings and normalize them into the 
posting_facets table. Check against owl_names for existing matches.
Items without owl matches go to owl_pending for later processing.

PREREQUISITE: postings with competency_keywords (JSONB array)

Input:  postings.competency_keywords 
Output: posting_facets rows + owl_pending entries for unmatched skills

Flow Diagram:
```mermaid
flowchart TD
    A[📋 postings.competency_keywords] --> B[Extract JSON array]
    B --> C[For each keyword]
    C --> D{Check owl_names}
    D -->|Match found| E[Insert posting_facets with skill_owl_id]
    D -->|No match| F[Insert posting_facets without skill_owl_id]
    F --> G{Already in owl_pending?}
    G -->|Yes| H[Skip - already pending]
    G -->|No| I[Insert owl_pending status='pending']
```

PIPELINE POSITION:
```
postings.competency_keywords → [THIS ACTOR] → posting_facets
                                                    ↓
                                              owl_pending (for unmatched)
                                                    ↓
                                              Lucy → Alma → Carl → Adam
```

Usage:
    # Process single posting:
    python3 actors/posting_facets__expand_C__ava.py 12345
    
    # Process all postings with competency_keywords:
    python3 actors/posting_facets__expand_C__ava.py --all
    
    # Process batch (with limit):
    python3 actors/posting_facets__expand_C__ava.py --batch 100
    
    # Dry run (show what would be done):
    python3 actors/posting_facets__expand_C__ava.py --dry-run --batch 10

Author: Arden
Date: 2026-01-20
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import psycopg2
import psycopg2.extras

# ============================================================================
# SETUP
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection

# ============================================================================
# CONFIGURATION
# ============================================================================

# Map posting importance values to posting_facets importance
IMPORTANCE_MAP = {
    'critical': 'critical',
    'important': 'required', 
    'essential': 'essential',
    'required': 'required',
    'preferred': 'preferred',
    'nice_to_have': 'nice_to_have',
    'bonus': 'bonus',
    'high': 'required',
    'medium': 'preferred',
    'low': 'nice_to_have',
}


# ============================================================================
# ACTOR CLASS
# ============================================================================
class PostingCompetenciesExpandC:
    """
    Expand posting competency_keywords to posting_facets table.
    
    For each posting:
    1. Extract competency_keywords JSON array
    2. For each keyword, check owl_names for existing match
    3. Insert into posting_facets (with or without skill_owl_id)
    4. For unmatched skills, add to owl_pending if not already there
    """
    
    def __init__(self, db_conn=None):
        """Initialize with database connection."""
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = get_connection()
            self._owns_connection = True
        self.stats = {
            'postings_processed': 0,
            'competencies_inserted': 0,
            'owl_matches': 0,
            'owl_pending_created': 0,
            'owl_pending_skipped': 0,  # Already in pending
            'errors': 0,
        }
        self._owl_name_cache: Dict[str, int] = {}  # lower(name) -> owl_id
        self._pending_cache: set = set()  # lower(name) already in owl_pending
        self.input_data: Dict[str, Any] = {}  # For daemon interface
    
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    def process(self) -> Dict[str, Any]:
        """Main entry point for daemon. Wraps process_posting()."""
        posting_id = self.input_data.get('posting_id') or self.input_data.get('subject_id')
        if not posting_id:
            return {'success': False, 'error': 'No posting_id or subject_id in input'}
        return self.process_posting(posting_id)
    
    def _load_caches(self):
        """Load owl_names and owl_pending into memory for fast lookup."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Load owl_names (use first match if duplicates)
        cur.execute("""
            SELECT LOWER(display_name) as name_lower, owl_id 
            FROM owl_names 
            WHERE language = 'en'
            ORDER BY is_primary DESC  -- prefer primary names
        """)
        for row in cur.fetchall():
            name_lower = row['name_lower']
            if name_lower not in self._owl_name_cache:
                self._owl_name_cache[name_lower] = row['owl_id']
        
        # Load owl_pending skill names
        cur.execute("""
            SELECT LOWER(raw_value) as raw_lower
            FROM owl_pending 
            WHERE owl_type = 'competency'
        """)
        self._pending_cache = {row['raw_lower'] for row in cur.fetchall()}
        
        print(f"Loaded {len(self._owl_name_cache)} owl_names, {len(self._pending_cache)} pending")
    
    def _lookup_owl(self, skill_name: str) -> Optional[int]:
        """Look up skill in owl_names, return owl_id or None."""
        return self._owl_name_cache.get(skill_name.lower())
    
    def _is_pending(self, skill_name: str) -> bool:
        """Check if skill is already in owl_pending."""
        return skill_name.lower() in self._pending_cache
    
    def _normalize_importance(self, raw_importance: str) -> str:
        """Normalize importance value to allowed enum."""
        if not raw_importance:
            return 'preferred'
        return IMPORTANCE_MAP.get(raw_importance.lower(), 'preferred')
    
    def process_posting(self, posting_id: int, dry_run: bool = False) -> Dict[str, Any]:
        """Process a single posting's competency_keywords."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Fetch posting
        cur.execute("""
            SELECT posting_id, competency_keywords
            FROM postings
            WHERE posting_id = %s AND competency_keywords IS NOT NULL
        """, (posting_id,))
        
        row = cur.fetchone()
        if not row:
            return {'success': False, 'error': f'Posting {posting_id} not found or no keywords'}
        
        keywords = row['competency_keywords']
        if not keywords:
            return {'success': True, 'posting_id': posting_id, 'count': 0}
        
        results = {
            'posting_id': posting_id,
            'competencies': [],
            'owl_matches': 0,
            'pending_created': 0,
            'pending_skipped': 0,
        }
        
        for kw in keywords:
            skill_name = kw.get('name', '').strip()
            if not skill_name:
                continue
            
            # Skip compound phrases (>60 chars) - these are requirement sentences, not atomic skills
            # They stay in postings.competency_keywords for reference but don't go to owl_pending
            if len(skill_name) > 60:
                results.setdefault('compounds_skipped', 0)
                results['compounds_skipped'] += 1
                continue
            
            weight = kw.get('weight')
            importance = self._normalize_importance(kw.get('importance'))
            years = kw.get('years_required')
            
            # Look up in owl_names
            owl_id = self._lookup_owl(skill_name)
            
            comp_data = {
                'skill_name': skill_name,
                'owl_id': owl_id,
                'weight': weight,
                'importance': importance,
                'years': years,
            }
            results['competencies'].append(comp_data)
            
            if owl_id:
                results['owl_matches'] += 1
            
            if not dry_run:
                # Insert into posting_facets
                cur.execute("""
                    INSERT INTO posting_facets 
                        (posting_id, skill_owl_name, skill_owl_id, weight, importance, experience_years, raw_requirement)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (posting_id, skill_name, owl_id, weight, importance, years, json.dumps(kw)))
                
                # If no owl match and not already pending, add to owl_pending
                if not owl_id and not self._is_pending(skill_name):
                    cur.execute("""
                        INSERT INTO owl_pending (owl_type, raw_value, source_context, status)
                        VALUES ('competency', %s, %s, 'pending')
                        ON CONFLICT (owl_type, raw_value) DO NOTHING
                    """, (skill_name, json.dumps({'source': 'posting', 'posting_id': posting_id})))
                    
                    if cur.rowcount > 0:
                        results['pending_created'] += 1
                        self._pending_cache.add(skill_name.lower())
                    else:
                        results['pending_skipped'] += 1
                elif not owl_id:
                    results['pending_skipped'] += 1
        
        if not dry_run:
            self.conn.commit()
        
        results['success'] = True
        results['count'] = len(results['competencies'])
        return results
    
    def process_all(self, limit: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Process all postings with competency_keywords."""
        self._load_caches()
        
        cur = self.conn.cursor()  # Note: get_connection() defaults to RealDictCursor
        
        # Find postings that need processing (have keywords but not yet in posting_facets)
        if limit:
            cur.execute("""
                SELECT p.posting_id
                FROM postings p
                WHERE p.competency_keywords IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM posting_facets pc WHERE pc.posting_id = p.posting_id
                  )
                ORDER BY p.posting_id
                LIMIT %s
            """, (limit,))
        else:
            cur.execute("""
                SELECT p.posting_id
                FROM postings p
                WHERE p.competency_keywords IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM posting_facets pc WHERE pc.posting_id = p.posting_id
                  )
                ORDER BY p.posting_id
            """)
        
        posting_ids = [row['posting_id'] for row in cur.fetchall()]
        
        print(f"Processing {len(posting_ids)} postings...")
        
        for i, posting_id in enumerate(posting_ids):
            try:
                result = self.process_posting(posting_id, dry_run=dry_run)
                
                if result.get('success'):
                    self.stats['postings_processed'] += 1
                    self.stats['competencies_inserted'] += result.get('count', 0)
                    self.stats['owl_matches'] += result.get('owl_matches', 0)
                    self.stats['owl_pending_created'] += result.get('pending_created', 0)
                    self.stats['owl_pending_skipped'] += result.get('pending_skipped', 0)
                else:
                    self.stats['errors'] += 1
                    self.conn.rollback()  # Reset transaction state
                
                if (i + 1) % 100 == 0:
                    print(f"  Processed {i + 1}/{len(posting_ids)} postings...")
                    
            except Exception as e:
                print(f"  Error on posting {posting_id}: {e}")
                self.stats['errors'] += 1
                self.conn.rollback()  # Reset transaction state on error
        
        return {
            'success': True,
            'stats': self.stats,
            'dry_run': dry_run,
        }
    
    def print_stats(self):
        """Print processing statistics."""
        print("\n" + "=" * 60)
        print("PROCESSING COMPLETE")
        print("=" * 60)
        print(f"Postings processed:     {self.stats['postings_processed']}")
        print(f"Competencies inserted:  {self.stats['competencies_inserted']}")
        print(f"OWL matches found:      {self.stats['owl_matches']}")
        print(f"owl_pending created:    {self.stats['owl_pending_created']}")
        print(f"owl_pending skipped:    {self.stats['owl_pending_skipped']} (already existed)")
        print(f"Errors:                 {self.stats['errors']}")
        print("=" * 60)


# ============================================================================
# MAIN
# ============================================================================
def main():
    """
    Process posting competency_keywords.
    
    Usage:
        python3 actors/posting_facets__expand_C__ava.py 12345     # single posting
        python3 actors/posting_facets__expand_C__ava.py --all     # all postings
        python3 actors/posting_facets__expand_C__ava.py --batch 100   # first 100
        python3 actors/posting_facets__expand_C__ava.py --dry-run --batch 10
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Expand posting competency_keywords')
    parser.add_argument('posting_id', nargs='?', type=int, help='Single posting ID to process')
    parser.add_argument('--all', action='store_true', help='Process all postings')
    parser.add_argument('--batch', type=int, help='Process N postings')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without saving')
    args = parser.parse_args()
    
    with get_connection() as conn:
        actor = PostingCompetenciesExpandC(conn)
        
        if args.posting_id:
            # Single posting
            actor._load_caches()
            result = actor.process_posting(args.posting_id, dry_run=args.dry_run)
            print(json.dumps(result, indent=2, default=str))
            
        elif args.all or args.batch:
            # Batch processing
            limit = args.batch if args.batch else None
            result = actor.process_all(limit=limit, dry_run=args.dry_run)
            actor.print_stats()
            
        else:
            # Show help
            parser.print_help()
            print("\n--- Current State ---")
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM postings WHERE competency_keywords IS NOT NULL")
            total = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(DISTINCT posting_id) 
                FROM posting_facets
            """)
            processed = cur.fetchone()[0]
            print(f"Postings with keywords: {total}")
            print(f"Already processed:      {processed}")
            print(f"Remaining:              {total - processed}")


if __name__ == '__main__':
    main()
