#!/usr/bin/env python3
"""
Standard Template for Script Actors in Wave Runner V2

This template defines the contract for all script actors:
1. Read input from stdin (JSON)
2. Query previous interactions for context
3. Process and write to staging tables
4. Output result to stdout (JSON)

Usage:
    Inherit from ScriptActorBase and implement process()
"""

import json
import sys
import psycopg2
from psycopg2.extras import RealDictCursor


class ScriptActorBase:
    """Base class for all script actors"""
    
    def __init__(self):
        self.input_data = None
        self.db_conn = None
        
    def load_input(self):
        """Load input from stdin"""
        try:
            self.input_data = json.loads(sys.stdin.read())
            return True
        except json.JSONDecodeError as e:
            self.output_error(f"Invalid JSON input: {e}")
            return False
    
    def connect_db(self):
        """Connect to database"""
        try:
            self.db_conn = psycopg2.connect(
                dbname="turing",
                user="base_admin",
                password=os.getenv('DB_PASSWORD', ''),
                host="localhost",
                cursor_factory=RealDictCursor
            )
            return True
        except Exception as e:
            self.output_error(f"Database connection failed: {e}")
            return False
    
    def query_previous_interaction(self, conversation_id=None, canonical_name=None):
        """Query output from previous interaction in same workflow run for same posting
        
        Args:
            conversation_id: Direct conversation ID to query
            canonical_name: Canonical name to look up conversation ID
        
        Returns:
            Output dict from the interaction, or None
        """
        cursor = self.db_conn.cursor()
        
        # If canonical_name provided, look up conversation_id
        if canonical_name and not conversation_id:
            cursor.execute("""
                SELECT conversation_id FROM conversations
                WHERE canonical_name = %s
                LIMIT 1
            """, (canonical_name,))
            row = cursor.fetchone()
            if row:
                conversation_id = row[0] if isinstance(row, tuple) else row['conversation_id']
            else:
                cursor.close()
                return None
        
        if not conversation_id:
            cursor.close()
            return None
        
        # Get posting_id from input_data if available
        posting_id = self.input_data.get('posting_id')
        
        if posting_id:
            # Filter by posting_id for posting-specific queries
            cursor.execute("""
                SELECT output
                FROM interactions
                WHERE workflow_run_id = %s
                  AND conversation_id = %s
                  AND posting_id = %s
                  AND status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            """, (self.input_data['workflow_run_id'], conversation_id, posting_id))
        else:
            # No posting_id - use original behavior (for non-posting workflows)
            cursor.execute("""
                SELECT output
                FROM interactions
                WHERE workflow_run_id = %s
                  AND conversation_id = %s
                  AND status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
            """, (self.input_data['workflow_run_id'], conversation_id))
        
        row = cursor.fetchone()
        cursor.close()
        if row:
            return row[0] if isinstance(row, tuple) else row['output']
        return None
    
    def process(self):
        """Override this method in child classes"""
        raise NotImplementedError("Subclass must implement process()")
    
    def output_success(self, result_data):
        """Output success result to stdout"""
        output = {
            'status': 'success',
            'data': result_data
        }
        print(json.dumps(output))
        sys.exit(0)
    
    def output_error(self, error_message):
        """Output error to stdout"""
        output = {
            'status': 'error',
            'error': error_message
        }
        print(json.dumps(output))
        sys.exit(1)
    
    def run(self):
        """Main execution flow"""
        if not self.load_input():
            return
        
        if not self.connect_db():
            return
        
        try:
            result = self.process()
            self.output_success(result)
        except Exception as e:
            self.output_error(str(e))
        finally:
            if self.db_conn:
                self.db_conn.close()
