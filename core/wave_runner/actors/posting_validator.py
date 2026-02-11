#!/usr/bin/env python3
"""
Workflow 3001 Step 0: posting_validator
Validates active postings by checking if their URLs are still live.
Marks removed postings as invalidated with full audit trail through interactions.

This actor creates ONE INTERACTION PER POSTING for proper audit trail:
- Parent interaction: batch coordinator
- Child interactions: one per posting validated (linked via parent_interaction_id)

This allows:
1. Real-time progress monitoring (count child interactions)
2. Full audit trail per posting
3. Resume capability if interrupted

Usage: Called by wave_runner as part of WF3001
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.wave_runner.script_actor_template import ScriptActorBase
import requests
import time
from datetime import datetime


class PostingValidator(ScriptActorBase):
    """Validate posting URLs are still live, invalidate removed ones"""
    
    # Rate limiting
    DEFAULT_DELAY = 0.5  # seconds between requests
    REQUEST_TIMEOUT = 10  # seconds
    
    def check_url_exists(self, url: str) -> dict:
        """
        Check if a job posting URL is still live.
        
        Returns:
            {
                'exists': True/False/None (None = inconclusive),
                'status_code': int or None,
                'reason': 'ok' | '404' | 'redirect_to_error' | 'timeout' | 'error'
            }
        """
        try:
            # Use HEAD first (faster), fall back to GET if needed
            response = requests.head(url, timeout=self.REQUEST_TIMEOUT, allow_redirects=True)
            
            # Check for redirects to error pages
            if response.url != url:
                if '/error' in response.url.lower() or '/404' in response.url.lower():
                    return {
                        'exists': False,
                        'status_code': response.status_code,
                        'reason': 'redirect_to_error',
                        'final_url': response.url
                    }
            
            if response.status_code == 200:
                return {'exists': True, 'status_code': 200, 'reason': 'ok'}
            elif response.status_code == 404:
                return {'exists': False, 'status_code': 404, 'reason': '404'}
            elif response.status_code == 405:
                # HEAD not allowed, try GET
                response = requests.get(url, timeout=self.REQUEST_TIMEOUT, allow_redirects=True)
                if response.status_code == 200:
                    return {'exists': True, 'status_code': 200, 'reason': 'ok'}
                else:
                    return {'exists': False, 'status_code': response.status_code, 'reason': str(response.status_code)}
            else:
                return {'exists': False, 'status_code': response.status_code, 'reason': str(response.status_code)}
                
        except requests.exceptions.Timeout:
            return {'exists': None, 'status_code': None, 'reason': 'timeout'}
        except requests.exceptions.RequestException as e:
            return {'exists': None, 'status_code': None, 'reason': f'error: {str(e)[:50]}'}
    
    def create_child_interaction(self, posting_id: int, result: dict, parent_id: int, conversation_id: int, actor_id: int, workflow_run_id: int) -> int:
        """Create a child interaction for a single posting validation."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO interactions (
                conversation_id, actor_id, actor_type, posting_id,
                parent_interaction_id, workflow_run_id, execution_order,
                status, input, output, started_at, completed_at
            ) VALUES (
                %s, %s, 'script', %s, %s, %s, 1,
                'completed',
                %s::jsonb,
                %s::jsonb,
                NOW(), NOW()
            ) RETURNING interaction_id
        """, (
            conversation_id,
            actor_id,
            posting_id,
            parent_id,
            workflow_run_id,
            '{"action": "validate_url"}',
            f'{{"data": {{"exists": {str(result["exists"]).lower()}, "status_code": {result["status_code"] or "null"}, "reason": "{result["reason"]}"}}}}'
        ))
        interaction_id = cursor.fetchone()['interaction_id']
        self.db_conn.commit()
        return interaction_id
    
    def process(self):
        """
        Main processing: Check all active postings for removed status.
        Creates one child interaction per posting for audit trail.
        """
        cursor = self.db_conn.cursor()
        
        # Check rate limit: only run once per 12 hours
        cursor.execute("""
            SELECT completed_at 
            FROM interactions 
            WHERE conversation_id = (
                SELECT conversation_id FROM conversations WHERE canonical_name = 'validate_postings'
            )
            AND status = 'completed'
            AND parent_interaction_id IS NULL  -- Only count parent/batch interactions
            AND output->'data'->>'dry_run' != 'true'
            ORDER BY completed_at DESC
            LIMIT 1
        """)
        last_run = cursor.fetchone()
        if last_run and last_run['completed_at']:
            hours_since = (datetime.now(last_run['completed_at'].tzinfo) - last_run['completed_at']).total_seconds() / 3600
            if hours_since < 12:
                return {
                    'status': 'skipped',
                    'reason': f'Rate limited: last run was {hours_since:.1f} hours ago (min 12h)',
                    'last_run': last_run['completed_at'].isoformat()
                }
        
        # Get configuration from input
        config = self.input_data.get('config', {})
        limit = config.get('limit')  # Optional limit for testing
        delay = config.get('delay', self.DEFAULT_DELAY)
        dry_run = config.get('dry_run', False)
        
        # Get active postings with URLs
        query = """
            SELECT posting_id, external_url, job_title
            FROM postings
            WHERE invalidated = FALSE
              AND source = 'deutsche_bank'
              AND external_url IS NOT NULL
            ORDER BY posting_id
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        postings = cursor.fetchall()
        total = len(postings)
        
        # Get IDs from input_data (passed by runner script)
        parent_id = self.input_data.get('interaction_id')
        workflow_run_id = self.input_data.get('workflow_run_id')
        
        # Look up conversation and actor IDs
        cursor.execute("""
            SELECT conversation_id, actor_id 
            FROM conversations 
            WHERE canonical_name = 'validate_postings'
        """)
        conv_row = cursor.fetchone()
        conversation_id = conv_row['conversation_id']
        actor_id = conv_row['actor_id']
        
        # Results tracking
        results = {
            'total_to_check': total,
            'checked': 0,
            'still_live': 0,
            'removed': [],
            'errors': 0,
            'dry_run': dry_run
        }
        
        # Check each posting
        for idx, posting in enumerate(postings, 1):
            result = self.check_url_exists(posting['external_url'])
            
            # Create child interaction for this posting (unless dry run)
            if not dry_run:
                self.create_child_interaction(
                    posting['posting_id'], result, parent_id,
                    conversation_id, actor_id, workflow_run_id
                )
            
            results['checked'] += 1
            
            if result['exists'] is False:
                results['removed'].append({
                    'posting_id': posting['posting_id'],
                    'job_title': posting['job_title'][:100] if posting['job_title'] else None,
                    'reason': result['reason']
                })
                
                # Invalidate immediately (unless dry run)
                if not dry_run:
                    cursor.execute("""
                        UPDATE postings
                        SET invalidated = TRUE,
                            invalidated_at = CURRENT_TIMESTAMP,
                            invalidated_reason = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE posting_id = %s
                    """, (f"removed from site ({result['reason']})", posting['posting_id']))
                    self.db_conn.commit()
                    
            elif result['exists'] is True:
                results['still_live'] += 1
            else:
                results['errors'] += 1
            
            # Rate limit (except for last item)
            if idx < total:
                time.sleep(delay)
        
        cursor.close()
        
        return {
            'total_checked': results['checked'],
            'still_live': results['still_live'],
            'removed_count': len(results['removed']),
            'removed_postings': results['removed'][:50],  # Limit output size
            'errors': results['errors'],
            'dry_run': dry_run,
            'invalidated': len(results['removed']) if not dry_run else 0
        }


if __name__ == '__main__':
    actor = PostingValidator()
    actor.run()
