#!/usr/bin/env python3
"""
SQL Query Executor for Turing Workflows
========================================

Executes SQL queries and returns results as branch conditions.

Input (JSON):
{
    "query": "SELECT ... FROM ... WHERE ...",
    "result_field": "field_name",  # Optional: specific field to check
    "branch_map": {                 # Optional: map results to branches
        "true": "[SKIP]",
        "false": "[RUN]",
        "null": "[RUN]",
        "error": "[FAILED]"
    }
}

Output:
- If branch_map provided: outputs the mapped branch string
- Otherwise: outputs the query result as JSON
"""

import sys
import json
from core.database import get_connection, return_connection
from psycopg2.extras import RealDictCursor


def execute_sql_query(query: str, params: dict = None) -> dict:
    """Execute SQL query and return result"""
    conn = get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # For SELECT queries, fetch results
        if query.strip().upper().startswith('SELECT'):
            result = cursor.fetchone()
            if result:
                return dict(result)
            else:
                return {}
        else:
            # For non-SELECT queries (UPDATE, INSERT, etc.)
            conn.commit()
            return {"rows_affected": cursor.rowcount}
            
    finally:
        return_connection(conn)


def map_result_to_branch(result: dict, result_field: str = None, branch_map: dict = None) -> str:
    """Map query result to branch condition"""
    
    if not branch_map:
        # No mapping - return JSON result
        return json.dumps(result)
    
    # Get the value to check
    if result_field:
        value = result.get(result_field)
    else:
        # Use first field in result
        value = list(result.values())[0] if result else None
    
    # Determine the key for branch mapping
    if value is None:
        key = "null"
    elif isinstance(value, bool):
        key = "true" if value else "false"
    elif isinstance(value, (int, float)):
        key = "true" if value > 0 else "false"
    else:
        key = "true" if value else "false"
    
    return branch_map.get(key, branch_map.get("default", "[RUN]"))


if __name__ == "__main__":
    try:
        # Read input
        input_data = json.loads(sys.stdin.read())
        
        query = input_data.get('query')
        params = input_data.get('params')
        result_field = input_data.get('result_field')
        branch_map = input_data.get('branch_map')
        
        if not query:
            raise ValueError("query is required")
        
        # Execute query
        result = execute_sql_query(query, params)
        
        # Map result to branch or return JSON
        output = map_result_to_branch(result, result_field, branch_map)
        
        # Always output JSON for Wave Runner V2 compatibility
        if branch_map and not output.startswith('{'):
            # Branch marker - wrap in JSON with status field
            print(json.dumps({"status": output}))
        else:
            # Already JSON
            print(output)
        
        sys.exit(0)
        
    except Exception as e:
        # On error, return error branch if mapped, otherwise fail
        error_output = {
            "error": str(e),
            "query": input_data.get('query', 'unknown') if 'input_data' in locals() else 'unknown'
        }
        
        if 'input_data' in locals() and input_data.get('branch_map'):
            error_branch = input_data['branch_map'].get('error', '[FAILED]')
            print(json.dumps({"status": error_branch, "error": str(e)}))
        else:
            print(json.dumps(error_output))
        
        sys.exit(1)
