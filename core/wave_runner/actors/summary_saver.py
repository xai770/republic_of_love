#!/usr/bin/env python3
"""
Workflow 3001 Step 10: summary_saver
Saves the standardized job summary to postings table.
Queries previous interaction outputs to get the formatted summary.
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.script_actor_template import ScriptActorBase


class SummarySaver(ScriptActorBase):
    """Save formatted summary to postings table"""
    
    def process(self):
        """
        Query format_standardization output and save to postings.
        
        Expected input:
        {
            "posting_id": 12345,
            "workflow_run_id": 99,
            "interaction_id": 888
        }
        
        Returns:
        {
            "status": "[SAVED]" | "[FAILED]",
            "posting_id": 12345,
            "summary_length": 450
        }
        """
        posting_id = self.input_data.get('posting_id')
        workflow_run_id = self.input_data.get('workflow_run_id')
        
        if not posting_id or not workflow_run_id:
            return {
                "status": "[FAILED]",
                "error": "Missing posting_id or workflow_run_id"
            }
        
        # Query previous interaction output (format_standardization - conversation_id 3341)
        summary_output = self.query_previous_interaction(conversation_id=3341)
        
        if not summary_output:
            return {
                "status": "[FAILED]",
                "error": "No summary from format_standardization step"
            }
        
        # Extract summary text from AI output
        # Expected: {"response": "**Role:** ...", ...}
        summary_text = summary_output.get('response', '')
        
        if not summary_text or len(summary_text) < 50:
            return {
                "status": "[FAILED]",
                "error": "Summary too short or missing"
            }
        
        cursor = self.db_conn.cursor()
        
        try:
            # Update postings table with summary
            cursor.execute("""
                UPDATE postings
                SET extracted_summary = %s,
                    updated_by_interaction_id = %s,
                    updated_at = NOW()
                WHERE posting_id = %s
            """, (summary_text, self.input_data.get('interaction_id'), posting_id))
            
            self.db_conn.commit()
            
            return {
                "status": "[SAVED]",
                "posting_id": posting_id,
                "summary_length": len(summary_text)
            }
            
        except Exception as e:
            self.db_conn.rollback()
            return {
                "status": "[FAILED]",
                "error": str(e)
            }


if __name__ == '__main__':
    actor = SummarySaver()
    actor.run()
