#!/usr/bin/env python3
"""
IHL Score Saver
Saves IHL (Ideal Hire Likelihood) score to postings table.
Queries previous interaction for IHL verdict output.
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.wave_runner.script_actor_template import ScriptActorBase


class IHLScoreSaver(ScriptActorBase):
    """Save IHL score to postings table"""
    
    def process(self):
        """
        Query IHL expert verdict and save score to postings.
        
        Expected input:
        {
            "posting_id": 12345,
            "workflow_run_id": 99,
            "interaction_id": 888
        }
        
        Returns:
        {
            "status": "success",
            "ihl_score": 75,
            "ihl_category": "MEDIUM",
            "posting_id": 12345
        }
        """
        posting_id = self.input_data.get('posting_id')
        workflow_run_id = self.input_data.get('workflow_run_id')
        interaction_id = self.input_data.get('interaction_id')
        
        if not posting_id or not workflow_run_id:
            return {
                "status": "error",
                "error": "Missing posting_id or workflow_run_id"
            }
        
        # Query previous interaction output (IHL HR Expert - Final Verdict - conversation_id 9163)
        expert_output = self.query_previous_interaction(conversation_id=9163)
        
        if not expert_output:
            return {
                "status": "error",
                "error": "No verdict from IHL expert step"
            }
        
        # Extract IHL score from AI output
        # HR Expert returns JSON wrapped in markdown code blocks: ```json\n{...}\n```
        import re
        import json
        
        ihl_score = expert_output.get('ihl_score')
        ihl_verdict = None  # Store verdict separately from category
        
        if ihl_score is None and 'response' in expert_output:
            response = expert_output['response']
            
            # Try to parse JSON from markdown-wrapped response
            # Pattern: ```json\n{...}\n``` or just raw JSON
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*(?:\[SUCCESS\])?\s*```', response, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    ihl_score = parsed.get('ihl_score')
                    ihl_verdict = parsed.get('verdict')  # Store for output
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Look for "IHL Score: 75" pattern
            if ihl_score is None:
                match = re.search(r'IHL Score:\s*(\d+)', response, re.IGNORECASE)
                if match:
                    ihl_score = int(match.group(1))
        
        if ihl_score is None:
            return {
                "status": "error",
                "error": "No IHL score found in expert verdict",
                "expert_response_preview": expert_output.get('response', '')[:300]
            }
        
        cursor = self.db_conn.cursor()
        
        try:
            # Update postings table with IHL score
            cursor.execute("""
                UPDATE postings
                SET ihl_score = %s,
                    updated_by_interaction_id = %s,
                    posting_status = 'complete'
                WHERE posting_id = %s
            """, (ihl_score, interaction_id, posting_id))
            
            self.db_conn.commit()
            
            return {
                "status": "success",
                "ihl_score": ihl_score,
                "ihl_verdict": ihl_verdict,
                "posting_id": posting_id
            }
            
        except Exception as e:
            self.db_conn.rollback()
            return {
                "status": "error",
                "error": str(e)
            }


if __name__ == '__main__':
    actor = IHLScoreSaver()
    actor.run()
