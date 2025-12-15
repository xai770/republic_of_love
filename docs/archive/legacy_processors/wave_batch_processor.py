#!/usr/bin/env python3
"""
Wave Batch Processor for Workflow 3001

Processes postings in "waves" - all postings through conversation 1, then all through 
conversation 2, etc. This minimizes model loading overhead by loading each model only once.

Usage:
    python3 tools/wave_batch_processor.py --workflow 3001 [--limit N]
"""

import sys
import os
from pathlib import Path
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wave_batch_processor import WaveBatchProcessorV2


class WaveBatchProcessor:
    """Process postings in waves through a workflow"""
    
    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id
        self.db_conn = get_connection()
        self.executor = WorkflowExecutor(self.db_conn)
        self.orchestrator = TuringOrchestrator()
        
    def get_pending_postings(self, limit: int = None) -> list:
        """Get postings that need processing"""
        query = """
            SELECT posting_id, job_description
            FROM postings
            WHERE extracted_summary IS NULL 
              AND ihl_score IS NOT NULL
            ORDER BY posting_id
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        cursor = self.db_conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        
        return [
            {
                'posting_id': row['posting_id'],
                'job_description': row['job_description']
            }
            for row in results
        ]
    
    def get_workflow_conversations(self) -> list:
        """Get ordered list of conversations in workflow"""
        query = """
            SELECT 
                wc.execution_order,
                wc.conversation_id,
                c.canonical_name,
                c.conversation_name
            FROM workflow_conversations wc
            JOIN conversations c ON c.conversation_id = wc.conversation_id
            WHERE wc.workflow_id = %s
            ORDER BY wc.execution_order
        """
        
        cursor = self.db_conn.cursor()
        cursor.execute(query, (self.workflow_id,))
        results = cursor.fetchall()
        cursor.close()
        
        return [
            {
                'execution_order': row['execution_order'],
                'conversation_id': row['conversation_id'],
                'canonical_name': row['canonical_name'],
                'name': row['conversation_name']
            }
            for row in results
        ]
    
    def get_posting_workflow_run(self, posting_id: int) -> int:
        """Get or create workflow_run_id for a posting"""
        # Check if run exists
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT workflow_run_id 
            FROM workflow_runs 
            WHERE workflow_id = %s 
              AND input_parameters->>'posting_id' = %s
            ORDER BY started_at DESC
            LIMIT 1
        """, (self.workflow_id, str(posting_id)))
        
        result = cursor.fetchone()
        
        if result:
            run_id = result['workflow_run_id']
        else:
            # Create new run
            cursor.execute("""
                INSERT INTO workflow_runs (
                    workflow_id,
                    input_parameters,
                    started_at,
                    status
                )
                VALUES (%s, %s, NOW(), 'RUNNING')
                RETURNING workflow_run_id
            """, (self.workflow_id, f'{{"posting_id": {posting_id}}}'))
            
            run_id = cursor.fetchone()['workflow_run_id']
            self.db_conn.commit()
        
        cursor.close()
        return run_id
    
    def execute_posting_through_workflow(
        self, 
        posting: dict
    ) -> tuple:
        """
        Execute full workflow for one posting
        
        Returns: (success: bool, output: str)
        """
        posting_id = posting['posting_id']
        
        try:
            print(f"  Posting {posting_id}: Executing workflow...", end=' ', flush=True)
            
            result = self.orchestrator.run_workflow(
                workflow_id=self.workflow_id,
                task_data={
                    'posting_id': posting_id,
                    'variations_param_1': posting['job_description']
                }
            )
            
            if result.get('status') == 'success':
                print(f"✓")
                return True, result.get('final_output', '')
            else:
                error = result.get('error', 'Unknown error')
                print(f"✗ {error}")
                return False, None
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return False, None
    
    def load_previous_outputs(self, posting_id: int, up_to_execution_order: int) -> dict:
        """Load previous conversation outputs for a posting"""
        query = """
            SELECT 
                wc.execution_order,
                li.response_received
            FROM llm_interactions li
            JOIN conversation_runs cr ON cr.conversation_run_id = li.conversation_run_id
            JOIN workflow_runs wr ON wr.workflow_run_id = li.workflow_run_id
            JOIN workflow_conversations wc ON wc.conversation_id = cr.conversation_id 
                AND wc.workflow_id = wr.workflow_id
            WHERE wr.workflow_id = %s
              AND wr.input_parameters->>'posting_id' = %s
              AND wc.execution_order < %s
            ORDER BY wc.execution_order
        """
        
        cursor = self.db_conn.cursor()
        cursor.execute(query, (self.workflow_id, str(posting_id), up_to_execution_order))
        results = cursor.fetchall()
        cursor.close()
        
        outputs = {}
        for idx, row in enumerate(results, start=1):
            exec_order = row['execution_order']
            output = row['response_received']
            outputs[f'session_{idx}_output'] = output
            outputs[f'session_r{exec_order}_output'] = output
        
        return outputs
    
    def process_wave(self, postings: list, conversation: dict):
        """Process all postings through one conversation (one wave)"""
        exec_order = conversation['execution_order']
        
        print(f"\n{'='*80}")
        print(f"WAVE {exec_order}: {conversation['canonical_name']}")
        print(f"{'='*80}")
        print(f"Processing {len(postings)} postings...")
        
        success_count = 0
        
        for posting in postings:
            posting_id = posting['posting_id']
            
            # Load previous outputs for this posting
            previous_outputs = self.load_previous_outputs(posting_id, exec_order)
            
            # Execute conversation
            success, output = self.execute_conversation_for_posting(
                posting, 
                conversation,
                previous_outputs
            )
            
            if success:
                success_count += 1
        
        print(f"\nWave completed: {success_count}/{len(postings)} successful")
    
    def run(self, limit: int = None, resume: bool = False):
        """Run wave processing for all pending postings"""
        
        print(f"Wave Batch Processor - Workflow {self.workflow_id}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Get postings to process
        postings = self.get_pending_postings(limit)
        
        if not postings:
            print("No postings found that need processing.")
            return
        
        print(f"Found {len(postings)} postings to process")
        
        # Get workflow conversations
        conversations = self.get_workflow_conversations()
        print(f"Workflow has {len(conversations)} conversations")
        
        # Process each wave
        for conversation in conversations:
            self.process_wave(postings, conversation)
        
        print(f"\n{'='*80}")
        print(f"Batch completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Wave Batch Processor - Process postings through workflow in waves'
    )
    
    parser.add_argument(
        '--workflow',
        type=int,
        default=3001,
        help='Workflow ID to execute (default: 3001)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of postings to process (for testing)'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from where previous run left off'
    )
    
    args = parser.parse_args()
    
    processor = WaveBatchProcessor(args.workflow)
    processor.run(limit=args.limit, resume=args.resume)


if __name__ == '__main__':
    main()
