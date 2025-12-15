#!/usr/bin/env python3
"""
Workflow 3001 Step 2 & 11 & 16: sql_query_executor
Executes SQL queries and returns results for branching decisions.
Used for checking if summary exists, skills exist, IHL score exists.

Supports staleness checks: if staleness_days is set, also checks if
the last interaction for this posting+conversation was recent enough.
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.script_actor_template import ScriptActorBase


class SQLQueryExecutor(ScriptActorBase):
    """Execute SQL query and return result for branching"""
    
    def process(self):
        """
        Execute SQL query and map result to branch condition.
        
        Expected input:
        {
            "query": "SELECT EXISTS(...) as summary_exists",
            "result_field": "summary_exists",
            "branch_map": {
                "true": "[SKIP]",
                "false": "[RUN]",
                "null": "[RUN]",
                "error": "[RUN]"
            },
            "posting_id": 12345,
            "staleness_days": 7,  # Optional: re-run if last check was >7 days ago
            "staleness_conversation_id": 9144  # Optional: which conversation to check staleness for
        }
        
        Returns:
        {
            "status": "[SKIP]" | "[RUN]" | "[TIMEOUT]" | "[FAILED]",
            "result_value": true/false/null,
            "is_stale": true/false,  # If staleness check was performed
            "last_run_days_ago": 5,  # Days since last run
            "query_result": {...}
        }
        """
        # Extract parameters
        query = self.input_data.get('query', '')
        result_field = self.input_data.get('result_field')
        branch_map = self.input_data.get('branch_map', {})
        posting_id = self.input_data.get('posting_id')
        workflow_run_id = self.input_data.get('workflow_run_id')
        staleness_days = self.input_data.get('staleness_days')
        staleness_conversation_id = self.input_data.get('staleness_conversation_id')
        
        if not query or not result_field:
            return {
                "status": "[FAILED]",
                "error": "Missing query or result_field"
            }
        
        # Substitute placeholders in query
        if posting_id:
            query = query.replace('{posting_id}', str(posting_id))
        if workflow_run_id:
            query = query.replace('{workflow_run_id}', str(workflow_run_id))
        
        cursor = self.db_conn.cursor()
        
        try:
            # Run main query
            cursor.execute(query)
            row = cursor.fetchone()
            
            if not row:
                result_value = "null"
            else:
                field_value = row.get(result_field)
                if field_value is None:
                    result_value = "null"
                elif isinstance(field_value, bool):
                    result_value = "true" if field_value else "false"
                else:
                    result_value = str(field_value)
            
            # Check staleness if configured
            is_stale = False
            last_run_days_ago = None
            
            if staleness_days is not None and staleness_conversation_id is not None and posting_id:
                cursor.execute("""
                    SELECT EXTRACT(DAY FROM NOW() - MAX(completed_at))::int as days_ago
                    FROM interactions
                    WHERE posting_id = %s
                      AND conversation_id = %s
                      AND status = 'completed'
                """, (posting_id, staleness_conversation_id))
                
                stale_row = cursor.fetchone()
                if stale_row and stale_row.get('days_ago') is not None:
                    last_run_days_ago = stale_row['days_ago']
                    is_stale = last_run_days_ago > staleness_days
                else:
                    # Never run before = stale
                    is_stale = True
                    last_run_days_ago = None
            
            # Determine final status
            # If data exists but is stale, we should [RUN] to refresh
            if result_value == "true" and is_stale:
                status = "[RUN]"  # Exists but stale, re-run
            else:
                status = branch_map.get(result_value, "[RUN]")
            
            return {
                "status": status,
                "result_value": result_value,
                "is_stale": is_stale,
                "last_run_days_ago": last_run_days_ago,
                "query_result": dict(row) if row else None
            }
            
        except Exception as e:
            return {
                "status": branch_map.get("error", "[FAILED]"),
                "error": str(e)
            }


if __name__ == '__main__':
    actor = SQLQueryExecutor()
    actor.run()
